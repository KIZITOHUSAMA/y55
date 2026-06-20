# YouTube Music Player & Downloader

A real-time web application to connect your YouTube account, browse playlists, and download high-quality audio/video to your local machine.

## Features
- **Modern Dashboard**: Sleek dark UI inspired by the provided mockup.
- **Google OAuth2**: Securely sync with your YouTube library.
- **High-Quality Downloads**: 320kbps MP3s and high-res video downloads using `yt-dlp`.
- **Integrated Player**: Play your downloaded library directly in the browser.
- **Selective Download**: Choose specific tracks or download entire playlists.

## Setup Instructions

### 1. Google Cloud Configuration
- Go to the [Google Cloud Console](https://console.cloud.google.com/).
- Create a new project.
- Enable the **YouTube Data API v3**.
- Go to **APIs & Services > OAuth consent screen** and configure it.
- Go to **Credentials > Create Credentials > OAuth client ID**.
- Select **Web application**.
- Add `http://localhost:8000/auth/callback` to **Authorized redirect URIs**.
- Download the JSON file, rename it to `client_secrets.json`, and place it in the `backend/` directory.

### 2. Backend Installation
- Navigate to the backend folder: `cd backend`
- Install dependencies: `pip install -r requirements.txt`
- Start the server: `uvicorn main:app --reload`
- The backend runs on `http://localhost:8000`.

### 3. Frontend Installation
- Navigate to the frontend folder: `cd frontend`
- Install dependencies: `npm install`
- Start the development server: `npm run dev`
- The frontend runs on `http://localhost:5173`.

### 4. Requirements
- **FFmpeg**: Must be installed on your system path for audio/video conversion.
- **Python 3.10+**
- **Node.js 18+**

## How to push to a new GitHub repository
1. Create a new empty repository on GitHub.
2. Run the following commands in your local project folder:
```bash
git init
git add .
git commit -m "Initial commit: YouTube Music Player"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```
