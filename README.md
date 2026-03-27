# InstaRec

Screen recording tool for Windows 10 with a minimal, Apple HIG-inspired UI.

## Features

- Region-based screen recording with resizable selection
- System audio and microphone capture
- MP4 and GIF export
- Global hotkey support
- 3-second countdown before recording
- Pause / resume recording
- Recording preview with seek bar

## Requirements

- Windows 10
- Python 3.10+

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Build

```bash
pip install pyinstaller
pyinstaller InstaRec.spec
```

The standalone executable will be created in `dist/InstaRec.exe`.

## License

[MIT](LICENSE)
