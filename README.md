# WebP Studio 2.0

Batch image converter for macOS, Windows and Linux. Drop a folder, pick a
preset, get smaller images.

A rewrite of ConvertImagesToWebP-MacAlpha v0.1 — same idea, working engine.

---

## What's new in 2.0

**Things v0.1 advertised but didn't do**

| | v0.1 | 2.0 |
|---|---|---|
| Drag & drop | `tkinterdnd2` in requirements, never imported | works; the app tells you if the package is missing |
| "Preserve EXIF & color profiles" toggle | ignored — metadata dropped from every file | actually written, plus optional GPS-only removal |
| `MAX_THREADS: 8` | unused; conversion ran one file at a time | real thread pool, auto-sized to your CPU |
| Time remaining | permanently "Calculating…" | live ETA and images/sec |
| Cancel | stopped, then reported "Conversion Complete!" | reports what finished and what never started |
| Errors | recorded, never displayed | listed on screen and savable to a log |
| 5,000-image batches | one widget per file, frozen window | single capped log view |
| `python setup.py py2app` | failed — missing `assets/icon.icns` | builds without an icon |
| GitHub Actions build | `cd` into a folder that isn't in the repo | fixed |

**New**

- **Output formats** — WebP, AVIF, JPEG, PNG (only the ones your Pillow build can write are offered)
- **Presets** — Web · Balanced · Archive · Smallest
- **Resize by** longest edge, width, height, or megapixels. Never upscales.
- **Destination control** — subfolder, a folder you choose, or next to each original
- **If a file already exists** — skip, overwrite, or rename
- **Preflight** — "482 images · 3.1 GB → Pictures/Converted" before you commit
- **Lossless mode**, encoder-effort control, worker count
- **System / Light / Dark**, remembered between launches
- **Keyboard** — `Ctrl/⌘O` folder · `Ctrl/⌘⇧O` files · `Return` convert · `Esc` stop or clear

---

## Install

```bash
pip install -r requirements.txt
python main.py
```

Only `customtkinter` and `Pillow` are required. The rest are optional and the
app degrades cleanly without them — check what you have:

```bash
python main.py --check
```

| Optional | Enables |
|---|---|
| `tkinterdnd2` | drag & drop onto the window |
| `piexif` | removing GPS tags while keeping the rest of the EXIF |
| `pillow-heif` | reading iPhone `.heic` / `.heif` |

## macOS

**Use Homebrew's Python, not Apple's.** macOS ships Tk 8.5.9; CustomTkinter
needs 8.6+ and renders as black rectangles below that. `python main.py --check`
prints your Tk version and says so if it's too old.

```bash
brew install python python-tk
/opt/homebrew/bin/python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Build a .app

```bash
python setup.py py2app     # -> dist/WebP Studio.app
```

Drop an `assets/icon.icns` in first if you want a custom icon — unlike v1, the
build no longer fails without one.

**py2app bundles the interpreter it is run with, so the result is single-arch.**
An app built on an M-series Mac will not launch on an Intel Mac and vice versa.
CI therefore builds both (`macos-15-intel`, `macos-14` Apple Silicon) and
uploads them as separate artifacts. To produce one universal binary instead,
build with a universal2 python.org interpreter rather than a Homebrew one.

`LSMinimumSystemVersion` is set to 10.13, but the real floor is whatever the
building Python supports.

### "The app is damaged and can't be opened"

That is Gatekeeper, not a broken build — the bundle is unsigned and
un-notarized, and anything downloaded from a browser or CI artifact gets
quarantined. Either right-click → Open the first time, or:

```bash
xattr -dr com.apple.quarantine "/Applications/WebP Studio.app"
```

Signing and notarizing requires a paid Apple Developer account; that is the
only real fix for distributing to other people.

## Tests

```bash
python tests/test_engine.py     # no display needed
python tests/test_gui_boot.py   # needs a display
```

No framework. `test_engine` covers sizing math, alpha flattening, metadata
keep/strip, output-collision handling, the skip/overwrite/rename policies,
error isolation, cancel, and savings accounting. `test_gui_boot` builds the
real window and drives a real conversion through the Tk event loop — it exists
to catch what only breaks on a specific OS (fonts that don't resolve, widget
options a platform's Tk rejects) and runs in CI on macOS and Windows.

Both write settings to a temp directory via `WEBP_STUDIO_CONFIG_DIR`, so they
never touch your real config.

---

## How it works

```
main.py            entry point + dependency check
core/
  config.py        Settings dataclass, presets, JSON persistence
  imaging.py       one image: open → orient → resize → square → encode
  runner.py        scan, plan destinations, thread pool, cancel, progress
gui/
  theme.py         design tokens — every color is a (light, dark) pair
  widgets.py       Card, StatTile, ProgressRing, SliderRow, LogView
  panel.py         the settings panel
  screens/         home · progress · results
```

`core/` has no UI imports, so the engine is usable from a script and testable
without a display.

### Notes on behaviour

- **Resizing never upscales.** A limit larger than the source is a no-op.
- **Metadata off converts to sRGB.** An untagged file is read as sRGB by every
  viewer, so baking the profile in keeps colors from shifting.
- **The output folder is excluded from scans.** Converting the same folder
  twice will not re-convert its own results.
- **Failed files leave nothing behind.** A partial write is deleted, because a
  truncated image looks fine in a file manager and fails later.
- **Animated sources take frame one**, and say so in the log.

## Verified on

| | Status |
|---|---|
| Windows 11 · Python 3.12 · Tk 8.6 · CustomTkinter 6.0 (`>=5.2.2` required) | both suites pass; app driven end to end |
| Engine logic (any OS) | 15 checks, no display required |
| macOS 14 (Apple Silicon), CI | GUI boot + real conversion pass; `.app` builds and its interpreter starts |
| macOS (Intel), CI | `.app` builds on `macos-15-intel` |
| Linux | should work; `test_gui_boot` needs `xvfb` in CI |

Not covered anywhere: a human double-clicking the built `.app`. CI runners have
no window server, so that last step is yours.

## License

MIT.
