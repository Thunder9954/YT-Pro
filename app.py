#!/usr/bin/env python3
"""
YouTube All-in-One Downloader Pro - Web Version
Flask-based web application for YouTube video and audio downloads
"""

import json
import os
import re
import tempfile
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import logging
from concurrent.futures import ThreadPoolExecutor
import uuid

from flask import Flask, render_template, request, jsonify, send_file
from flask_session import Session

try:
    import yt_dlp
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Install: pip install yt-dlp mutagen requests flask flask-session")
    raise SystemExit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = tempfile.mkdtemp()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
Session(app)

# Global download manager
download_manager = None

class YouTubeDownloadManager:
    def __init__(self):
        self.root = Path("YT_Downloads_Web")
        self.root.mkdir(exist_ok=True)
        
        # Current version
        self.version = "2.0.0-web"
        
        # Quality presets for videos
        self.quality_presets = {
            "best": {"video": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "description": "Best quality available"},
            "4k": {"video": "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160]", "description": "4K UHD (2160p)"},
            "1440p": {"video": "bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440]", "description": "2K QHD (1440p)"},
            "1080p": {"video": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]", "description": "Full HD (1080p)"},
            "720p": {"video": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]", "description": "HD (720p)"},
            "480p": {"video": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]", "description": "SD (480p)"},
            "360p": {"video": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]", "description": "Low (360p)"},
            "240p": {"video": "bestvideo[height<=240][ext=mp4]+bestaudio[ext=m4a]/best[height<=240]", "description": "Very Low (240p)"}
        }
        
        # Audio quality presets
        self.audio_presets = {
            "best": {"format": "bestaudio[ext=m4a]/bestaudio", "description": "Best quality audio"},
            "320kbps": {"format": "bestaudio[ext=m4a]/bestaudio", "description": "High quality (320kbps)"},
            "192kbps": {"format": "bestaudio[ext=m4a]/bestaudio", "description": "Good quality (192kbps)"},
            "128kbps": {"format": "bestaudio[ext=m4a]/bestaudio", "description": "Standard (128kbps)"}
        }
        
        # Video formats
        self.video_formats = {
            "mp4": {"name": "MP4", "description": "Universal format (H.264/AAC)"},
            "mkv": {"name": "MKV", "description": "High quality container"},
            "webm": {"name": "WebM", "description": "Web optimized (VP9/Opus)"},
            "avi": {"name": "AVI", "description": "Legacy format"}
        }
        
        # Audio formats
        self.audio_formats = {
            "mp3": {"name": "MP3", "description": "Universal audio (192kbps)", "default_bitrate": "192"},
            "m4a": {"name": "M4A", "description": "Apple audio (AAC)", "default_bitrate": "256"},
            "flac": {"name": "FLAC", "description": "Lossless audio", "default_bitrate": "lossless"},
            "opus": {"name": "Opus", "description": "High efficiency audio", "default_bitrate": "160"},
            "wav": {"name": "WAV", "description": "Uncompressed audio", "default_bitrate": "1411"}
        }
        
        # Active downloads tracking
        self.active_downloads = {}
        self.download_history = []
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Statistics
        self.stats = {
            "total_downloads": 0,
            "video_downloads": 0,
            "audio_downloads": 0,
            "last_download": None,
            "total_size_gb": 0.0
        }
        
        # Load stats if exists
        self.load_stats()

    def load_stats(self) -> None:
        """Load statistics from file"""
        stats_file = self.root / "stats.json"
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    loaded_stats = json.load(f)
                    # Validate loaded data
                    if isinstance(loaded_stats, dict) and all(key in loaded_stats for key in ["total_downloads", "video_downloads", "audio_downloads"]):
                        self.stats = loaded_stats
                    else:
                        logger.warning("Invalid stats file format, using defaults")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Could not load stats: {e}")

    def save_stats(self) -> None:
        """Save statistics to file safely"""
        stats_file = self.root / "stats.json"
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Could not save stats: {e}")

    def clean_filename(self, name: str) -> str:
        """Clean filename to remove invalid characters safely"""
        if not name:
            return "download"
        
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for c in invalid_chars:
            name = name.replace(c, "_")
        
        # Remove control characters
        name = ''.join(char for char in name if ord(char) >= 32)
        
        # Clean whitespace and limit length
        name = re.sub(r"\\s+", " ", name).strip()
        
        # Remove leading/trailing dots and spaces
        name = name.strip('. ')
        
        return name[:150] if len(name) > 150 else name

    def get_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL safely"""
        if not url or not isinstance(url, str):
            return None
        
        try:
            # Parse URL to validate
            parsed = urllib.parse.urlparse(url)
            if not parsed.netloc:
                return None
            
            patterns = [
                r"(?:v=|/)([0-9A-Za-z_-]{11}).*",
                r"(?:embed/)([0-9A-Za-z_-]{11})",
                r"(?:shorts/)([0-9A-Za-z_-]{11})",
                r"youtu\\.be/([0-9A-Za-z_-]{11})"
            ]
            for p in patterns:
                m = re.search(p, url)
                if m:
                    return m.group(1)
        except Exception as e:
            logger.error(f"Error extracting video ID: {e}")
        return None

    def get_info(self, url: str) -> Optional[Dict]:
        """Get video/audio information"""
        try:
            with yt_dlp.YoutubeDL({
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False
            }) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"Failed to fetch info: {e}")
            return None

    def format_size(self, bytes_size: int) -> str:
        """Format file size to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"

    def format_duration(self, seconds: int) -> str:
        """Format duration from seconds to HH:MM:SS"""
        if not seconds:
            return "00:00"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    def update_stats(self, file_size: int, media_type: str) -> None:
        """Update download statistics"""
        self.stats["total_downloads"] += 1
        if media_type == "video":
            self.stats["video_downloads"] += 1
        else:
            self.stats["audio_downloads"] += 1
        self.stats["total_size_gb"] += file_size / (1024**3)
        self.stats["last_download"] = datetime.now().isoformat()
        self.save_stats()

    def progress_callback(self, download_id: str, d: Dict) -> None:
        """Progress callback for downloads"""
        if download_id in self.active_downloads:
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes")
                speed = d.get("speed")
                
                if total and downloaded:
                    pct = downloaded / total * 100
                    mb_downloaded = downloaded / 1024 / 1024
                    mb_total = total / 1024 / 1024
                    
                    speed_str = ""
                    if speed:
                        speed_mb = speed / 1024 / 1024
                        speed_str = f" @ {speed_mb:.1f} MB/s"
                    
                    self.active_downloads[download_id].update({
                        "progress": pct,
                        "downloaded_mb": mb_downloaded,
                        "total_mb": mb_total,
                        "speed": speed_str,
                        "status": "downloading"
                    })
                    
            elif d.get("status") == "finished":
                self.active_downloads[download_id].update({
                    "progress": 100,
                    "status": "processing"
                })

    def download_video(self, download_id: str, url: str, quality: str, container: str) -> bool:
        """Download video with specific quality and format"""
        try:
            # Update download status
            self.active_downloads[download_id].update({
                "status": "fetching_info",
                "progress": 0
            })
            
            info = self.get_info(url)
            if not info:
                self.active_downloads[download_id].update({
                    "status": "error",
                    "error": "Failed to fetch video information"
                })
                return False

            title = self.clean_filename(info.get("title", "video"))
            out_dir = self.root / "Videos" / "Singles"
            out_dir.mkdir(exist_ok=True, parents=True)
            outtmpl = str(out_dir / f"{title}.%(ext)s")

            fmt = self.quality_presets.get(quality, self.quality_presets["720p"])["video"]

            ydl_opts = {
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
                "format": fmt,
                "merge_output_format": container,
                "progress_hooks": [lambda d: self.progress_callback(download_id, d)],
                "postprocessors": [],
                "writethumbnail": True,
                "writesubtitles": False,  # Changed to False to prevent 'Did not get any data blocks' error
                "subtitleslangs": ["en"],
                "subtitlesformat": "srt",
                "embedthumbnail": True,
                "embedsubtitles": False,  # Also disabled since writesubtitles is false
                "concurrent_fragments": 4,
            }

            if container != "webm":
                ydl_opts["postprocessors"].extend([
                    {"key": "FFmpegVideoConvertor", "preferedformat": container},
                    {"key": "EmbedThumbnail"},
                ])

            self.active_downloads[download_id].update({
                "status": "downloading",
                "title": title,
                "quality": quality,
                "format": container
            })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Update statistics
            output_file = out_dir / f"{title}.{container}"
            if output_file.exists():
                file_size = output_file.stat().st_size
                self.update_stats(file_size, "video")
                
                self.active_downloads[download_id].update({
                    "status": "completed",
                    "progress": 100,
                    "file_size": self.format_size(file_size),
                    "file_path": str(output_file.relative_to(self.root))
                })
                
                # Add to history
                self.download_history.append({
                    "id": download_id,
                    "type": "video",
                    "title": title,
                    "url": url,
                    "quality": quality,
                    "format": container,
                    "file_size": self.format_size(file_size),
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed"
                })
                
                return True
            else:
                self.active_downloads[download_id].update({
                    "status": "error",
                    "error": "Output file not found after download"
                })
                return False
            
        except Exception as e:
            logger.error(f"Video download failed: {e}")
            self.active_downloads[download_id].update({
                "status": "error",
                "error": str(e)
            })
            return False

    def download_audio(self, download_id: str, url: str, audio_format: str, bitrate: str = "192") -> bool:
        """Download audio with optional metadata embedding"""
        try:
            # Update download status
            self.active_downloads[download_id].update({
                "status": "fetching_info",
                "progress": 0
            })
            
            info = self.get_info(url)
            if not info:
                self.active_downloads[download_id].update({
                    "status": "error",
                    "error": "Failed to fetch audio information"
                })
                return False

            title = self.clean_filename(info.get("title", "audio"))
            out_dir = self.root / "Music" / "Singles"
            out_dir.mkdir(exist_ok=True, parents=True)
            outtmpl = str(out_dir / f"{title}.%(ext)s")

            ydl_opts = {
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
                "format": "bestaudio[ext=m4a]/bestaudio",
                "progress_hooks": [lambda d: self.progress_callback(download_id, d)],
                "postprocessors": [],
                "writethumbnail": True,
                "writeinfojson": True,
            }

            # Configure postprocessors based on format
            if audio_format == "m4a":
                # Keep as is
                pass
            elif audio_format == "mp3":
                ydl_opts["postprocessors"].append({
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate,
                })
            elif audio_format == "flac":
                ydl_opts["postprocessors"].append({
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "flac",
                })
            elif audio_format == "opus":
                ydl_opts["postprocessors"].append({
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "opus",
                    "preferredquality": "192",
                })
            elif audio_format == "wav":
                ydl_opts["postprocessors"].append({
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                })

            # Add metadata embedding
            ydl_opts["postprocessors"].extend([
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail"},
            ])
            ydl_opts["embedthumbnail"] = True

            self.active_downloads[download_id].update({
                "status": "downloading",
                "title": title,
                "quality": bitrate,
                "format": audio_format
            })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Update statistics
            output_file = out_dir / f"{title}.{audio_format}"
            if output_file.exists():
                file_size = output_file.stat().st_size
                self.update_stats(file_size, "audio")
                
                self.active_downloads[download_id].update({
                    "status": "completed",
                    "progress": 100,
                    "file_size": self.format_size(file_size),
                    "file_path": str(output_file.relative_to(self.root))
                })
                
                # Add to history
                self.download_history.append({
                    "id": download_id,
                    "type": "audio",
                    "title": title,
                    "url": url,
                    "quality": bitrate,
                    "format": audio_format,
                    "file_size": self.format_size(file_size),
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed"
                })
                
                return True
            else:
                self.active_downloads[download_id].update({
                    "status": "error",
                    "error": "Output file not found after download"
                })
                return False
            
        except Exception as e:
            logger.error(f"Audio download failed: {e}")
            self.active_downloads[download_id].update({
                "status": "error",
                "error": str(e)
            })
            return False

    def start_download(self, url: str, media_type: str, quality: str, format_type: str, bitrate: str = "192") -> str:
        """Start a new download"""
        download_id = str(uuid.uuid4())
        
        self.active_downloads[download_id] = {
            "id": download_id,
            "url": url,
            "type": media_type,
            "quality": quality,
            "format": format_type,
            "bitrate": bitrate,
            "status": "queued",
            "progress": 0,
            "started_at": datetime.now().isoformat()
        }
        
        # Submit download to thread pool
        if media_type == "video":
            self.executor.submit(self.download_video, download_id, url, quality, format_type)
        else:
            self.executor.submit(self.download_audio, download_id, url, format_type, bitrate)
        
        return download_id

    def get_download_status(self, download_id: str) -> Optional[Dict]:
        """Get status of a specific download"""
        return self.active_downloads.get(download_id)

    def get_all_downloads(self) -> List[Dict]:
        """Get all active downloads"""
        return list(self.active_downloads.values())

    def get_download_history(self, limit: int = 50) -> List[Dict]:
        """Get download history"""
        return sorted(self.download_history, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]

# Initialize download manager
download_manager = YouTubeDownloadManager()

# Routes
@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', 
                         version=download_manager.version,
                         stats=download_manager.stats)

@app.route('/api/info')
def get_video_info():
    """Get video information"""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    info = download_manager.get_info(url)
    if not info:
        return jsonify({'error': 'Failed to fetch video information'}), 400
    
    # Format response
    response = {
        'title': info.get('title', 'Unknown'),
        'uploader': info.get('uploader', 'Unknown'),
        'duration': download_manager.format_duration(info.get('duration', 0)),
        'duration_seconds': info.get('duration', 0),
        'views': info.get('view_count', 0),
        'upload_date': info.get('upload_date', 'Unknown'),
        'description': (info.get('description') or '')[:500],
        'thumbnail': info.get('thumbnail', ''),
        'formats': []
    }
    
    # Add available formats
    if 'formats' in info:
        formats = info['formats']
        video_formats = [f for f in formats if f.get('vcodec') != 'none']
        audio_formats = [f for f in formats if f.get('acodec') != 'none']
        
        # Video formats
        video_qualities = set()
        for fmt in video_formats:
            height = fmt.get('height')
            if height:
                video_qualities.add(f"{height}p")
        
        # Audio formats
        audio_bitrates = set()
        for fmt in audio_formats:
            abr = fmt.get('abr')
            if abr:
                audio_bitrates.add(f"{int(abr)}kbps")
        
        response['formats'] = {
            'video': sorted(list(video_qualities), key=lambda x: int(x.replace('p', '')), reverse=True),
            'audio': sorted(list(audio_bitrates), key=lambda x: int(x.replace('kbps', '')), reverse=True)
        }
    
    return jsonify(response)

@app.route('/api/download', methods=['POST'])
def start_download():
    """Start a new download"""
    data = request.get_json()
    
    url = data.get('url')
    media_type = data.get('type')  # 'video' or 'audio'
    quality = data.get('quality', '720p')
    format_type = data.get('format', 'mp4')
    bitrate = data.get('bitrate', '192')
    
    if not url or not media_type:
        return jsonify({'error': 'URL and type are required'}), 400
    
    # Validate media type
    if media_type not in ['video', 'audio']:
        return jsonify({'error': 'Invalid media type'}), 400
    
    # Start download
    download_id = download_manager.start_download(url, media_type, quality, format_type, bitrate)
    
    return jsonify({
        'download_id': download_id,
        'message': 'Download started'
    })

@app.route('/api/download/<download_id>')
def get_download_status(download_id):
    """Get download status"""
    status = download_manager.get_download_status(download_id)
    if not status:
        return jsonify({'error': 'Download not found'}), 404
    
    return jsonify(status)

@app.route('/api/downloads')
def get_all_downloads():
    """Get all active downloads"""
    downloads = download_manager.get_all_downloads()
    return jsonify(downloads)

@app.route('/api/history')
def get_download_history():
    """Get download history"""
    history = download_manager.get_download_history()
    return jsonify(history)

@app.route('/api/stats')
def get_stats():
    """Get download statistics"""
    return jsonify(download_manager.stats)

@app.route('/download/<path:filename>')
def download_file(filename):
    """Download a file"""
    try:
        file_path = download_manager.root / filename
        if file_path.exists() and file_path.is_file():
            return send_file(str(file_path), as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error serving file: {e}")
        return jsonify({'error': 'Failed to serve file'}), 500

@app.route('/api/presets')
def get_presets():
    """Get quality and format presets"""
    return jsonify({
        'video_qualities': download_manager.quality_presets,
        'audio_qualities': download_manager.audio_presets,
        'video_formats': download_manager.video_formats,
        'audio_formats': download_manager.audio_formats
    })

# Template HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube All-in-One Downloader Pro - Web Version</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
    <style>
        .download-progress {
            transition: width 0.3s ease;
        }
        .fade-in {
            animation: fadeIn 0.5s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <!-- Header -->
    <header class="bg-gradient-to-r from-red-600 to-red-700 text-white shadow-lg">
        <div class="container mx-auto px-4 py-6">
            <div class="flex flex-col md:flex-row items-center justify-between space-y-4 md:space-y-0">
                <div class="flex items-center space-x-4">
                    <svg class="w-10 h-10 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                    </svg>
                    <div class="text-center md:text-left">
                        <h1 class="text-xl md:text-2xl font-bold">YouTube Downloader Pro</h1>
                        <p class="text-red-100 text-sm">Web Version {{ version }}</p>
                    </div>
                </div>
                <div class="flex items-center justify-center space-x-6 text-sm w-full md:w-auto">
                    <div class="text-center">
                        <div class="font-bold text-lg">{{ stats.total_downloads }}</div>
                        <div class="text-red-100">Downloads</div>
                    </div>
                    <div class="text-center">
                        <div class="font-bold text-lg">{{ "%.1f"|format(stats.total_size_gb) }} GB</div>
                        <div class="text-red-100">Total Size</div>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="container mx-auto px-2 sm:px-4 py-6 md:py-8">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 md:gap-8">
            <!-- Download Form -->
            <div class="lg:col-span-2">
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-xl font-bold mb-6 text-gray-800">Download Media</h2>
                    
                    <!-- URL Input -->
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Video/Audio URL</label>
                        <input type="url" id="videoUrl" placeholder="https://www.youtube.com/watch?v=..." 
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent">
                    </div>

                    <!-- Media Type Selection -->
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Media Type</label>
                        <div class="grid grid-cols-2 gap-4">
                            <button onclick="selectMediaType('video')" id="videoBtn" 
                                    class="media-type-btn px-4 py-3 border-2 border-red-500 text-red-500 rounded-lg hover:bg-red-50 transition">
                                <svg class="w-6 h-6 mx-auto mb-1" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/>
                                </svg>
                                Video
                            </button>
                            <button onclick="selectMediaType('audio')" id="audioBtn"
                                    class="media-type-btn px-4 py-3 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition">
                                <svg class="w-6 h-6 mx-auto mb-1" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
                                </svg>
                                Audio
                            </button>
                        </div>
                    </div>

                    <!-- Video Options -->
                    <div id="videoOptions" class="mb-6 hidden">
                        <div class="grid md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">Quality</label>
                                <select id="videoQuality" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500">
                                    <option value="best">Best Available</option>
                                    <option value="4k">4K (2160p)</option>
                                    <option value="1440p">1440p</option>
                                    <option value="1080p" selected>1080p</option>
                                    <option value="720p">720p</option>
                                    <option value="480p">480p</option>
                                    <option value="360p">360p</option>
                                    <option value="240p">240p</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2 mt-4 md:mt-0">Format</label>
                                <select id="videoFormat" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500">
                                    <option value="mp4" selected>MP4</option>
                                    <option value="mkv">MKV</option>
                                    <option value="webm">WebM</option>
                                    <option value="avi">AVI</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <!-- Audio Options -->
                    <div id="audioOptions" class="mb-6 hidden">
                        <div class="grid md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">Format</label>
                                <select id="audioFormat" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500">
                                    <option value="mp3" selected>MP3</option>
                                    <option value="m4a">M4A</option>
                                    <option value="flac">FLAC</option>
                                    <option value="opus">Opus</option>
                                    <option value="wav">WAV</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2 mt-4 md:mt-0">Bitrate</label>
                                <select id="audioBitrate" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500">
                                    <option value="320">320 kbps</option>
                                    <option value="256">256 kbps</option>
                                    <option value="192" selected>192 kbps</option>
                                    <option value="128">128 kbps</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <!-- Video Info Display -->
                    <div id="videoInfo" class="mb-6 hidden">
                        <div class="bg-gray-50 rounded-lg p-4">
                            <h3 class="font-semibold text-gray-800 mb-2">Video Information</h3>
                            <div id="videoInfoContent"></div>
                        </div>
                    </div>

                    <!-- Download Button -->
                    <button onclick="startDownload()" id="downloadBtn" disabled
                            class="w-full bg-red-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition">
                        Get Video Info First
                    </button>
                </div>

                <!-- Active Downloads -->
                <div class="bg-white rounded-lg shadow-md p-6 mt-8">
                    <h2 class="text-xl font-bold mb-6 text-gray-800">Active Downloads</h2>
                    <div id="activeDownloads" class="space-y-4">
                        <p class="text-gray-500 text-center py-8">No active downloads</p>
                    </div>
                </div>
            </div>

            <!-- Sidebar -->
            <div class="lg:col-span-1">
                <!-- Statistics -->
                <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                    <h2 class="text-xl font-bold mb-4 text-gray-800">Statistics</h2>
                    <div class="space-y-3">
                        <div class="flex justify-between">
                            <span class="text-gray-600">Video Downloads:</span>
                            <span class="font-semibold">{{ stats.video_downloads }}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Audio Downloads:</span>
                            <span class="font-semibold">{{ stats.audio_downloads }}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Total Size:</span>
                            <span class="font-semibold">{{ "%.1f"|format(stats.total_size_gb) }} GB</span>
                        </div>
                    </div>
                </div>

                <!-- Recent Downloads -->
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-xl font-bold mb-4 text-gray-800">Recent Downloads</h2>
                    <div id="recentDownloads" class="space-y-3">
                        <p class="text-gray-500 text-center py-4">No recent downloads</p>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script>
        let selectedMediaType = 'video';
        let currentDownloads = {};
        let videoInfoData = null;

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            selectMediaType('video');
            loadDownloadHistory();
            setInterval(updateActiveDownloads, 2000);
        });

        function selectMediaType(type) {
            selectedMediaType = type;
            
            // Update button styles
            document.querySelectorAll('.media-type-btn').forEach(btn => {
                btn.classList.remove('border-red-500', 'text-red-500', 'bg-red-50');
                btn.classList.add('border-gray-300', 'text-gray-700');
            });
            
            const selectedBtn = document.getElementById(type + 'Btn');
            selectedBtn.classList.remove('border-gray-300', 'text-gray-700');
            selectedBtn.classList.add('border-red-500', 'text-red-500', 'bg-red-50');
            
            // Show/hide options
            document.getElementById('videoOptions').classList.toggle('hidden', type !== 'video');
            document.getElementById('audioOptions').classList.toggle('hidden', type !== 'audio');
        }

        async function getVideoInfo() {
            const url = document.getElementById('videoUrl').value.trim();
            if (!url) {
                alert('Please enter a video URL');
                return;
            }

            const downloadBtn = document.getElementById('downloadBtn');
            downloadBtn.textContent = 'Fetching Info...';
            downloadBtn.disabled = true;

            try {
                const response = await axios.get('/api/info?url=' + encodeURIComponent(url));
                videoInfoData = response.data;
                
                displayVideoInfo(videoInfoData);
                downloadBtn.textContent = 'Start Download';
                downloadBtn.disabled = false;
            } catch (error) {
                console.error('Error fetching video info:', error);
                alert('Failed to fetch video information. Please check the URL and try again.');
                downloadBtn.textContent = 'Get Video Info First';
                downloadBtn.disabled = true;
            }
        }

        function displayVideoInfo(info) {
            const videoInfoDiv = document.getElementById('videoInfo');
            const contentDiv = document.getElementById('videoInfoContent');
            
            contentDiv.innerHTML = `
                <div class="space-y-2">
                    <div><strong>Title:</strong> ${info.title}</div>
                    <div><strong>Channel:</strong> ${info.uploader}</div>
                    <div><strong>Duration:</strong> ${info.duration}</div>
                    <div><strong>Views:</strong> ${info.views.toLocaleString()}</div>
                    ${info.description ? `<div><strong>Description:</strong> ${info.description}</div>` : ''}
                </div>
            `;
            
            videoInfoDiv.classList.remove('hidden');
            videoInfoDiv.classList.add('fade-in');
        }

        async function startDownload() {
            if (!videoInfoData) {
                await getVideoInfo();
                return;
            }

            const url = document.getElementById('videoUrl').value.trim();
            const quality = selectedMediaType === 'video' ? 
                document.getElementById('videoQuality').value : 
                document.getElementById('audioBitrate').value;
            const format = selectedMediaType === 'video' ? 
                document.getElementById('videoFormat').value : 
                document.getElementById('audioFormat').value;
            const bitrate = selectedMediaType === 'audio' ? 
                document.getElementById('audioBitrate').value : '192';

            const downloadBtn = document.getElementById('downloadBtn');
            downloadBtn.textContent = 'Starting Download...';
            downloadBtn.disabled = true;

            try {
                const response = await axios.post('/api/download', {
                    url: url,
                    type: selectedMediaType,
                    quality: quality,
                    format: format,
                    bitrate: bitrate
                });

                const downloadId = response.data.download_id;
                currentDownloads[downloadId] = {
                    id: downloadId,
                    url: url,
                    type: selectedMediaType,
                    title: videoInfoData.title,
                    status: 'queued'
                };

                // Reset form
                document.getElementById('videoUrl').value = '';
                document.getElementById('videoInfo').classList.add('hidden');
                videoInfoData = null;
                downloadBtn.textContent = 'Get Video Info First';
                
                // Start monitoring
                updateActiveDownloads();
                
            } catch (error) {
                console.error('Error starting download:', error);
                alert('Failed to start download. Please try again.');
                downloadBtn.textContent = 'Start Download';
                downloadBtn.disabled = false;
            }
        }

        async function updateActiveDownloads() {
            try {
                const response = await axios.get('/api/downloads');
                const downloads = response.data;
                
                const container = document.getElementById('activeDownloads');
                
                if (downloads.length === 0) {
                    container.innerHTML = '<p class="text-gray-500 text-center py-8">No active downloads</p>';
                    return;
                }

                container.innerHTML = downloads.map(download => `
                    <div class="border rounded-lg p-4 fade-in">
                        <div class="flex justify-between items-start mb-2">
                            <div class="flex-1">
                                <h4 class="font-semibold text-gray-800">${download.title || 'Loading...'}</h4>
                                <p class="text-sm text-gray-600">${download.type} • ${download.quality} • ${download.format}</p>
                            </div>
                            <span class="px-2 py-1 text-xs rounded-full ${getStatusClass(download.status)}">
                                ${download.status}
                            </span>
                        </div>
                        ${download.status === 'downloading' ? `
                            <div class="mt-3">
                                <div class="flex justify-between text-sm text-gray-600 mb-1">
                                    <span>${download.downloaded_mb ? download.downloaded_mb.toFixed(1) : '0'} MB / ${download.total_mb ? download.total_mb.toFixed(1) : '0'} MB</span>
                                    <span>${download.progress ? download.progress.toFixed(1) : 0}% ${download.speed || ''}</span>
                                </div>
                                <div class="w-full bg-gray-200 rounded-full h-2">
                                    <div class="download-progress bg-red-600 h-2 rounded-full" style="width: ${download.progress || 0}%"></div>
                                </div>
                            </div>
                        ` : ''}
                        ${download.status === 'completed' ? `
                            <div class="mt-2 text-sm text-green-600">
                                ✓ Completed • ${download.file_size || 'Unknown size'}
                                ${download.file_path ? `<a href="/download/${download.file_path}" class="ml-2 text-blue-600 hover:underline">Download File</a>` : ''}
                            </div>
                        ` : ''}
                        ${download.status === 'error' ? `
                            <div class="mt-2 text-sm text-red-600">
                                ✗ Error: ${download.error || 'Unknown error'}
                            </div>
                        ` : ''}
                    </div>
                `).join('');

            } catch (error) {
                console.error('Error updating downloads:', error);
            }
        }

        function getStatusClass(status) {
            switch(status) {
                case 'completed': return 'bg-green-100 text-green-800';
                case 'downloading': return 'bg-blue-100 text-blue-800';
                case 'error': return 'bg-red-100 text-red-800';
                case 'queued': return 'bg-yellow-100 text-yellow-800';
                default: return 'bg-gray-100 text-gray-800';
            }
        }

        async function loadDownloadHistory() {
            try {
                const response = await axios.get('/api/history');
                const history = response.data;
                
                const container = document.getElementById('recentDownloads');
                
                if (history.length === 0) {
                    container.innerHTML = '<p class="text-gray-500 text-center py-4">No recent downloads</p>';
                    return;
                }

                container.innerHTML = history.slice(0, 5).map(item => `
                    <div class="border-l-4 border-red-500 pl-3 py-2">
                        <div class="font-medium text-sm text-gray-800">${item.title}</div>
                        <div class="text-xs text-gray-600">${item.type} • ${item.format} • ${item.file_size}</div>
                        <div class="text-xs text-gray-500">${new Date(item.timestamp).toLocaleString()}</div>
                    </div>
                `).join('');

            } catch (error) {
                console.error('Error loading history:', error);
            }
        }

        // Auto-get info when URL is pasted
        document.getElementById('videoUrl').addEventListener('paste', function() {
            setTimeout(getVideoInfo, 500);
        });
    </script>
</body>
</html>
"""

# Template route
@app.route('/index.html')
def index_template():
    """Serve the main template"""
    return HTML_TEMPLATE

# Initialize templates on app load for WSGI
os.makedirs('templates', exist_ok=True)
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(HTML_TEMPLATE)

if __name__ == '__main__':
    print("Starting YouTube Downloader Pro - Web Version")
    print(f"Version: {download_manager.version}")
    print(f"Downloads folder: {download_manager.root.absolute()}")
    print("Open http://localhost:5000 in your browser")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
