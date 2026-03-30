# InstaRec

**English** | [日本語](#instarec-1)

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
- Save, copy path to clipboard, or open in Explorer

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

---

# InstaRec

[English](#instarec) | **日本語**

Windows 10 向けの軽量な画面録画ツール。

Windows 11 には Snipping Tool に録画機能が内蔵されていますが、Windows 10 にはありません。InstaRec はその不足を補います。

## 機能

**録画**

- 範囲指定による画面キャプチャ（リサイズ可能な選択エリア）
- Snipping Tool 風の選択ハンドル（コーナーティックとエッジティック）
- 録画開始前の 3 秒カウントダウン
- 一時停止と再開
- システム音声とマイクのキャプチャ（デバイス選択対応）

**プレビューとエクスポート**

- 再生コントロール付きの動画プレビュー
- シークバー、音量調整、トリミング（開始/終了）
- MP4 または GIF でエクスポート（品質とフレームレート設定）
- 保存、クリップボードにパスをコピー、エクスプローラーで開く

**使いやすさ**

- グローバルホットキー: `Win+Shift+R` で録画開始/停止
- 英語 / 日本語 UI（ツールバーメニューから切り替え）
- コンパクトなフローティングツールバー
- 録画、オーディオ、動作の設定パネル

## インストール

[Releases](https://github.com/Sora-bluesky/InstaRec/releases) から最新のインストーラーをダウンロードして実行してください。Python や FFmpeg の追加インストールは不要です。

### 動作環境

- Windows 10 以降（Windows 11 でも動作します）

### 開発者向け

```bash
pip install -r requirements.txt
python main.py
```

スタンドアロン実行ファイルのビルド:

```bash
pip install pyinstaller
pyinstaller InstaRec.spec
```

## 使い方

1. InstaRec を起動すると、画面上部にコントロールバーが表示されます。
2. 赤い録画ボタンをクリックして範囲選択を開始します。
3. ドラッグして録画したい範囲を選択します。
4. **スタート** をクリックすると録画が始まります（3 秒のカウントダウン後）。
5. コントロールバーで一時停止、再開、停止ができます。
6. 停止後、プレビューウィンドウが開き、再生やエクスポートができます。

## アップデート

[Releases](https://github.com/Sora-bluesky/InstaRec/releases) から最新のインストーラーをダウンロードして実行してください。前のバージョンは自動的に置き換えられます。設定は保持されます。

## ライセンス

[MIT](LICENSE)
