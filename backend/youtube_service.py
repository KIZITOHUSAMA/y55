from fastapi import APIRouter, Depends
from auth import get_yt_service

router = APIRouter(prefix="/youtube", tags=["youtube"])

@router.get("/playlists")
async def get_playlists(youtube=Depends(get_yt_service)):
    request = youtube.playlists().list(
        part="snippet,contentDetails",
        mine=True,
        maxResults=50
    )
    response = request.execute()

    playlists = []
    for item in response.get("items", []):
        playlists.append({
            "id": item["id"],
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"],
            "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
            "trackCount": item["contentDetails"]["itemCount"]
        })

    return playlists

@router.get("/playlists/{playlist_id}/items")
async def get_playlist_items(playlist_id: str, youtube=Depends(get_yt_service)):
    items = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response.get("items", []):
            items.append({
                "id": item["snippet"]["resourceId"]["videoId"],
                "title": item["snippet"]["title"],
                "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
                "position": item["snippet"]["position"]
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return items

@router.get("/trending")
async def get_trending(youtube=Depends(get_yt_service)):
    # Fetching popular music videos as "Trending"
    request = youtube.videos().list(
        part="snippet,contentDetails",
        chart="mostPopular",
        videoCategoryId="10", # Music category
        maxResults=10
    )
    response = request.execute()

    videos = []
    for item in response.get("items", []):
        videos.append({
            "id": item["id"],
            "title": item["snippet"]["title"],
            "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
            "duration": item["contentDetails"]["duration"] # ISO 8601 format
        })

    return videos
