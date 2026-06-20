from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router
from youtube_service import router as youtube_router
from download_service import router as download_router
from player_service import router as player_router

app = FastAPI(title="YouTube Music Player API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(youtube_router)
app.include_router(download_router)
app.include_router(player_router)

@app.get("/")
async def root():
    return {"message": "YouTube Music Player API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
