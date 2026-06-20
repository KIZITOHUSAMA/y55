from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from download_service import DOWNLOAD_DIR
import os
import urllib.parse

router = APIRouter(prefix="/player", tags=["player"])

@router.get("/stream/{filename}")
async def stream_file(filename: str):
    # Decode filename in case it has special characters
    decoded_filename = urllib.parse.unquote(filename)

    # Path traversal protection
    file_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, decoded_filename))
    if not file_path.startswith(os.path.abspath(DOWNLOAD_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)

@router.get("/scan")
async def scan_library():
    # This can be used to refresh the frontend library state
    files = []
    for filename in os.listdir(DOWNLOAD_DIR):
        if filename.endswith((".mp3", ".mp4", ".mkv", ".webm")):
            stat = os.stat(os.path.join(DOWNLOAD_DIR, filename))
            files.append({
                "id": filename,
                "title": filename.rsplit('.', 1)[0],
                "filename": filename,
                "size": stat.st_size,
                "type": "video" if filename.endswith((".mp4", ".mkv", ".webm")) else "audio"
            })
    return files
