import React, { useState, useEffect, useRef } from 'react';
import {
  Home, Compass, Radio, Library, Heart, Download,
  Play, Pause, SkipBack, SkipForward, Repeat, Shuffle,
  Volume2, Search, Bell, MoreHorizontal, User,
  ListMusic, TrendingUp, Music2, Disc
} from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const App = () => {
  const [activeTab, setActiveTab] = useState('Home');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [playlists, setPlaylists] = useState([]);
  const [trending, setTrending] = useState([]);
  const [localLibrary, setLocalLibrary] = useState([]);
  const [selectedPlaylist, setSelectedPlaylist] = useState(null);
  const [playlistItems, setPlaylistItems] = useState([]);
  const [selectedVideoIds, setSelectedVideoIds] = useState([]);
  const [currentTrack, setCurrentTrack] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [volume, setVolume] = useState(80);
  const audioRef = useRef(null);

  useEffect(() => {
    checkAuthStatus();
    fetchLocalLibrary();
  }, []);

  useEffect(() => {
    if (isLoggedIn) {
      fetchPlaylists();
      fetchTrending();
    }
  }, [isLoggedIn]);

  const checkAuthStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/auth/status`);
      setIsLoggedIn(res.data.logged_in);
    } catch (err) {
      console.error("Auth check failed", err);
    }
  };

  const handleLogin = async () => {
    try {
      const res = await axios.get(`${API_BASE}/auth/login`);
      if (res.data.url) window.location.href = res.data.url;
    } catch (err) {
      alert("Please ensure client_secrets.json is provided in the backend.");
    }
  };

  const fetchPlaylists = async () => {
    try {
      const res = await axios.get(`${API_BASE}/youtube/playlists`);
      setPlaylists(res.data);
    } catch (err) {
      console.error("Failed to fetch playlists", err);
    }
  };

  const fetchTrending = async () => {
    try {
      const res = await axios.get(`${API_BASE}/youtube/trending`);
      setTrending(res.data);
    } catch (err) {
      console.error("Failed to fetch trending", err);
    }
  };

  const fetchLocalLibrary = async () => {
    try {
      const res = await axios.get(`${API_BASE}/player/scan`);
      setLocalLibrary(res.data);
    } catch (err) {
      console.error("Failed to fetch library", err);
    }
  };

  const handleDownload = async (ids, isPlaylist = false) => {
    try {
      await axios.post(`${API_BASE}/download/start`, {
        ids: Array.isArray(ids) ? ids : [ids],
        is_playlist: isPlaylist
      });
      alert("Download started!");
    } catch (err) {
      console.error("Download failed", err);
    }
  };

  const openPlaylist = async (playlist) => {
    setSelectedPlaylist(playlist);
    setSelectedVideoIds([]);
    try {
      const res = await axios.get(`${API_BASE}/youtube/playlists/${playlist.id}/items`);
      setPlaylistItems(res.data);
    } catch (err) {
      console.error("Failed to fetch playlist items", err);
    }
  };

  const toggleVideoSelection = (videoId) => {
    setSelectedVideoIds(prev =>
      prev.includes(videoId) ? prev.filter(id => id !== videoId) : [...prev, videoId]
    );
  };

  const playTrack = (track) => {
    setCurrentTrack(track);
    setIsPlaying(true);
    if (audioRef.current) {
      audioRef.current.src = `${API_BASE}/player/stream/${encodeURIComponent(track.filename)}`;
      audioRef.current.play();
    }
  };

  const togglePlay = () => {
    if (!currentTrack) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  return (
    <div className="flex h-screen bg-[#0a0514] text-white overflow-hidden font-sans">
      {/* Sidebar */}
      <div className="w-64 bg-[#140c21] flex flex-col p-6 border-r border-white/5">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-purple-500 to-pink-500 flex items-center justify-center">
            <User size={24} />
          </div>
          <div>
            <p className="text-xs text-gray-400">Hi!</p>
            <p className="font-bold">Ahmad Fauzi</p>
          </div>
        </div>

        <nav className="flex-1 space-y-6">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-4 px-2">Menu</p>
            <SidebarItem icon={<Compass size={20}/>} label="Explore" active={activeTab === 'Explore'} onClick={() => setActiveTab('Explore')} />
            <SidebarItem icon={<Radio size={20}/>} label="Genres" />
            <SidebarItem icon={<Disc size={20}/>} label="Albums" />
            <SidebarItem icon={<User size={20}/>} label="Artist" />
          </div>

          <div>
            <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-4 px-2">Library</p>
            <SidebarItem icon={<Heart size={20}/>} label="Favourites" />
            <SidebarItem icon={<TrendingUp size={20}/>} label="Popular" />
            <SidebarItem icon={<Library size={20}/>} label="My Music" active={activeTab === 'My Music'} onClick={() => setActiveTab('My Music')} />
          </div>
        </nav>

        {!isLoggedIn && (
          <button
            onClick={handleLogin}
            className="mt-auto bg-primary py-2 px-4 rounded-full text-sm font-semibold hover:bg-opacity-80 transition"
          >
            Connect YouTube
          </button>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-y-auto scrollbar-hide">
        {/* Header */}
        <header className="p-6 flex justify-between items-center sticky top-0 bg-[#0a0514]/80 backdrop-blur-md z-10">
          <h1 className="text-2xl font-bold">{activeTab === 'Explore' ? 'Explore' : 'Home'}</h1>
          <div className="flex items-center gap-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                placeholder="Type here to search"
                className="bg-[#1c132b] rounded-full py-2 pl-10 pr-4 text-sm w-64 focus:outline-none border border-white/5"
              />
            </div>
            <Bell size={20} className="text-gray-400 cursor-pointer" />
          </div>
        </header>

        <main className="p-6 pt-0 space-y-8">
          {/* Banner */}
          <div className="relative h-64 rounded-3xl overflow-hidden bg-gradient-to-r from-[#b066ff] to-[#9d4edd] p-10 flex flex-col justify-center">
            <div className="max-w-md z-10">
              <p className="text-xs uppercase tracking-widest mb-2 opacity-80">Muskinaja</p>
              <h2 className="text-4xl font-bold mb-4 leading-tight">Listen to trending songs all the time</h2>
              <p className="text-sm opacity-80 mb-6">With Muskinaja, you can get premium music for free anywhere and at any time</p>
              <button className="bg-white text-black px-6 py-2 rounded-full text-sm font-bold w-fit shadow-xl hover:scale-105 transition">
                Explore Now
              </button>
            </div>
            <img
              src="https://images.unsplash.com/photo-1514525253361-b83f859b73c0?auto=format&fit=crop&q=80&w=1000"
              className="absolute right-0 top-0 h-full w-1/2 object-cover mix-blend-overlay opacity-50"
              alt="Banner"
            />
          </div>

          {/* Playlists */}
          <section>
            <div className="flex justify-between items-center mb-4 px-2">
              <h3 className="text-xl font-bold">Playlist</h3>
              <button className="text-xs text-gray-400 hover:text-white">See More</button>
            </div>
            <div className="grid grid-cols-4 gap-6">
              {playlists.slice(0, 4).map((pl) => (
                <PlaylistCard
                  key={pl.id}
                  playlist={pl}
                  onDownload={() => handleDownload(pl.id, true)}
                  onClick={() => openPlaylist(pl)}
                />
              ))}
              {!isLoggedIn && [1,2,3,4].map(i => <div key={i} className="h-48 bg-[#1c132b] rounded-2xl animate-pulse" />)}
            </div>
          </section>

          {/* Trending & Top Artist */}
          <div className="grid grid-cols-3 gap-8">
            <div className="col-span-2">
              <div className="flex justify-between items-center mb-4 px-2">
                <h3 className="text-xl font-bold">Trending</h3>
                <button className="text-xs text-gray-400 hover:text-white">See More</button>
              </div>
              <div className="space-y-3">
                {trending.map((v, i) => (
                  <TrendingItem key={v.id} video={v} index={i+1} onDownload={() => handleDownload(v.id)} />
                ))}
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-4 px-2">
                <h3 className="text-xl font-bold">Top Artist</h3>
                <button className="text-xs text-gray-400 hover:text-white">See More</button>
              </div>
              <div className="space-y-4">
                <ArtistItem name="Mamank" plays="122M" followers="1928" />
                <ArtistItem name="Maimunah" plays="50M" followers="1928" />
                <ArtistItem name="Paijo" plays="32M" followers="1928" />
              </div>

              {/* Mini Player widget from UI */}
              <div className="mt-8 bg-[#140c21] rounded-3xl p-4 shadow-2xl relative group">
                <img
                  src={currentTrack ? "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?auto=format&fit=crop&q=80&w=500" : "https://images.unsplash.com/photo-1493225255756-d9584f8606e9?auto=format&fit=crop&q=80&w=500"}
                  className="w-full h-48 object-cover rounded-2xl mb-4"
                />
                <div className="px-2">
                  <h4 className="font-bold truncate">{currentTrack ? currentTrack.title : 'No track selected'}</h4>
                  <p className="text-xs text-gray-400">Library</p>
                </div>

                <div className="flex items-center gap-2 mt-4 px-2">
                   <span className="text-[10px] text-gray-500">1:20</span>
                   <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
                      <div className="h-full bg-primary w-1/3 rounded-full" />
                   </div>
                   <span className="text-[10px] text-gray-500">3:30</span>
                </div>

                <div className="flex justify-center items-center gap-4 mt-4">
                  <Shuffle size={14} className="text-gray-500" />
                  <SkipBack size={18} fill="currentColor" />
                  <button onClick={togglePlay} className="w-10 h-10 rounded-full bg-white text-black flex items-center justify-center">
                    {isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" className="ml-1" />}
                  </button>
                  <SkipForward size={18} fill="currentColor" />
                  <Repeat size={14} className="text-gray-500" />
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Playlist Items Modal */}
      {selectedPlaylist && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-[#140c21] w-full max-w-4xl max-h-[80vh] rounded-3xl overflow-hidden flex flex-col border border-white/10 shadow-2xl">
            <div className="p-6 border-b border-white/5 flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold">{selectedPlaylist.title}</h2>
                <p className="text-sm text-gray-400">{playlistItems.length} Tracks</p>
              </div>
              <div className="flex gap-4">
                <button
                  onClick={() => handleDownload(selectedVideoIds)}
                  disabled={selectedVideoIds.length === 0}
                  className="bg-primary px-6 py-2 rounded-full text-sm font-bold disabled:opacity-50"
                >
                  Download Selected ({selectedVideoIds.length})
                </button>
                <button onClick={() => setSelectedPlaylist(null)} className="p-2 hover:bg-white/5 rounded-full">
                  <SkipBack className="rotate-90" /> {/* Close icon substitute */}
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-2">
              {playlistItems.map((item) => (
                <div key={item.id} className="flex items-center gap-4 p-2 hover:bg-white/5 rounded-xl group transition">
                  <input
                    type="checkbox"
                    checked={selectedVideoIds.includes(item.id)}
                    onChange={() => toggleVideoSelection(item.id)}
                    className="w-4 h-4 rounded border-gray-600 bg-transparent text-primary focus:ring-primary"
                  />
                  <img src={item.thumbnail} className="w-12 h-12 object-cover rounded-lg" />
                  <span className="flex-1 text-sm font-medium truncate">{item.title}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Hidden Audio Element */}
      <audio
        ref={audioRef}
        onTimeUpdate={() => setProgress((audioRef.current.currentTime / audioRef.current.duration) * 100)}
        onEnded={() => setIsPlaying(false)}
      />
    </div>
  );
};

const SidebarItem = ({ icon, label, active, onClick }) => (
  <div
    onClick={onClick}
    className={`flex items-center gap-4 py-3 px-2 rounded-xl cursor-pointer transition-all ${active ? 'bg-primary text-white shadow-lg shadow-purple-500/20' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
  >
    {icon}
    <span className="text-sm font-medium">{label}</span>
  </div>
);

const PlaylistCard = ({ playlist, onDownload, onClick }) => (
  <div className="group relative bg-[#1c132b] rounded-2xl p-4 hover:bg-white/5 transition border border-white/5 cursor-pointer" onClick={onClick}>
    <img src={playlist.thumbnail} className="w-full aspect-square object-cover rounded-xl mb-4 shadow-lg" alt={playlist.title} />
    <h4 className="font-bold text-sm truncate">{playlist.title}</h4>
    <p className="text-xs text-gray-500 mt-1">{playlist.trackCount} Tracks</p>
    <button
      onClick={(e) => { e.stopPropagation(); onDownload(); }}
      className="absolute right-6 bottom-6 w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition shadow-xl"
    >
      <Download size={16} />
    </button>
  </div>
);

const TrendingItem = ({ video, index, onDownload }) => (
  <div className="flex items-center gap-4 group p-2 hover:bg-white/5 rounded-xl transition cursor-pointer">
    <span className="text-gray-600 text-sm font-bold w-4">{index.toString().padStart(2, '0')}</span>
    <img src={video.thumbnail} className="w-12 h-12 object-cover rounded-lg" />
    <div className="flex-1 min-w-0">
      <h4 className="text-sm font-bold truncate">{video.title}</h4>
      <p className="text-xs text-gray-400">YouTube Trending</p>
    </div>
    <span className="text-xs text-gray-500">3:20</span>
    <button onClick={onDownload} className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center group-hover:bg-primary transition text-gray-400 group-hover:text-white">
      <Download size={14} />
    </button>
  </div>
);

const ArtistItem = ({ name, plays, followers }) => (
  <div className="flex items-center gap-4">
    <div className="w-10 h-10 rounded-full bg-white/10 overflow-hidden">
      <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${name}`} alt={name} />
    </div>
    <div className="flex-1">
      <h4 className="text-sm font-bold">{name}</h4>
      <p className="text-[10px] text-gray-500 uppercase tracking-tighter">{followers} Followers • {plays} Plays</p>
    </div>
    <button className="text-gray-500"><MoreHorizontal size={18} /></button>
  </div>
);

export default App;
