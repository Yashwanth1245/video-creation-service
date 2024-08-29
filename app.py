import os
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from moviepy.editor import *
import tempfile
import shutil

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mkv'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_clip(file_path, clip_duration):
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        clip = ImageClip(file_path).set_duration(clip_duration)
    elif file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        clip = VideoFileClip(file_path)
        if clip.duration > clip_duration:
            clip = clip.subclip(0, clip_duration)
    else:
        return None
    
    # Resize clip to 1080x1920 (9:16 aspect ratio for Shorts)
    clip = clip.resize(height=1920)
    clip = clip.crop(x_center=clip.w/2, width=1080)
    
    return clip

def apply_transition(clip, transition_type, duration):
    if transition_type == "fade":
        return clip.crossfadein(duration)
    elif transition_type == "fade_black":
        return CompositeVideoClip([Color(color=(0,0,0)).set_duration(duration),
                                   clip.set_start(duration).crossfadein(duration)])
    elif transition_type == "slide_left":
        return clip.set_position(("right", "center")).set_start(duration).crossfadein(duration)
    elif transition_type == "slide_right":
        return clip.set_position(("left", "center")).set_start(duration).crossfadein(duration)
    else:
        return clip

def render_video(media_folder, output_path, clip_duration=5, transition_duration=1, transition_type="fade"):
    media_files = [f for f in os.listdir(media_folder) if allowed_file(f)]
    media_files.sort()

    clips = []
    for media_file in media_files:
        media_path = os.path.join(media_folder, media_file)
        clip = create_clip(media_path, clip_duration)
        if clip is not None:
            clips.append(clip)

    final_clips = []
    for i, clip in enumerate(clips):
        if i > 0:
            clip = apply_transition(clip, transition_type, transition_duration)
        final_clips.append(clip)

    final_video = concatenate_videoclips(final_clips, method="compose")
    final_video.write_videofile(output_path, fps=30)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'files[]' not in request.files:
            return 'No file part'
        files = request.files.getlist('files[]')
        if not files or files[0].filename == '':
            return 'No selected file'
        
        transition_type = request.form.get('transition_type', 'fade')
        clip_duration = float(request.form.get('clip_duration', 5))
        transition_duration = float(request.form.get('transition_duration', 1))
        
        temp_dir = tempfile.mkdtemp()
        try:
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(temp_dir, filename))
            
            output_path = os.path.join(temp_dir, 'output.mp4')
            render_video(temp_dir, output_path, clip_duration, transition_duration, transition_type)
            
            return send_file(output_path, as_attachment=True)
        finally:
            shutil.rmtree(temp_dir)
    
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)