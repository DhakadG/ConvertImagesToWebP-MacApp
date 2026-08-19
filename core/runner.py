"""Batch orchestration: scan sources, plan destinations, run a thread pool.

UI-agnostic on purpose — it takes plain callbacks, so the GUI can marshal them
onto the Tk thread however it likes, and the tests can call it directly.
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from core.config import Settings
from core.imaging import convert_file

CONVERTED, SKIPPED, FAILED, CANCELLED = "converted", "skipped", "failed", "cancelled"


@dataclass
class FileResult:
    source: Path
    status: str
    destination: Path | None = None
    source_bytes: int = 0
    output_bytes: int = 0
    message: str = ""

    @property
    def saved_bytes(self) -> int:
        return self.source_bytes - self.output_bytes if self.status == CONVERTED else 0


@dataclass
class Scan:
    files: list[Path] = field(default_factory=list)
    root: Path = Path(".")
    total_bytes: int = 0

    def __bool__(self) -> bool:
        return bool(self.files)


@dataclass
class Progress:
    completed: int
    total: int
    converted: int
    skipped: int
    failed: int
    bytes_in: int
    bytes_out: int
    elapsed: float
    current: str = ""

    @property
    def fraction(self) -> float:
        return self.completed / self.total if self.total else 0.0

    @property
    def rate(self) -> float:
        """Files per second so far."""
        return self.completed / self.elapsed if self.elapsed > 0.5 else 0.0

    @property
    def eta_seconds(self) -> float | None:
        if self.completed < 3 or self.rate <= 0:
            return None  # too early to be anything but a lie
        return (self.total - self.completed) / self.rate


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------
def common_root(paths: Iterable[Path]) -> Path:
    """Deepest directory containing every source, so relative structure is
    preserved instead of everything being flattened into one folder."""
    dirs = [p if p.is_dir() else p.parent for p in paths]
    if not dirs:
        return Path.cwd()
    try:
        return Path(os.path.commonpath([str(d.resolve()) for d in dirs]))
    except ValueError:  # different drives on Windows
        return dirs[0].resolve()


def scan_sources(sources: list[Path], extensions: tuple[str, ...],
                 exclude_under: Path | None = None) -> Scan:
    """Collect every readable image below `sources`.

    `exclude_under` keeps a previous run's output folder out of the next run —
    without it, converting a folder twice re-converts its own results.
    """
    wanted = {e.lower() for e in extensions}
    found: set[Path] = set()
    skip_root = exclude_under.resolve() if exclude_under else None

    def keep(path: Path) -> bool:
        if path.suffix.lower() not in wanted:
            return False
        if skip_root:
            try:
                path.resolve().relative_to(skip_root)
                return False
            except ValueError:
                pass
        return True

    for source in sources:
        if source.is_file():
            if keep(source):
                found.add(source.resolve())
        elif source.is_dir():
            # One walk, filter by suffix — rglob per extension re-walks the
            # tree N times and double-counts on case-insensitive filesystems.
            for path in source.rglob("*"):
                if path.is_file() and keep(path):
                    found.add(path.resolve())

    files = sorted(found)
    total = 0
    for f in files:
        try:
            total += f.stat().st_size
        except OSError:
            pass
    return Scan(files=files, root=common_root(sources), total_bytes=total)


def destination_root(sources: list[Path], settings: Settings) -> Path | None:
    """Where output lands. None means in-place (next to each source)."""
    if settings.dest_mode == "in_place":
        return None
    if settings.dest_mode == "custom" and settings.dest_folder.strip():
        return Path(settings.dest_folder).expanduser()
    return common_root(sources) / settings.subfolder_name


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
class Runner:
    """Runs one batch. Single use — build a new one per run."""

    def __init__(self, scan: Scan, settings: Settings,
                 on_progress: Callable[[Progress], None] | None = None,
                 on_file: Callable[[FileResult], None] | None = None,
                 on_finish: Callable[[list[FileResult], bool, float], None] | None = None):
        self.scan = scan
        self.settings = settings
        self.on_progress = on_progress
        self.on_file = on_file
        self.on_finish = on_finish

        self.results: list[FileResult] = []
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._claimed: set[str] = set()
        self._started = 0.0
        self._counts = {CONVERTED: 0, SKIPPED: 0, FAILED: 0}
        self._bytes_in = 0
        self._bytes_out = 0

    # -- public ---------------------------------------------------------
    def cancel(self) -> None:
        self._cancel.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> list[FileResult]:
        """Blocking. Call from a worker thread if you have a UI."""
        self.settings.clamp()
        self._started = time.monotonic()
        dest_root = destination_root([self.scan.root], self.settings)

        workers = self.settings.worker_count()
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                # map() submits every task up front; cancelled files fall through
                # _process cheaply rather than being withdrawn from the queue.
                for _ in pool.map(lambda f: self._process(f, dest_root), self.scan.files):
                    pass
        finally:
            # on_finish must fire even if the pool blows up — the progress
            # screen waits on it, and without it the user is stranded there.
            elapsed = time.monotonic() - self._started
            if self.on_finish:
                self.on_finish(self.results, self.cancelled, elapsed)
        return self.results

    def start_background(self) -> threading.Thread:
        thread = threading.Thread(target=self.run, name="convert-batch", daemon=True)
        thread.start()
        return thread

    # -- internals ------------------------------------------------------
    def _process(self, source: Path, dest_root: Path | None) -> None:
        """Never raises. pool.map re-raises in the consuming loop, so a single
        escaped exception would abort the batch and skip every remaining file."""
        try:
            self._process_one(source, dest_root)
        except Exception as exc:
            try:
                self._record(FileResult(source, FAILED,
                                        message=f"{type(exc).__name__}: {exc}"))
            except Exception:
                pass

    def _process_one(self, source: Path, dest_root: Path | None) -> None:
        if self._cancel.is_set():
            self._record(FileResult(source, CANCELLED))
            return

        try:
            source_bytes = source.stat().st_size
        except OSError as exc:
            self._record(FileResult(source, FAILED, message=str(exc)))
            return

        try:
            destination = self._claim_destination(source, dest_root)
        except _Skip:
            self._record(FileResult(source, SKIPPED, source_bytes=source_bytes,
                                    message="output already exists"))
            return

        # Encode to a sidecar, then rename over the target. Two reasons:
        # a half-written file never appears at the destination, and under the
        # overwrite policy a failed encode can no longer destroy the perfectly
        # good output from a previous run.
        staging = destination.with_name(destination.name + ".part")
        try:
            encoded = convert_file(source, staging, self.settings)
            staging.replace(destination)
            output_bytes = destination.stat().st_size
            self._record(FileResult(source, CONVERTED, destination, source_bytes,
                                    output_bytes, encoded.note))
        except Exception as exc:
            _discard(staging)
            self._record(FileResult(source, FAILED, source_bytes=source_bytes,
                                    message=f"{type(exc).__name__}: {exc}"))

    def _claim_destination(self, source: Path, dest_root: Path | None) -> Path:
        """Reserve a unique output path. Raises _Skip under the skip policy."""
        if dest_root is None:
            folder = source.parent
        else:
            try:
                relative = source.parent.relative_to(self.scan.root)
            except ValueError:
                relative = Path()
            folder = dest_root / relative

        suffix = self.settings.output_suffix()
        base = folder / (source.stem + suffix)
        policy = self.settings.on_existing

        with self._lock:
            candidate, index = base, 0
            while True:
                key = str(candidate).lower()
                taken_this_run = key in self._claimed
                exists_on_disk = candidate.exists()

                if not taken_this_run and not exists_on_disk:
                    self._claimed.add(key)
                    return candidate
                if not taken_this_run and exists_on_disk and policy == "overwrite":
                    self._claimed.add(key)
                    return candidate
                if not taken_this_run and exists_on_disk and policy == "skip":
                    raise _Skip
                # rename policy, or two sources competing for one name this run
                index += 1
                candidate = folder / f"{source.stem}_{index}{suffix}"

    def _record(self, result: FileResult) -> None:
        with self._lock:
            self.results.append(result)
            if result.status in self._counts:
                self._counts[result.status] += 1
            self._bytes_in += result.source_bytes
            self._bytes_out += result.output_bytes
            snapshot = Progress(
                completed=len(self.results),
                total=len(self.scan.files),
                converted=self._counts[CONVERTED],
                skipped=self._counts[SKIPPED],
                failed=self._counts[FAILED],
                bytes_in=self._bytes_in,
                bytes_out=self._bytes_out,
                elapsed=time.monotonic() - self._started,
                current=result.source.name,
            )
        if self.on_file:
            self.on_file(result)
        if self.on_progress:
            self.on_progress(snapshot)


class _Skip(Exception):
    """Destination exists and the policy says leave it alone."""


def _discard(path: Path) -> None:
    """Delete a staging file, tolerating failure. On Windows an antivirus or
    indexer holding the handle raises PermissionError; leaving a stray .part
    behind is far better than losing the whole batch to it."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------------
def format_bytes(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60:02d}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60:02d}m"
