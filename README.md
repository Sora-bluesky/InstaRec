# InstaRec

**English** | [日本語](README.ja.md)

A lightweight screen recording tool for Windows 10.

Windows 11 has a built-in screen recording feature via Snipping Tool, but Windows 10 does not. InstaRec fills that gap.

## Features

**Recording**

- Region-based screen capture with resizable selection area
- Snipping Tool-style selection handles (corner ticks and edge ticks)
- 3-second countdown before recording starts
- Pause and resume recording
- System audio and microphone capture (with device selection)

**Preview & Export**

- Built-in video preview with playback controls
- Seek bar, volume control, and trim (start/end)
- Export as MP4 or GIF (with quality and frame rate options)
- Save, copy video file to clipboard, or open folder in Explorer

**Usability**

- Global hotkey: `Win+Shift+R` to start/stop recording
- English / Japanese UI (switchable from toolbar menu)
- Compact floating toolbar that stays out of the way
- Settings panel for recording, audio, and behavior preferences

## Installation

Download the latest installer from [Releases](https://github.com/Sora-bluesky/InstaRec/releases) and run it. No additional software required — Python and FFmpeg are bundled in the installer.

### System Requirements

- Windows 10 or later (also works on Windows 11)

### For Developers

```bash
pip install -r requirements.txt
python main.py
```

To build the standalone executable:

```bash
pip install pyinstaller
pyinstaller InstaRec.spec
```

## Usage

1. Launch InstaRec. A control bar appears at the top of the screen.
2. Click the red record button to start selecting a region.
3. Drag to select the area you want to record.
4. Click **Start** to begin recording (after a 3-second countdown).
5. Use the control bar to pause, resume, or stop.
6. After stopping, the preview window opens for playback and export.

## Update

Download the latest installer from [Releases](https://github.com/Sora-bluesky/InstaRec/releases) and run it. The installer will automatically replace the previous version. Your settings are preserved.

## License

[MIT](LICENSE)
