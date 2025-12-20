# ConvertImagesToWebP - MacAlpha v0.1

A native macOS GUI application for converting images to WebP format.

## Features

- 🖱️ **Drag & Drop** - Drop images or folders directly onto the app
- ⚙️ **Customizable Settings** - Quality, resolution, encoding speed
- 📊 **Real-time Progress** - Watch your conversions in progress
- 📈 **Size Savings Stats** - See how much space you saved
- 🌙 **Dark Mode Support** - Native macOS appearance

## Supported Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)
- HEIC (.heic)
- WebP (.webp) - direct copy

## Installation

### 1. Prerequisite: Homebrew

If you don't have Homebrew installed, open Terminal and run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Setup Python & Dependencies

Run these commands one by one in Terminal:

```bash
# Install Python and Tkinter via Homebrew
brew install python python-tk

# Navigate to the app folder
cd ConvertImagesToWebP-MacAlpha

# Create a virtual environment (fixes 'pip' issues)
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install required libraries
pip install -r requirements.txt
```

### 3. Run the App

```bash
python main.py
```

### Build .app Bundle (via GitHub Actions)

**Since you are on Windows**, you cannot build the macOS app directly. Instead:

1. Push this code to a GitHub repository
2. Go to the **Actions** tab in your repo
3. Select **Build macOS App** workflow
4. Run workflow (or it runs on push)
5. Download the `MacOS-App-Bundle` artifact when done

### Build .app Bundle (on macOS)

```bash
python setup.py py2app
```

This creates `ConvertImagesToWebP.app` in the `dist/` folder.

## Usage

1. **Drop Zone** - Drag images/folders or click Browse
2. **Settings** - Adjust quality, resolution, encoding options
3. **Progress** - Watch real-time conversion progress
4. **Results** - View stats and open output folder

## Settings

| Setting     | Description                | Default  |
| ----------- | -------------------------- | -------- |
| Quality     | WebP quality (1-100)       | 90       |
| Resolution  | Max megapixels limit       | 19 MP    |
| Encoding    | Speed vs compression (1-6) | 6 (Best) |
| Metadata    | Preserve EXIF/ICC profiles | Yes      |
| Square Mode | Original, Crop, or Canvas  | Original |

## License

MIT License - Feel free to modify and distribute.

---

Made with ❤️ for macOS
