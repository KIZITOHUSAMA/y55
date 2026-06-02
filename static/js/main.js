document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('videoUrl');
    const searchBtn = document.getElementById('searchBtn');
    const loading = document.getElementById('loading');
    const preview = document.getElementById('preview');
    const thumbnail = document.getElementById('thumbnail');
    const videoTitle = document.getElementById('videoTitle');
    const videoAuthor = document.getElementById('videoAuthor');
    const videoDuration = document.getElementById('videoDuration');
    const downloadVideo = document.getElementById('downloadVideo');
    const downloadAudio = document.getElementById('downloadAudio');

    let currentVideoInfo = null;
    let currentUrl = "";

    searchBtn.addEventListener('click', fetchInfo);
    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') fetchInfo();
    });

    async function fetchInfo() {
        const url = urlInput.value.trim();
        if (!url) return;

        currentUrl = url;
        loading.classList.remove('hidden');
        preview.classList.add('hidden');

        try {
            const response = await fetch('/info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url }),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to fetch video info');
            }

            const info = await response.json();
            currentVideoInfo = info;

            thumbnail.src = info.thumbnail;
            videoTitle.textContent = info.title;
            videoAuthor.textContent = `By ${info.uploader}`;
            videoDuration.textContent = `Duration: ${formatDuration(info.duration)}`;

            loading.classList.add('hidden');
            preview.classList.remove('hidden');
        } catch (error) {
            alert(error.message);
            loading.classList.add('hidden');
        }
    }

    downloadVideo.addEventListener('click', () => {
        const downloadUrl = `/download?url=${encodeURIComponent(currentUrl)}&type=video&title=${encodeURIComponent(currentVideoInfo.title)}`;
        window.location.href = downloadUrl;
    });

    downloadAudio.addEventListener('click', () => {
        const downloadUrl = `/download?url=${encodeURIComponent(currentUrl)}&type=audio&title=${encodeURIComponent(currentVideoInfo.title)}`;
        window.location.href = downloadUrl;
    });

    function formatDuration(seconds) {
        if (!seconds) return "Unknown";
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
});
