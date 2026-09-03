# WebP Studio 2.0

[![Build](https://github.com/DhakadG/ConvertImagesToWebP-MacApp/actions/workflows/build.yml/badge.svg)](https://github.com/DhakadG/ConvertImagesToWebP-MacApp/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](requirements.txt)

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

Pick the row that matches you.

| You want to | Go to |
|---|---|
| Run the Mac app | [Install on macOS](#install-on-macos) |
| Run it on Windows for testing | [Run on Windows](#run-on-windows) |
| Run it on Linux | [Run on Linux](#run-on-linux) |
| Build the `.app` yourself | [Build a .app](#build-a-app) |

---

## Install on macOS

### 1. Work out which build you need

 → **About This Mac**:

| It says | Download |
|---|---|
| Chip: Apple M1 / M2 / M3 / M4 … | `WebP-Studio-macOS-apple-silicon.zip` |
| Processor: Intel … | `WebP-Studio-macOS-intel.zip` |

They are not interchangeable. py2app bundles the interpreter it built with, so
each zip runs on one kind of Mac only. The wrong one will refuse to open.

### 2. Download it

[**Releases**](https://github.com/DhakadG/ConvertImagesToWebP-MacApp/releases/latest)
— every tagged version, kept permanently.

If there is no release yet, or you want the newest commit instead, take a build
from CI: [**Actions → Build**](https://github.com/DhakadG/ConvertImagesToWebP-MacApp/actions/workflows/build.yml)
→ open the most recent green run → **Artifacts**. CI builds are kept 90 days.
You must be signed in to GitHub to download artifacts.

### 3. Unzip and install

Double-click the zip, then drag **WebP Studio** into your Applications folder.

### 4. Get past Gatekeeper

**Expect this to fail the first time.** macOS will say the app *"is damaged and
can't be opened"* or *"cannot be opened because Apple cannot check it for
malicious software."*

Nothing is damaged. These builds are unsigned and un-notarized — signing
requires a paid Apple Developer account — and macOS quarantines anything
unsigned that arrives via a browser. You have to clear that flag yourself.

**The one-liner that always works:**

```bash
xattr -dr com.apple.quarantine "/Applications/WebP Studio.app"
```

Then open the app normally. That is the whole fix.

<details>
<summary>Prefer to do it without the Terminal?</summary>

**macOS 15 (Sequoia) and later**

1. Double-click the app. Let it get blocked. Dismiss the dialog.
2. **System Settings → Privacy & Security**.
3. Scroll to the Security section. There is a line saying *"WebP Studio was
   blocked to protect your Mac."*
4. Click **Open Anyway**, then authenticate.
5. Double-click the app again and click **Open**.

Step 1 matters — the button in step 3 does not appear until macOS has blocked
the app at least once.

**macOS 14 (Sonoma) and earlier**

Right-click (or Control-click) the app → **Open** → **Open** in the dialog.
The right-click route is what makes the "open anyway" button appear; plain
double-clicking never offers it.

</details>

> Only do this for builds you produced or trust. Clearing the quarantine flag
> is exactly what you would do for genuine malware too — the check exists for a
> reason, and you are choosing to skip it here because you know where this
> binary came from.

### 5. If it bounces in the Dock and quits

That is not Gatekeeper, that is a crash. Get the real error:

```bash
"/Applications/WebP Studio.app/Contents/MacOS/WebP Studio" --check
```

That prints your Python, your Tk version, and which optional features are
available, instead of dying silently. Include its output if you file an issue.

---

## Run on Windows

There is no packaged `.exe` — Windows runs from source. Takes about a minute.

**1. Install Python 3.10 or newer** from [python.org](https://www.python.org/downloads/windows/).
Tick **"Add python.exe to PATH"** in the installer.

> Avoid the Microsoft Store build of Python — it ships without a usable
> `tkinter`, and this is a Tk app. `python main.py --check` will tell you if
> yours is the broken kind.

**2. Set it up** (PowerShell, from the repo folder):

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py --check
```

If `Activate.ps1` is blocked by execution policy, either use
`.venv\Scripts\activate.bat` or run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.

**3. Run it:**

```powershell
python main.py
```

Every launch after this only needs the activate line and `python main.py`.

---

## Run on Linux

```bash
sudo apt install python3-tk          # or your distro's Tk package
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## Dependencies

Only `customtkinter` and `Pillow` are required. Everything else is optional and
the app degrades cleanly without it:

| Optional | Enables |
|---|---|
| `tkinterdnd2` | drag & drop onto the window |
| `piexif` | removing GPS tags while keeping the rest of the EXIF |
| `pillow-heif` | reading iPhone `.heic` / `.heif` |

`python main.py --check` prints exactly what you have and what each missing
package costs you.

## Running from source on macOS

**Use Homebrew's Python, not Apple's.** macOS ships Tk 8.5.9; CustomTkinter
needs 8.6+ and renders as black rectangles below that. `--check` says so if
your Tk is too old.

```bash
brew install python python-tk
/opt/homebrew/bin/python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Build a .app

```bash
pip install py2app
python setup.py py2app     # -> dist/WebP Studio.app
```

Drop an `assets/icon.icns` in first if you want a custom icon — unlike v1, the
build no longer fails without one.

**py2app bundles the interpreter it is run with, so the result is single-arch.**
An app built on an M-series Mac will not launch on an Intel Mac and vice versa.
CI therefore builds both (`macos-15-intel`, `macos-14` Apple Silicon) and
publishes them as separate downloads. For one universal binary instead, build
with a universal2 python.org interpreter rather than a Homebrew one.

`LSMinimumSystemVersion` is set to 10.13, but the real floor is whatever the
building Python supports.

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

## Contributing

Issues and PRs welcome. `python tests/test_engine.py` should stay green with
no display, and CI runs it plus the GUI boot suite on every PR.

### Cutting a release

Push a tag matching `v*.*.*`:

```bash
git tag v2.0.0
git push origin v2.0.0
```

`.github/workflows/release.yml` builds both macOS bundles and publishes them
to a new GitHub Release, titled after the tag with auto-generated notes.

## License

[MIT](LICENSE).
