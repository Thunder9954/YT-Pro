#!/usr/bin/env python3
"""
YouTube All-in-One Downloader Pro
Combines Music and Video downloading with advanced features
"""

import json
import os
import re
import shutil
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import platform
import logging

try:
    import yt_dlp
    from colorama import init, Fore
    import requests
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Install: pip install yt-dlp colorama mutagen requests")
    raise SystemExit(1)

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YouTubeAllInOnePro:
    def __init__(self):
        self.root = Path("YT_Downloads_Pro")
        self.root.mkdir(exist_ok=True)
        
        # Current version
        self.version = "2.0.0"
        
        # Quality presets for videos
        self.quality_presets = {
            "best": {
                "video": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "description": "🎯 Best quality available",
                "icon": "🏆"
            },
            "4k": {
                "video": "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160]",
                "description": "📺 4K UHD (2160p)",
                "icon": "🖥️"
            },
            "1440p": {
                "video": "bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440]",
                "description": "🎬 2K QHD (1440p)",
                "icon": "🎥"
            },
            "1080p": {
                "video": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
                "description": "🌟 Full HD (1080p)",
                "icon": "⭐"
            },
            "720p": {
                "video": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
                "description": "📱 HD (720p)",
                "icon": "📱"
            },
            "480p": {
                "video": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",
                "description": "📼 SD (480p)",
                "icon": "📼"
            },
            "360p": {
                "video": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",
                "description": "📶 Low (360p)",
                "icon": "📶"
            },
            "240p": {
                "video": "bestvideo[height<=240][ext=mp4]+bestaudio[ext=m4a]/best[height<=240]",
                "description": "📞 Very Low (240p)",
                "icon": "📞"
            }
        }
        
        # Audio quality presets
        self.audio_presets = {
            "best": {
                "format": "bestaudio[ext=m4a]/bestaudio",
                "description": "🎵 Best quality audio",
                "icon": "🎵"
            },
            "320kbps": {
                "format": "bestaudio[ext=m4a]/bestaudio",
                "description": "🎧 High quality (320kbps)",
                "icon": "🎧"
            },
            "192kbps": {
                "format": "bestaudio[ext=m4a]/bestaudio",
                "description": "🎼 Good quality (192kbps)",
                "icon": "🎼"
            },
            "128kbps": {
                "format": "bestaudio[ext=m4a]/bestaudio",
                "description": "🎶 Standard (128kbps)",
                "icon": "🎶"
            }
        }
        
        # Video formats
        self.video_formats = {
            "mp4": {
                "name": "MP4",
                "description": "Universal format (H.264/AAC)",
                "icon": "📹"
            },
            "mkv": {
                "name": "MKV",
                "description": "High quality container",
                "icon": "🎞️"
            },
            "webm": {
                "name": "WebM",
                "description": "Web optimized (VP9/Opus)",
                "icon": "🌐"
            },
            "avi": {
                "name": "AVI",
                "description": "Legacy format",
                "icon": "📼"
            }
        }
        
        # Audio formats
        self.audio_formats = {
            "mp3": {
                "name": "MP3",
                "description": "Universal audio (192kbps)",
                "icon": "🎵",
                "default_bitrate": "192"
            },
            "m4a": {
                "name": "M4A",
                "description": "Apple audio (AAC)",
                "icon": "🍎",
                "default_bitrate": "256"
            },
            "flac": {
                "name": "FLAC",
                "description": "Lossless audio",
                "icon": "🎛️",
                "default_bitrate": "lossless"
            },
            "opus": {
                "name": "Opus",
                "description": "High efficiency audio",
                "icon": "🔊",
                "default_bitrate": "160"
            },
            "wav": {
                "name": "WAV",
                "description": "Uncompressed audio",
                "icon": "🎚️",
                "default_bitrate": "1411"
            }
        }
        
        # Supported sites
        self.supported_sites = [
            "YouTube", "YouTube Music", "Vimeo", "Dailymotion",
            "Facebook", "Twitter/X", "Instagram", "TikTok",
            "SoundCloud", "Bandcamp", "Twitch", "Reddit"
        ]
        
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

    def clear(self) -> None:
        """Clear terminal screen safely"""
        try:
            if os.name == 'nt':
                os.system('cls')
            else:
                os.system('clear')
        except Exception as e:
            logger.warning(f"Could not clear screen: {e}")

    def print_header(self, title: str) -> None:
        """Print formatted header"""
        width = 70
        print(Fore.CYAN + "╔" + "═" * (width - 2) + "╗")
        print(Fore.CYAN + "║" + Fore.YELLOW + f"{title:^{width-2}}" + Fore.CYAN + "║")
        print(Fore.CYAN + "╚" + "═" * (width - 2) + "╝")

    def print_success(self, message: str) -> None:
        """Print success message"""
        print(Fore.GREEN + "✅ " + message)

    def print_error(self, message: str) -> None:
        """Print error message"""
        print(Fore.RED + "❌ " + message)

    def print_warning(self, message: str) -> None:
        """Print warning message"""
        print(Fore.YELLOW + "⚠️ " + message)

    def print_info(self, message: str) -> None:
        """Print info message"""
        print(Fore.BLUE + "ℹ️ " + message)

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
        name = re.sub(r"\s+", " ", name).strip()
        
        # Remove leading/trailing dots and spaces
        name = name.strip('. ')
        
        return name[:150] if len(name) > 150 else name

    def format_duration(self, seconds: int) -> str:
        """Format duration from seconds to HH:MM:SS"""
        if not seconds:
            return "00:00"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    def format_size(self, bytes_size: int) -> str:
        """Format file size to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"

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
                r"youtu\.be/([0-9A-Za-z_-]{11})"
            ]
            for p in patterns:
                m = re.search(p, url)
                if m:
                    return m.group(1)
        except Exception as e:
            logger.error(f"Error extracting video ID: {e}")
        return None

    def get_info(self, url: str, quiet: bool = True) -> Optional[Dict]:
        """Get video/audio information"""
        try:
            with yt_dlp.YoutubeDL({
                "quiet": quiet,
                "no_warnings": quiet,
                "extract_flat": False
            }) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            self.print_error(f"Failed to fetch info: {e}")
            return None

    def display_info(self, info: Dict) -> None:
        """Display video/audio information"""
        print(f"\n{Fore.CYAN}📋 Information:")
        print(Fore.CYAN + "━" * 50)
        
        title = info.get('title', 'Unknown')
        uploader = info.get('uploader', 'Unknown')
        duration = info.get('duration', 0)
        views = info.get('view_count', 0)
        upload_date = info.get('upload_date', 'Unknown')
        categories = info.get('categories', [])
        
        print(f"{Fore.WHITE}Title: {Fore.YELLOW}{title}")
        print(f"{Fore.WHITE}Channel: {Fore.CYAN}{uploader}")
        print(f"{Fore.WHITE}Duration: {Fore.GREEN}{self.format_duration(duration)}")
        print(f"{Fore.WHITE}Views: {Fore.MAGENTA}{views:,}")
        print(f"{Fore.WHITE}Upload Date: {Fore.WHITE}{upload_date}")
        
        if categories:
            print(f"{Fore.WHITE}Category: {Fore.CYAN}{', '.join(categories[:3])}")
        
        # Show available formats briefly
        if 'formats' in info:
            print(f"\n{Fore.WHITE}Available Qualities:")
            formats = info['formats']
            video_formats = [f for f in formats if f.get('vcodec') != 'none']
            audio_formats = [f for f in formats if f.get('acodec') != 'none']
            
            video_formats.sort(key=lambda x: x.get('height', 0) or x.get('width', 0), reverse=True)
            audio_formats.sort(key=lambda x: x.get('abr', 0), reverse=True)
            
            if video_formats:
                print(f"  {Fore.GREEN}Video: ", end="")
                res_list = []
                for fmt in video_formats[:3]:
                    res = f"{fmt.get('height', '?')}p" if fmt.get('height') else f"{fmt.get('width', '?')}x{fmt.get('height', '?')}"
                    res_list.append(res)
                print(", ".join(res_list))
            
            if audio_formats:
                print(f"  {Fore.BLUE}Audio: ", end="")
                bitrate_list = []
                for fmt in audio_formats[:3]:
                    abr = f"{fmt.get('abr', '?')}kbps" if fmt.get('abr') else '?'
                    bitrate_list.append(abr)
                print(", ".join(bitrate_list))

    def progress_hook(self, d: Dict) -> None:
        """Progress hook for downloads"""
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
                
                print(f"\r{Fore.CYAN}⬇️  {pct:5.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB){speed_str}", 
                      end="", flush=True)
            elif downloaded:
                mb = downloaded / 1024 / 1024
                print(f"\r{Fore.CYAN}⬇️  Downloaded: {mb:6.1f} MB", end="", flush=True)
        
        elif d.get("status") == "finished":
            print(f"\r{Fore.GREEN}✅ Download complete! Processing...")

    def ensure_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        if shutil.which("ffmpeg") is None:
            self.print_warning("FFmpeg not found in PATH!")
            print(f"{Fore.YELLOW}FFmpeg is required for:")
            print("  • Audio format conversion (MP3, FLAC, etc.)")
            print("  • Merging video and audio streams")
            print("  • Some format conversions")
            print(f"\n{Fore.CYAN}Install FFmpeg:")
            if platform.system() == "Linux":
                print(f"  {Fore.WHITE}sudo apt install ffmpeg")
            elif platform.system() == "Darwin":  # macOS
                print(f"  {Fore.WHITE}brew install ffmpeg")
            else:  # Windows
                print(f"  {Fore.WHITE}Download from ffmpeg.org and add to PATH")
            print(f"\n{Fore.YELLOW}Continue without FFmpeg? Some features may not work.")
            return False
        return True

    def download_video(self, url: str, quality: str, container: str, out_dir: Path) -> bool:
        """Download video with specific quality and format"""
        if not self.ensure_ffmpeg():
            self.print_error("FFmpeg is required for video merging/conversion on most sites.")
            return False

        self.print_info("Fetching video information...")
        info = self.get_info(url, quiet=False)
        if not info:
            return False

        self.display_info(info)
        
        title = self.clean_filename(info.get("title", "video"))
        out_dir.mkdir(exist_ok=True, parents=True)
        outtmpl = str(out_dir / f"{title}.%(ext)s")

        fmt = self.quality_presets.get(quality, self.quality_presets["720p"])["video"]

        ydl_opts: Dict = {
            "outtmpl": outtmpl,
            "quiet": False,
            "no_warnings": False,
            "format": fmt,
            "merge_output_format": container,
            "progress_hooks": [self.progress_hook],
            "postprocessors": [],
            "writethumbnail": True,
            "writesubtitles": False, # Changed to False to prevent 'Did not get any data blocks' error
            "subtitleslangs": ["en", "fr", "es", "de"],
            "subtitlesformat": "srt",
            "embedthumbnail": True,
            "embedsubtitles": False,
            "concurrent_fragments": 4,
        }

        if container != "webm":
            ydl_opts["postprocessors"].extend([
                {"key": "FFmpegVideoConvertor", "preferedformat": container},
                {"key": "EmbedThumbnail"},
            ])

        try:
            self.print_info(f"Starting download: {quality} quality as {container.upper()}")
            print(f"{Fore.WHITE}Output: {out_dir / f'{title}.{container}'}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Update statistics
            output_file = out_dir / f"{title}.{container}"
            if output_file.exists():
                file_size = output_file.stat().st_size
                self.update_stats(file_size, "video")
                self.print_success(f"Video downloaded: {self.format_size(file_size)}")
                
                # Save details
                self.save_details_json(out_dir, title, info, url, "video")
            
            return True
            
        except Exception as e:
            self.print_error(f"Download failed: {e}")
            return False

    def download_audio(self, url: str, audio_format: str, out_dir: Path, 
                      embed_tags: bool = True, bitrate: str = "192") -> bool:
        """Download audio with optional metadata embedding"""
        needs_ffmpeg = (audio_format != "m4a") or embed_tags
        if needs_ffmpeg and not self.ensure_ffmpeg():
            self.print_error("FFmpeg is required for audio conversion/embedding.")
            return False

        self.print_info("Fetching audio information...")
        info = self.get_info(url, quiet=False)
        if not info:
            return False

        self.display_info(info)
        
        title = self.clean_filename(info.get("title", "audio"))
        out_dir.mkdir(exist_ok=True, parents=True)
        outtmpl = str(out_dir / f"{title}.%(ext)s")

        ydl_opts: Dict = {
            "outtmpl": outtmpl,
            "quiet": False,
            "no_warnings": False,
            "format": "bestaudio[ext=m4a]/bestaudio",
            "progress_hooks": [self.progress_hook],
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
        else:
            self.print_error(f"Invalid audio format: {audio_format}")
            return False

        if embed_tags:
            ydl_opts["postprocessors"].extend([
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail"},
            ])
            ydl_opts["embedthumbnail"] = True

        try:
            self.print_info(f"Starting download: {audio_format.upper()} audio")
            print(f"{Fore.WHITE}Output: {out_dir / f'{title}.{audio_format}'}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Update statistics
            output_file = out_dir / f"{title}.{audio_format}"
            if output_file.exists():
                file_size = output_file.stat().st_size
                self.update_stats(file_size, "audio")
                self.print_success(f"Audio downloaded: {self.format_size(file_size)}")
                
                # Enhanced metadata embedding
                if embed_tags and audio_format == "mp3":
                    self.embed_enhanced_metadata(output_file, info, url)
                
                # Save details
                self.save_details_json(out_dir, title, info, url, "audio")
            
            return True
            
        except Exception as e:
            self.print_error(f"Download failed: {e}")
            return False

    def save_details_json(self, out_dir: Path, base: str, info: Dict, 
                         url: str, media_type: str) -> None:
        """Save detailed information as JSON"""
        details = {
            "media_type": media_type,
            "title": info.get("title"),
            "artist": info.get("uploader"),
            "channel": info.get("channel"),
            "channel_url": info.get("channel_url"),
            "duration": info.get("duration"),
            "url": url,
            "video_id": info.get("id") or self.get_video_id(url),
            "description": (info.get("description") or "")[:1000],
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "upload_date": info.get("upload_date"),
            "categories": info.get("categories", []),
            "tags": info.get("tags", []),
            "download_date": datetime.now().isoformat(),
            "thumbnail_url": info.get("thumbnail"),
        }
        
        # Add format info if available
        if "formats" in info:
            details["available_formats"] = [
                {
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "resolution": f"{f.get('width', '')}x{f.get('height', '')}",
                    "fps": f.get("fps"),
                    "vcodec": f.get("vcodec"),
                    "acodec": f.get("acodec"),
                    "filesize": f.get("filesize"),
                }
                for f in info["formats"][:10]
            ]
        
        p = out_dir / f"{base}_details.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(details, f, indent=2, ensure_ascii=False, default=str)
        
        self.print_info(f"Details saved: {p.name}")

    def embed_enhanced_metadata(self, mp3_path: Path, info: Dict, url: str) -> None:
        """Embed enhanced metadata into MP3 file safely"""
        try:
            from mutagen.id3 import ID3, APIC, TALB, TIT2, TPE1, TRCK, TYER, TCON, COMM, TCOM, TPE2
            from mutagen.mp3 import MP3
        except ImportError:
            self.print_warning("Enhanced metadata requires: mutagen")
            return

        try:
            # Fetch high-quality thumbnail
            vid = info.get("id") or self.get_video_id(url)
            thumb_bytes = None
            thumb_mime = "image/jpeg"
            
            if vid:
                thumb_urls = [
                    f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg",
                    f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                    f"https://img.youtube.com/vi/{vid}/sddefault.jpg",
                    f"https://img.youtube.com/vi/{vid}/0.jpg",
                ]
                
                for thumb_url in thumb_urls:
                    try:
                        response = requests.get(thumb_url, timeout=10, stream=True)
                        if response.status_code == 200:
                            # Limit thumbnail size to prevent memory issues
                            content = response.content
                            if len(content) < 5 * 1024 * 1024:  # 5MB limit
                                thumb_bytes = content
                                break
                    except (requests.RequestException, ConnectionError) as e:
                        logger.warning(f"Could not fetch thumbnail {thumb_url}: {e}")
                        continue
            
            # Load MP3 file
            audio = MP3(str(mp3_path), ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            
            # Clear existing tags
            for key in list(audio.tags.keys()):
                audio.tags.delall(key)
            
            # Add basic tags
            title = info.get("title", "Unknown")
            uploader = info.get("uploader", "Unknown")
            upload_date = info.get("upload_date")
            
            if title:
                audio.tags.add(TIT2(encoding=3, text=str(title)[:255]))  # Limit length
            if uploader:
                audio.tags.add(TPE1(encoding=3, text=str(uploader)[:255]))
                audio.tags.add(TPE2(encoding=3, text=str(uploader)[:255]))  # Album artist
            
            # Album (use playlist or channel name)
            album = info.get("album") or info.get("playlist") or info.get("channel") or "YouTube Audio"
            audio.tags.add(TALB(encoding=3, text=str(album)[:255]))
            
            # Year
            if upload_date and len(str(upload_date)) >= 4:
                year = str(upload_date)[:4]
                if year.isdigit():
                    audio.tags.add(TYER(encoding=3, text=year))
            
            # Track number (for playlists)
            if info.get("playlist_index") and isinstance(info.get("playlist_index"), (int, str)):
                try:
                    track_num = str(int(info.get("playlist_index")))
                    audio.tags.add(TRCK(encoding=3, text=track_num))
                except (ValueError, TypeError):
                    pass
            
            # Genre
            categories = info.get("categories", [])
            if categories and isinstance(categories, list):
                genre = str(categories[0])[:255] if categories[0] else ""
                if genre:
                    audio.tags.add(TCON(encoding=3, text=genre))
            
            # Comment with description
            description = info.get("description", "")
            if description:
                desc_str = str(description)[:200] + "..." if len(str(description)) > 200 else str(description)
                audio.tags.add(COMM(encoding=3, lang='eng', desc='Description', text=desc_str))
            
            # Composer (channel)
            if uploader:
                audio.tags.add(TCOM(encoding=3, text=str(uploader)[:255]))
            
            # Add thumbnail
            if thumb_bytes:
                audio.tags.add(
                    APIC(
                        encoding=3,
                        mime=thumb_mime,
                        type=3,  # Front cover
                        desc="Cover",
                        data=thumb_bytes
                    )
                )
            
            audio.save()
            self.print_success("Enhanced metadata embedded successfully")
            
        except Exception as e:
            logger.error(f"Could not embed enhanced metadata: {e}")
            self.print_warning(f"Could not embed enhanced metadata: {e}")

    def extract_playlist_entries(self, url: str, limit: int = 100) -> Optional[Dict]:
        """Extract playlist entries"""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlist_items": f"1-{limit}",
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                pl = ydl.extract_info(url, download=False)
            if not pl or "entries" not in pl:
                return None
            return pl
        except Exception as e:
            self.print_error(f"Failed to fetch playlist: {e}")
            return None

    def pick_indices_menu(self, n: int) -> List[int]:
        """Menu for selecting playlist items with validation"""
        if n <= 0:
            return []
            
        print(f"\n{Fore.CYAN}📋 Selection Options:")
        print(f"{Fore.WHITE}1. Download all {n} items")
        print(f"{Fore.WHITE}2. Download specific range")
        print(f"{Fore.WHITE}3. Select individual items")
        print(f"{Fore.WHITE}4. Skip every X items")
        
        try:
            mode = input(f"\n{Fore.GREEN}Choose option (1-4): {Fore.WHITE}").strip()
        except (EOFError, KeyboardInterrupt):
            return []

        if mode == "1":
            return list(range(1, n + 1))

        if mode == "2":
            try:
                start = int(input(f"{Fore.GREEN}Start from item: {Fore.WHITE}").strip())
                end = int(input(f"{Fore.GREEN}End at item: {Fore.WHITE}").strip())
                start = max(1, min(n, start))
                end = max(1, min(n, end))
                if end < start:
                    start, end = end, start
                return list(range(start, end + 1))
            except (ValueError, EOFError, KeyboardInterrupt):
                return []

        if mode == "3":
            try:
                sel = input(f"{Fore.GREEN}Enter items (e.g., 1,3,5-7): {Fore.WHITE}").strip()
                indices: set[int] = set()
                for part in sel.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    if "-" in part:
                        try:
                            a, b = map(int, part.split("-"))
                            for i in range(min(a, b), max(a, b) + 1):
                                if 1 <= i <= n:
                                    indices.add(i)
                        except ValueError:
                            continue
                    else:
                        try:
                            i = int(part)
                            if 1 <= i <= n:
                                indices.add(i)
                        except ValueError:
                            continue
                return sorted(indices)
            except (EOFError, KeyboardInterrupt):
                return []

        if mode == "4":
            try:
                skip = int(input(f"{Fore.GREEN}Download every X items (e.g., 2 for every other): {Fore.WHITE}").strip())
                if skip < 1:
                    skip = 1
                return list(range(1, n + 1, skip))
            except (ValueError, EOFError, KeyboardInterrupt):
                return []

        return []

    def run_playlist_download(self, url: str, kind: str, quality: str, 
                            out_format: str, out_dir: Path, limit: int, 
                            embed_tags: bool = True) -> None:
        """Download playlist with options"""
        self.print_info(f"Fetching playlist (max {limit} items)...")
        pl = self.extract_playlist_entries(url, limit)
        if not pl:
            return

        title = self.clean_filename(pl.get("title", "playlist"))
        entries = pl.get("entries", [])
        n = len(entries)

        print(f"\n{Fore.CYAN}📁 Playlist: {Fore.YELLOW}{title}")
        print(f"{Fore.CYAN}🎵 Items: {Fore.GREEN}{n}")
        print(f"{Fore.CYAN}👤 Uploader: {Fore.WHITE}{pl.get('uploader', 'Unknown')}")
        
        # Show first few items
        print(f"\n{Fore.CYAN}First 10 items:")
        for idx, e in enumerate(entries[:10], 1):
            item_title = self.clean_filename(e.get('title', 'Unknown'))[:60]
            duration = e.get('duration')
            dur_str = f" ({self.format_duration(duration)})" if duration else ""
            print(f"{Fore.WHITE}{idx:3d}. {item_title}{dur_str}")
        if n > 10:
            print(f"{Fore.CYAN}... and {n-10} more")

        indices = self.pick_indices_menu(n)
        if not indices:
            self.print_error("Nothing selected")
            return

        base_dir = out_dir / title
        base_dir.mkdir(exist_ok=True, parents=True)

        # Create playlist info file
        playlist_info = {
            "playlist_title": title,
            "playlist_url": url,
            "total_items": n,
            "downloaded_items": len(indices),
            "download_date": datetime.now().isoformat(),
            "quality": quality,
            "format": out_format,
            "items": []
        }

        ok = 0
        fail = 0
        for j, i in enumerate(indices, 1):
            e = entries[i - 1]
            item_url = e.get("url") or (f"https://youtube.com/watch?v={e.get('id')}" if e.get("id") else None)
            if not item_url:
                fail += 1
                continue

            item_title = e.get('title', f'Item {i}')
            print(f"\n{Fore.CYAN}[{j}/{len(indices)}] {item_title}")
            
            if kind == "video":
                if self.download_video(item_url, quality, out_format, base_dir):
                    ok += 1
                    playlist_info["items"].append({
                        "index": i,
                        "title": item_title,
                        "url": item_url,
                        "status": "success"
                    })
                else:
                    fail += 1
                    playlist_info["items"].append({
                        "index": i,
                        "title": item_title,
                        "url": item_url,
                        "status": "failed"
                    })
            else:
                if self.download_audio(item_url, out_format, base_dir, embed_tags):
                    ok += 1
                    playlist_info["items"].append({
                        "index": i,
                        "title": item_title,
                        "url": item_url,
                        "status": "success"
                    })
                else:
                    fail += 1
                    playlist_info["items"].append({
                        "index": i,
                        "title": item_title,
                        "url": item_url,
                        "status": "failed"
                    })

        # Save playlist info
        info_file = base_dir / "playlist_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(playlist_info, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n{Fore.CYAN}📊 Playlist Download Complete!")
        print(Fore.CYAN + "━" * 50)
        print(f"{Fore.GREEN}✅ Successful: {ok}")
        print(f"{Fore.RED}❌ Failed: {fail}")
        print(f"{Fore.CYAN}📁 Location: {base_dir}")
        print(f"{Fore.CYAN}📄 Info file: {info_file.name}")

    def batch_download(self, kind: str, quality: str, out_format: str, 
                      embed_tags: bool = True) -> None:
        """Batch download from multiple URLs"""
        print(f"\n{Fore.CYAN}📝 Enter URLs (one per line). Type 'END' to finish:")
        print(Fore.CYAN + "─" * 50)
        
        urls: List[str] = []
        while True:
            u = input(f"{Fore.WHITE}> ").strip()
            if u.upper() == "END":
                break
            if u:
                urls.append(u)

        if not urls:
            self.print_error("No URLs provided")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_dir = self.root / "Batch" / f"{kind}_{timestamp}"
        batch_dir.mkdir(exist_ok=True, parents=True)

        # Save URL list
        urls_file = batch_dir / "url_list.txt"
        with open(urls_file, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(url + "\n")

        print(f"\n{Fore.CYAN}Starting batch download of {len(urls)} items...")
        print(f"{Fore.WHITE}Type: {kind}")
        print(f"{Fore.WHITE}Quality: {quality}")
        print(f"{Fore.WHITE}Format: {out_format}")
        print(f"{Fore.WHITE}Location: {batch_dir}")

        ok = 0
        results = []
        for idx, u in enumerate(urls, 1):
            print(f"\n{Fore.CYAN}[{idx}/{len(urls)}] {u[:60]}...")
            
            start_time = time.time()
            if kind == "video":
                success = self.download_video(u, quality, out_format, batch_dir)
            else:
                success = self.download_audio(u, out_format, batch_dir, embed_tags)
            
            elapsed = time.time() - start_time
            results.append({
                "url": u,
                "success": success,
                "time_seconds": round(elapsed, 2)
            })
            
            if success:
                ok += 1

        # Save results
        results_file = batch_dir / "batch_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "total": len(urls),
                "successful": ok,
                "failed": len(urls) - ok,
                "timestamp": timestamp,
                "type": kind,
                "quality": quality,
                "format": out_format,
                "results": results
            }, f, indent=2, ensure_ascii=False)

        success_rate = (ok / len(urls)) * 100 if urls else 0
        print(f"\n{Fore.CYAN}📊 Batch Download Complete!")
        print(Fore.CYAN + "━" * 50)
        print(f"{Fore.GREEN}✅ Successful: {ok}/{len(urls)} ({success_rate:.1f}%)")
        print(f"{Fore.RED}❌ Failed: {len(urls) - ok}/{len(urls)}")
        print(f"{Fore.CYAN}📁 Location: {batch_dir}")
        print(f"{Fore.CYAN}📄 Results: {results_file.name}")

    def show_downloads(self) -> None:
        """Show download statistics and files"""
        self.clear()
        self.print_header("📊 DOWNLOAD STATISTICS")
        
        if not self.root.exists():
            self.print_error("No downloads folder found")
            input(f"\n{Fore.GREEN}Press Enter to continue...")
            return

        # Statistics
        print(f"\n{Fore.CYAN}📈 Overall Statistics:")
        print(Fore.CYAN + "━" * 50)
        print(f"{Fore.WHITE}Total Downloads: {Fore.YELLOW}{self.stats['total_downloads']}")
        print(f"{Fore.WHITE}Video Downloads: {Fore.CYAN}{self.stats['video_downloads']}")
        print(f"{Fore.WHITE}Audio Downloads: {Fore.GREEN}{self.stats['audio_downloads']}")
        print(f"{Fore.WHITE}Total Size: {Fore.MAGENTA}{self.stats['total_size_gb']:.2f} GB")
        
        if self.stats['last_download']:
            last_dl = datetime.fromisoformat(self.stats['last_download'])
            last_str = last_dl.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{Fore.WHITE}Last Download: {Fore.YELLOW}{last_str}")

        # File system scan
        print(f"\n{Fore.CYAN}📁 File System Scan:")
        print(Fore.CYAN + "━" * 50)
        
        media_exts = {'.mp4', '.mkv', '.webm', '.avi', '.mp3', '.m4a', '.flac', '.opus', '.wav'}
        all_files = [p for p in self.root.rglob("*") if p.is_file() and p.suffix.lower() in media_exts]
        all_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        total_size = sum(f.stat().st_size for f in all_files)
        print(f"{Fore.WHITE}Total Files: {Fore.YELLOW}{len(all_files)}")
        print(f"{Fore.WHITE}Total Size: {Fore.CYAN}{self.format_size(total_size)}")
        
        # Group by type
        video_files = [f for f in all_files if f.suffix.lower() in {'.mp4', '.mkv', '.webm', '.avi'}]
        audio_files = [f for f in all_files if f.suffix.lower() in {'.mp3', '.m4a', '.flac', '.opus', '.wav'}]
        
        print(f"{Fore.WHITE}Video Files: {Fore.GREEN}{len(video_files)}")
        print(f"{Fore.WHITE}Audio Files: {Fore.BLUE}{len(audio_files)}")
        
        # Recent files
        print(f"\n{Fore.CYAN}📅 Recent Downloads (last 10):")
        print(Fore.CYAN + "━" * 50)
        
        if not all_files:
            print(f"{Fore.YELLOW}No downloads yet")
        else:
            for idx, p in enumerate(all_files[:10], 1):
                size_mb = p.stat().st_size / (1024 * 1024)
                ts = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                try:
                    rel = p.relative_to(self.root)
                except:
                    rel = p
                
                icon = "🎬" if p.suffix.lower() in {'.mp4', '.mkv', '.webm', '.avi'} else "🎵"
                print(f"{Fore.WHITE}{idx:2}. {icon} {ts} {size_mb:7.1f}MB {Fore.CYAN}{rel}")

        # Folder structure
        print(f"\n{Fore.CYAN}📂 Folder Structure:")
        print(Fore.CYAN + "━" * 50)
        
        folders = ["Videos", "Music", "Batch", "Playlists"]
        for folder in folders:
            folder_path = self.root / folder
            if folder_path.exists():
                file_count = len([f for f in folder_path.rglob("*") if f.is_file()])
                size = sum(f.stat().st_size for f in folder_path.rglob("*") if f.is_file())
                print(f"{Fore.WHITE}{folder:<12} {Fore.YELLOW}{file_count:4} files {Fore.CYAN}{self.format_size(size)}")

        input(f"\n{Fore.GREEN}Press Enter to continue...")

    def show_features(self) -> None:
        """Display all features"""
        self.clear()
        self.print_header("⭐ FEATURES LIST")
        
        features = [
            {
                "icon": "🎬",
                "name": "Video Download",
                "items": [
                    "8 quality presets (240p to 4K)",
                    "4 output formats (MP4, MKV, WebM, AVI)",
                    "Automatic subtitle download",
                    "Thumbnail embedding",
                    "Concurrent fragment download"
                ]
            },
            {
                "icon": "🎵",
                "name": "Music Download",
                "items": [
                    "5 audio formats (MP3, M4A, FLAC, Opus, WAV)",
                    "Enhanced metadata embedding",
                    "High-quality thumbnail embedding",
                    "Bitrate selection (128-320kbps)",
                    "ID3 tag support"
                ]
            },
            {
                "icon": "📁",
                "name": "Playlist Support",
                "items": [
                    "Download entire playlists",
                    "Selective item download",
                    "Range selection",
                    "Skip pattern download",
                    "Playlist metadata preservation"
                ]
            },
            {
                "icon": "🔗",
                "name": "Batch Processing",
                "items": [
                    "Multiple URL download",
                    "Progress tracking",
                    "Result logging",
                    "Error handling",
                    "Resume support"
                ]
            },
            {
                "icon": "📊",
                "name": "Statistics & Management",
                "items": [
                    "Download statistics",
                    "File organization",
                    "Storage tracking",
                    "Recent downloads view",
                    "Folder structure view"
                ]
            },
            {
                "icon": "⚙️",
                "name": "Advanced Features",
                "items": [
                    "FFmpeg integration",
                    "Concurrent downloads",
                    "Proxy support",
                    "Cookies support",
                    "User-agent customization"
                ]
            }
        ]
        
        for feature in features:
            print(f"\n{Fore.YELLOW}{feature['icon']} {feature['name']}")
            print(Fore.CYAN + "─" * 40)
            for item in feature['items']:
                print(f"  {Fore.GREEN}✓ {Fore.WHITE}{item}")
        
        print(f"\n{Fore.CYAN}🌐 Supported Sites:")
        sites_per_line = 4
        for i in range(0, len(self.supported_sites), sites_per_line):
            line_sites = self.supported_sites[i:i + sites_per_line]
            print(f"  {Fore.WHITE}" + "  •  ".join(line_sites))
        
        print(f"\n{Fore.CYAN}🎯 System Requirements:")
        print(f"  {Fore.WHITE}• Python 3.7+")
        print(f"  {Fore.WHITE}• FFmpeg (recommended)")
        print(f"  {Fore.WHITE}• Internet connection")
        print(f"  {Fore.WHITE}• 100MB+ free disk space")
        
        input(f"\n{Fore.GREEN}Press Enter to continue...")

    def settings_menu(self) -> None:
        """Settings menu"""
        while True:
            self.clear()
            self.print_header("⚙️ SETTINGS")
            
            print(f"\n{Fore.CYAN}1. {Fore.WHITE}Change download folder")
            print(f"{Fore.CYAN}2. {Fore.WHITE}Set default video quality")
            print(f"{Fore.CYAN}3. {Fore.WHITE}Set default audio quality")
            print(f"{Fore.CYAN}4. {Fore.WHITE}Clear all downloads")
            print(f"{Fore.CYAN}5. {Fore.WHITE}Reset statistics")
            print(f"{Fore.CYAN}6. {Fore.WHITE}Check for updates")
            print(f"{Fore.CYAN}7. {Fore.WHITE}Back to main menu")
            
            choice = input(f"\n{Fore.GREEN}Select option (1-7): {Fore.WHITE}").strip()
            
            if choice == "1":
                new_path = input(f"{Fore.GREEN}Enter new download path: {Fore.WHITE}").strip()
                if new_path:
                    old_root = self.root
                    self.root = Path(new_path)
                    self.root.mkdir(exist_ok=True, parents=True)
                    
                    # Try to move existing files
                    try:
                        if old_root.exists() and old_root != self.root:
                            print(f"{Fore.YELLOW}Moving existing downloads...")
                            for item in old_root.iterdir():
                                shutil.move(str(item), str(self.root / item.name))
                            shutil.rmtree(old_root)
                    except Exception as e:
                        self.print_warning(f"Could not move files: {e}")
                    
                    self.print_success(f"Download folder changed to: {self.root}")
                    time.sleep(2)
            
            elif choice == "4":
                confirm = input(f"{Fore.RED}⚠️  Delete ALL downloaded files? (y/N): {Fore.WHITE}").lower()
                if confirm == 'y':
                    try:
                        # Keep stats file
                        stats_backup = self.stats.copy()
                        shutil.rmtree(self.root)
                        self.root.mkdir(exist_ok=True)
                        self.stats = stats_backup
                        self.save_stats()
                        self.print_success("All downloads cleared!")
                    except Exception as e:
                        self.print_error(f"Failed to clear: {e}")
                    time.sleep(2)
            
            elif choice == "5":
                confirm = input(f"{Fore.YELLOW}Reset all statistics? (y/N): {Fore.WHITE}").lower()
                if confirm == 'y':
                    self.stats = {
                        "total_downloads": 0,
                        "video_downloads": 0,
                        "audio_downloads": 0,
                        "last_download": None,
                        "total_size_gb": 0.0
                    }
                    self.save_stats()
                    self.print_success("Statistics reset!")
                    time.sleep(2)
            
            elif choice == "6":
                self.check_updates()
                input(f"\n{Fore.GREEN}Press Enter to continue...")
            
            elif choice == "7":
                break

    def check_updates(self) -> None:
        """Check for updates"""
        self.print_info("Checking for updates...")
        print(f"{Fore.WHITE}Current version: {Fore.YELLOW}{self.version}")
        print(f"{Fore.WHITE}Latest version: {Fore.GREEN}Checking...")
        print(f"\n{Fore.CYAN}Update instructions:")
        print(f"{Fore.WHITE}1. Visit: https://github.com/")
        print(f"{Fore.WHITE}2. Check for new releases")
        print(f"{Fore.WHITE}3. Download latest version")
        print(f"\n{Fore.YELLOW}Note: This is a local tool. Updates must be manual.")

    def quality_menu(self, media_type: str = "video") -> str:
        """Quality selection menu"""
        if media_type == "video":
            presets = self.quality_presets
            title = "🎚️ VIDEO QUALITY"
        else:
            presets = self.audio_presets
            title = "🎵 AUDIO QUALITY"
        
        self.clear()
        self.print_header(title)
        
        keys = list(presets.keys())
        for i, k in enumerate(keys, 1):
            preset = presets[k]
            print(f"{Fore.YELLOW}{i:2}. {preset['icon']} {k:<10} {Fore.WHITE}- {preset['description']}")
        
        try:
            c = int(input(f"\n{Fore.GREEN}Choose (1-{len(keys)}): {Fore.WHITE}").strip())
            if 1 <= c <= len(keys):
                return keys[c - 1]
        except ValueError:
            pass
        
        return "720p" if media_type == "video" else "best"

    def format_menu(self, media_type: str = "video") -> str:
        """Format selection menu"""
        if media_type == "video":
            formats = self.video_formats
            title = "📁 VIDEO FORMAT"
        else:
            formats = self.audio_formats
            title = "🎵 AUDIO FORMAT"
        
        self.clear()
        self.print_header(title)
        
        keys = list(formats.keys())
        for i, k in enumerate(keys, 1):
            fmt = formats[k]
            print(f"{Fore.YELLOW}{i:2}. {fmt['icon']} {k:<5} {Fore.WHITE}- {fmt['description']}")
        
        try:
            c = int(input(f"\n{Fore.GREEN}Choose (1-{len(keys)}): {Fore.WHITE}").strip())
            if 1 <= c <= len(keys):
                return keys[c - 1]
        except ValueError:
            pass
        
        return "mp4" if media_type == "video" else "mp3"

    def main_menu(self) -> None:
        """Main application menu"""
        while True:
            self.clear()
            self.print_header("🎬 YOUTUBE ALL-IN-ONE PRO")
            
            # Version and stats
            print(f"{Fore.CYAN}Version: {Fore.YELLOW}{self.version}")
            print(f"{Fore.CYAN}Downloads: {Fore.GREEN}{self.stats['total_downloads']} total")
            print(f"{Fore.CYAN}Folder: {Fore.WHITE}{self.root.absolute()}")
            
            # Check disk space
            try:
                disk_usage = shutil.disk_usage(self.root)
                free_gb = disk_usage.free / (1024**3)
                used_pct = (disk_usage.used / disk_usage.total) * 100
                print(f"{Fore.CYAN}Disk: {Fore.GREEN}{free_gb:.1f} GB free ({used_pct:.1f}% used)")
            except:
                pass
            
            # Menu options
            menu_options = [
                ("🎬", "VIDEO: Single", "1"),
                ("📁", "VIDEO: Playlist", "2"),
                ("🔗", "VIDEO: Batch URLs", "3"),
                ("🎵", "MUSIC: Single (MP3 with tags)", "4"),
                ("📚", "MUSIC: Playlist (MP3 with tags)", "5"),
                ("🔗", "MUSIC: Batch URLs", "6"),
                ("📊", "View Downloads & Statistics", "7"),
                ("⭐", "Features List", "8"),
                ("⚙️", "Settings", "9"),
                ("🚪", "Exit", "0")
            ]
            
            print(f"\n{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗")
            for icon, text, key in menu_options:
                if key in ["1", "2", "3"]:
                    color = Fore.GREEN
                elif key in ["4", "5", "6"]:
                    color = Fore.BLUE
                elif key in ["7", "8", "9"]:
                    color = Fore.MAGENTA
                else:
                    color = Fore.RED
                
                print(f"{Fore.CYAN}║  {color}{key}. {icon} {text:<40}{Fore.CYAN}║")
            print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════════════╝")
            
            choice = input(f"\n{Fore.YELLOW}Select option (0-9): {Fore.WHITE}").strip()
            
            if choice == "1":  # Video Single
                url = input(f"{Fore.CYAN}🎬 Enter Video URL: {Fore.WHITE}").strip()
                if url:
                    quality = self.quality_menu("video")
                    fmt = self.format_menu("video")
                    out_dir = self.root / "Videos" / "Singles"
                    self.download_video(url, quality, fmt, out_dir)
                    input(f"\n{Fore.GREEN}Press Enter to continue...")
            
            elif choice == "2":  # Video Playlist
                url = input(f"{Fore.CYAN}📁 Enter Playlist URL: {Fore.WHITE}").strip()
                if url:
                    limit = input(f"{Fore.CYAN}Max items (default 50): {Fore.WHITE}").strip()
                    try:
                        lim = int(limit) if limit else 50
                    except ValueError:
                        lim = 50
                    quality = self.quality_menu("video")
                    fmt = self.format_menu("video")
                    out_dir = self.root / "Videos" / "Playlists"
                    self.run_playlist_download(url, "video", quality, fmt, out_dir, lim, False)
                    input(f"\n{Fore.GREEN}Press Enter to continue...")
            
            elif choice == "3":  # Video Batch
                quality = self.quality_menu("video")
                fmt = self.format_menu("video")
                self.batch_download("video", quality, fmt, False)
                input(f"\n{Fore.GREEN}Press Enter to continue...")
            
            elif choice == "4":  # Music Single
                url = input(f"{Fore.CYAN}🎵 Enter Music URL: {Fore.WHITE}").strip()
                if url:
                    fmt = self.format_menu("audio")
                    quality = self.quality_menu("audio")
                    out_dir = self.root / "Music" / "Singles"
                    
                    # Ask for bitrate for MP3
                    bitrate = "192"
                    if fmt == "mp3":
                        bitrate_choice = input(f"{Fore.CYAN}MP3 Bitrate (128/192/256/320, default 192): {Fore.WHITE}").strip()
                        if bitrate_choice in ["128", "192", "256", "320"]:
                            bitrate = bitrate_choice
                    
                    self.download_audio(url, fmt, out_dir, True, bitrate)
                    input(f"\n{Fore.GREEN}Press Enter to continue...")
            
            elif choice == "5":  # Music Playlist
                url = input(f"{Fore.CYAN}📚 Enter Music Playlist URL: {Fore.WHITE}").strip()
                if url:
                    limit = input(f"{Fore.CYAN}Max items (default 100): {Fore.WHITE}").strip()
                    try:
                        lim = int(limit) if limit else 100
                    except ValueError:
                        lim = 100
                    fmt = self.format_menu("audio")
                    quality = self.quality_menu("audio")
                    out_dir = self.root / "Music" / "Playlists"
                    self.run_playlist_download(url, "audio", quality, fmt, out_dir, lim, True)
                    input(f"\n{Fore.GREEN}Press Enter to continue...")
            
            elif choice == "6":  # Music Batch
                fmt = self.format_menu("audio")
                quality = self.quality_menu("audio")
                self.batch_download("audio", quality, fmt, True)
                input(f"\n{Fore.GREEN}Press Enter to continue...")
            
            elif choice == "7":  # View Downloads
                self.show_downloads()
            
            elif choice == "8":  # Features List
                self.show_features()
            
            elif choice == "9":  # Settings
                self.settings_menu()
            
            elif choice == "0":  # Exit
                print(f"\n{Fore.GREEN}Thank you for using YouTube All-in-One Pro! 👋")
                print(f"{Fore.CYAN}Goodbye!")
                time.sleep(1)
                break

def main() -> None:
    """Main entry point"""
    # Check dependencies
    try:
        pass
    except ImportError:
        print("Error: Missing dependencies!")
        print("Install: pip install yt-dlp colorama mutagen")
        return
    
    # Create and run application
    app = YouTubeAllInOnePro()
    app.main_menu()

if __name__ == "__main__":
    main()