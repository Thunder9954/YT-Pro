# YouTube All-in-One Downloader Pro - Web Version

A modern Flask-based web application for downloading YouTube videos and audio with advanced features.

## Features

### 🎬 Video Downloads
- **Multiple Quality Options**: 240p to 4K UHD
- **Format Support**: MP4, MKV, WebM, AVI
- **Automatic Subtitles**: Embedded subtitles in multiple languages
- **Thumbnail Embedding**: Video thumbnails embedded in files
- **Concurrent Downloads**: Multi-threaded downloading

### 🎵 Audio Downloads  
- **Format Support**: MP3, M4A, FLAC, Opus, WAV
- **Quality Options**: 128kbps to 320kbps
- **Metadata Embedding**: Automatic ID3 tag embedding
- **Cover Art**: High-quality thumbnail embedding
- **Enhanced Tags**: Artist, album, genre, and more

### 🌐 Web Interface
- **Modern UI**: Clean, responsive design with Tailwind CSS
- **Real-time Progress**: Live download progress updates
- **Download Management**: Track active and completed downloads
- **Statistics**: Comprehensive download statistics
- **History**: Download history with file management

### 🔧 Advanced Features
- **Multi-threaded**: Concurrent download processing
- **Error Handling**: Robust error recovery and logging
- **Security**: Input validation and safe file operations
- **Performance**: Optimized for speed and memory usage
- **Cross-platform**: Works on Windows, macOS, and Linux

## Installation

### Prerequisites
- Python 3.7+
- FFmpeg (recommended for full functionality)

### Setup
1. Clone or download the project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install FFmpeg (optional but recommended):
   - **Ubuntu/Debian**: `sudo apt install ffmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org) and add to PATH

### Running the Application
```bash
python app.py
```

The application will start on `http://localhost:5000`

## Usage

### Basic Download
1. Paste a YouTube URL into the input field
2. Select media type (Video or Audio)
3. Choose quality and format options
4. Click "Get Video Info" to preview
5. Click "Start Download" to begin

### Advanced Features
- **Batch Downloads**: Multiple URLs supported (in development)
- **Playlist Support**: Entire playlist downloads (in development)
- **Custom Settings**: Configure download paths and preferences

## API Endpoints

### Video Information
```
GET /api/info?url=<youtube_url>
```
Returns video metadata including title, duration, available formats.

### Start Download
```
POST /api/download
Content-Type: application/json

{
  "url": "youtube_url",
  "type": "video|audio",
  "quality": "720p|1080p|best",
  "format": "mp4|mp3|etc",
  "bitrate": "192|320|etc"
}
```

### Download Status
```
GET /api/download/<download_id>
```
Returns current download status and progress.

### All Downloads
```
GET /api/downloads
```
Returns all active downloads.

### Download History
```
GET /api/history
```
Returns download history.

### Statistics
```
GET /api/stats
```
Returns download statistics.

### File Download
```
GET /download/<file_path>
```
Downloads the specified file.

## Security Features

### Input Validation
- URL validation and sanitization
- File path traversal protection
- Parameter type checking

### Safe Operations
- Sandboxed file operations
- Memory limits for downloads
- Timeout protection for network requests

### Error Handling
- Comprehensive exception handling
- Graceful degradation
- Detailed logging

## File Structure

```
/home/markush/yt/
├── app.py                 # Main Flask application
├── mix_tool.py           # Original CLI tool (fixed)
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── YT_Downloads_Web/    # Download directory
    ├── Videos/          # Video downloads
    ├── Music/           # Audio downloads
    └── stats.json       # Download statistics
```

## Configuration

### Environment Variables
- `FLASK_SECRET_KEY`: Custom secret key for sessions
- `DOWNLOAD_PATH`: Custom download directory
- `MAX_WORKERS`: Maximum concurrent download threads

### Default Settings
- Port: 5000
- Max concurrent downloads: 3
- Session type: Filesystem
- Max upload size: 16MB

## Troubleshooting

### Common Issues

1. **FFmpeg Not Found**
   - Install FFmpeg and ensure it's in PATH
   - Some features may not work without FFmpeg

2. **Download Failures**
   - Check internet connection
   - Verify YouTube URL is valid
   - Check available disk space

3. **Permission Errors**
   - Ensure write permissions in download directory
   - Run as administrator if necessary

4. **Memory Issues**
   - Reduce concurrent downloads in settings
   - Monitor system resources

### Logs
Application logs are printed to console and include:
- Download progress
- Error messages
- Performance metrics

## Development

### Adding New Features
1. Modify `app.py` for backend changes
2. Update HTML template for UI changes
3. Add new API endpoints as needed

### Testing
```bash
# Run with debug mode
python app.py

# Test API endpoints
curl http://localhost:5000/api/stats
```

## License

This project is for educational and personal use only.
Please respect YouTube's Terms of Service and copyright laws.

## Changelog

### v2.0.0-web
- Complete Flask web application
- Fixed all CLI security issues
- Added real-time progress tracking
- Modern responsive UI
- Multi-threaded downloads
- Enhanced error handling
- Comprehensive API

### v2.0.0 (CLI)
- Original CLI tool with bug fixes
- Security improvements
- Better error handling
- Enhanced metadata support

## Support

For issues and feature requests, please check the code comments and documentation.
