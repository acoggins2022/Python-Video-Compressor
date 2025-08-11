import os
import subprocess
import sys
import json
import re

def get_executable_path(name):
    """
    Gets the path to a bundled executable, handling both normal script execution
    and running as a frozen PyInstaller application.
    """
    if hasattr(sys, '_MEIPASS'):
        # This attribute is set by PyInstaller when running as a bundle.
        # It points to the temporary folder where files are unpacked.
        return os.path.join(sys._MEIPASS, name)
    
    # When running as a normal .py script, assume the executable is
    # in the same directory as this logic script.
    return os.path.join(os.path.dirname(__file__), name)

def get_video_info(input_path):
    """
    Uses the bundled ffprobe to get video information (duration and height).
    """
    ffprobe_path = get_executable_path('ffprobe.exe')
    command = [
        ffprobe_path,
        '-v', 'error',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        input_path
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        data = json.loads(result.stdout)
        
        duration = float(data['format']['duration'])
        video_stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
        
        if not video_stream:
            return None, None
            
        height = int(video_stream['height'])
        return duration, height
        
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None, None

def compress_video(input_path, output_path, settings, progress_callback):
    """
    Re-encodes a video file using the bundled FFmpeg, capturing real-time progress.
    """
    try:
        progress_callback({'status': 'progress', 'message': 'Analyzing video...', 'value': 0})
        
        total_duration, original_height = get_video_info(input_path)
        
        if total_duration is None or total_duration <= 0:
            progress_callback({'status': 'error', 'message': 'Error: Could not analyze video file.'})
            return

        ffmpeg_path = get_executable_path('ffmpeg.exe')

        # --- Build the FFmpeg command ---
        command = [
            ffmpeg_path,
            '-i', input_path,
            '-y',
            '-vcodec', 'libx264',
            '-crf', str(settings['crf']),
            '-preset', settings['preset'],
            '-acodec', 'aac',
            '-b:a', settings['audio_bitrate'],
            '-threads', '0'
        ]

        if settings['target_height'] > 0 and settings['target_height'] < original_height:
            command.extend(['-vf', f'scale=-2:{settings["target_height"]}'])

        command.append(output_path)
        
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW

        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True, 
            encoding='utf-8',
            creationflags=creation_flags
        )

        time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})')

        while True:
            line = process.stderr.readline()
            if not line:
                break
            
            match = time_pattern.search(line)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = int(match.group(3))
                current_time = hours * 3600 + minutes * 60 + seconds
                
                percentage = (current_time / total_duration) * 100
                progress_callback({'status': 'progress', 'message': f'Compressing... {int(percentage)}%', 'value': min(100, percentage)})

        process.wait()

        if process.returncode == 0:
            output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            progress_callback({'status': 'success', 'message': f"Success! New file size: {output_size_mb:.2f} MB"})
        else:
            progress_callback({'status': 'error', 'message': 'Error: FFmpeg failed. See console for details.'})
            error_output = process.stderr.read()
            print(f"\n--- FFmpeg Error (return code {process.returncode}) ---\n")
            if error_output:
                print(error_output)

    except Exception as e:
        progress_callback({'status': 'error', 'message': f"An unexpected error occurred: {e}"})
        print(f"An unexpected error occurred: {str(e)}")
