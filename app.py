from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify
import os
import tempfile
import yt_dlp
from werkzeug.utils import secure_filename
import threading
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        download_type = request.form.get('download_type', 'video')
        is_playlist = 'playlist' in request.form
        
        if not url:
            flash('Please enter a YouTube URL', 'error')
            return redirect(url_for('index'))
        
        try:
            # Create a temporary directory for downloads
            temp_dir = tempfile.mkdtemp()
            
            # Set up yt-dlp options based on download type
            if download_type == 'video':
                quality = request.form.get('quality', '720p')
                # Convert quality to height (e.g., '720p' -> 720)
                height = int(quality.replace('p', ''))
                
                ydl_opts = {
                    'format': f'bestvideo[height<={height}]+bestaudio/best[height<={height}]',
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'merge_output_format': 'mp4',  # Ensure output is mp4
                    'progress_hooks': [progress_hook],
                }
            else:  # audio
                audio_quality = request.form.get('audio_quality', '320kbps')
                # Convert quality to bitrate (e.g., '320kbps' -> 320)
                bitrate = int(audio_quality.replace('kbps', ''))
                
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': str(bitrate),
                    }],
                    'progress_hooks': [progress_hook],
                }
            
            # Handle playlist option
            if is_playlist:
                ydl_opts['noplaylist'] = False
            else:
                ydl_opts['noplaylist'] = True
            
            # Download the video/audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # If it's a single video/audio
                if not is_playlist or 'entries' not in info:
                    filename = ydl.prepare_filename(info)
                    
                    # For video, ensure it's mp4
                    if download_type == 'video':
                        # Check if the file exists and has the correct extension
                        if not filename.endswith('.mp4'):
                            # Look for an mp4 version
                            base, ext = os.path.splitext(filename)
                            mp4_filename = base + '.mp4'
                            if os.path.exists(mp4_filename):
                                filename = mp4_filename
                            else:
                                # If mp4 doesn't exist, try to find any video file
                                for file in os.listdir(temp_dir):
                                    if file.endswith('.mp4'):
                                        filename = os.path.join(temp_dir, file)
                                        break
                    
                    # For audio, ensure it's mp3
                    elif download_type == 'audio':
                        if not filename.endswith('.mp3'):
                            # Look for an mp3 version
                            base, ext = os.path.splitext(filename)
                            mp3_filename = base + '.mp3'
                            if os.path.exists(mp3_filename):
                                filename = mp3_filename
                            else:
                                # If mp3 doesn't exist, try to find any audio file
                                for file in os.listdir(temp_dir):
                                    if file.endswith('.mp3'):
                                        filename = os.path.join(temp_dir, file)
                                        break
                    
                    return send_file(filename, as_attachment=True)
                
                # If it's a playlist
                else:
                    import zipfile
                    playlist_title = info['title']
                    zip_filename = os.path.join(temp_dir, f'{playlist_title}.zip')
                    
                    with zipfile.ZipFile(zip_filename, 'w') as zipf:
                        for root, _, files in os.walk(temp_dir):
                            for file in files:
                                if file != f'{playlist_title}.zip':
                                    file_path = os.path.join(root, file)
                                    zipf.write(file_path, file)
                    
                    return send_file(zip_filename, as_attachment=True, download_name=f'{playlist_title}.zip')
                    
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('index'))
    
    return render_template('index.html')

def progress_hook(d):
    if d['status'] == 'downloading':
        percent_str = d.get('_percent_str', '0%')
        percent = percent_str.strip('%')
        # In a real application, you would send this to the frontend via WebSocket or similar
        # For now, we'll just print it
        print(f"Download progress: {percent}%")
    elif d['status'] == 'finished':
        print("Download finished")

if __name__ == '__main__':
    app.run(debug=True)