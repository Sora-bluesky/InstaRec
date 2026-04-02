# InstaRec

[English](README.md) | **日本語**

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
- 保存、動画ファイルをクリップボードにコピー、フォルダをエクスプローラーで開く

**使いやすさ**

- グローバルホットキー: `Win+Shift+R` で録画開始/停止
- 英語 / 日本語 UI（ツールバーメニューから切り替え）
- コンパクトなフローティングツールバー
- 録画、オーディオ、動作の設定パネル

## インストール

### winget（推奨）

```powershell
winget install Sora-bluesky.InstaRec
```

### インストーラー

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
4. **Start** をクリックすると録画が始まります（3 秒のカウントダウン後）。
5. コントロールバーで一時停止、再開、停止ができます。
6. 停止後、プレビューウィンドウが開き、再生やエクスポートができます。

## アップデート

```powershell
winget upgrade Sora-bluesky.InstaRec
```

または [Releases](https://github.com/Sora-bluesky/InstaRec/releases) から最新のインストーラーをダウンロードして実行してください。前のバージョンは自動的に置き換えられます。設定は保持されます。

## ライセンス

[MIT](LICENSE)
