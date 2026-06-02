# Y55 - Fast YouTube Downloader

A modern, fast, and lightweight YouTube downloader web app that supports 1080p video and audio streaming. Installable as a PWA on Windows 10.

## Features
- **Fast 1080p Downloads**: Muxes video and audio on-the-fly.
- **MP3 Audio**: High-quality audio extraction.
- **Streaming Approach**: No server-side disk usage; data is streamed directly to your browser.
- **Dark Mode**: Sleek and modern user interface.
- **PWA Support**: Install it as a standalone app on Windows 10.

## Installation

### 1. Prerequisites
- **Python 3.10+**
- **FFmpeg**: Required for merging video and audio streams.
  - **Windows**: [Download FFmpeg](https://ffmpeg.org/download.html), extract it, and add the `bin` folder to your System PATH.
  - **Linux**: `sudo apt update && sudo apt install ffmpeg`

### 2. Setup
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd y55
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Run the App
Start the server using Uvicorn:
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
Open your browser and go to `http://localhost:8000`.

## How to Install on Windows 10 (PWA)

1. Open the app in **Google Chrome** or **Microsoft Edge** (`http://localhost:8000`).
2. In the address bar, click the **Install App** icon (looks like a screen with an arrow) or:
   - **Chrome**: Click the three dots (⋮) -> **Save and Share** -> **Install page as app**.
   - **Edge**: Click the three dots (...) -> **Apps** -> **Install this site as an app**.
3. Y55 will now appear in your Start Menu and on your Desktop as a standalone application.

## Usage
1. Paste a YouTube URL into the input field.
2. Click **Fetch** to see the video preview.
3. Choose **Download 1080p Video** or **Download MP3 Audio**.
4. The download will start immediately!
