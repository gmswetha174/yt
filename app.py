from flask import Flask, render_template, request, jsonify
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import subprocess
import assemblyai as aai
from yt_dlp import YoutubeDL
import time

app = Flask(__name__)

# Store progress per YouTube URL
progress_status = {}

available_languages = {
    'Tamil': 'ta',
    'Hindi': 'hi',
    'French': 'fr',
    'Spanish': 'es',
    'German': 'de',
    'Chinese': 'zh-CN',
    'Japanese': 'ja'
}

def update_progress(url, value):
    """ Update the progress of a specific YouTube URL """
    progress_status[url] = value

@app.route('/progress', methods=['GET'])
def get_progress():
    """ Return progress status for a given URL """
    url = request.args.get('url')
    return jsonify({"progress": progress_status.get(url, 0)})

def clear_old_audio():
    try:
        for file in os.listdir("static"):
            if file.startswith("downloaded_audio") or file.startswith("translated_audio_"):
                os.remove(os.path.join("static", file))
    except Exception as e:
        print(f"Error clearing old files: {e}")

def download_audio(url):
    try:
        clear_old_audio()
        update_progress(url, 10)  # Update progress to 10%

        output_filename = "static/downloaded_audio"
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': f"{output_filename}.%(ext)s"}

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        downloaded_files = [f for f in os.listdir("static") if f.startswith("downloaded_audio")]
        audio_file = next((f for f in downloaded_files if f.endswith(".webm") or f.endswith(".m4a")), None)

        if not audio_file:
            return None

        audio_path = os.path.join("static", audio_file)
        mp3_file = f"{output_filename}.mp3"

        if not audio_file.endswith(".mp3"):
            command = f'ffmpeg -i "{audio_path}" -vn -ar 44100 -ac 2 -b:a 192k "{mp3_file}"'
            subprocess.run(command, shell=True, check=True)
            os.remove(audio_path)

        update_progress(url, 30)  # Update progress to 30%
        return mp3_file if os.path.exists(mp3_file) else None
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None

def transcribe_audio(file_path, url):
    try:
        if not os.path.exists(file_path):
            return None

        update_progress(url, 50)  # Update progress to 50%

        aai.settings.api_key = "8ded3e61ee47493b8d2bcc093ca1bf67"
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(file_path)

        if transcript and transcript.text:
            update_progress(url, 70)  # Update progress to 70%
            return transcript.text
        else:
            return None
    except Exception as e:
        print(f"Error in transcription: {e}")
        return None

def split_text(text, max_length=500):
    sentences = text.split('. ')
    chunks, current_chunk = [], ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_length:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def translate_text_to_audio(text, target_lang, url):
    try:
        if target_lang not in available_languages:
            return None, None

        update_progress(url, 80)  # Update progress to 80%

        lang_code = available_languages[target_lang]
        text_chunks = split_text(text, max_length=500)
        translated_chunks = [GoogleTranslator(source="auto", target=lang_code).translate(chunk) for chunk in text_chunks]

        translated_text = " ".join(translated_chunks)
        audio_file = f"static/translated_audio_{lang_code}.mp3"

        tts = gTTS(text=translated_text, lang=lang_code)
        tts.save(audio_file)

        update_progress(url, 100)  # Update progress to 100%
        return audio_file, translated_text

    except Exception as e:
        print(f"Error in translation: {e}")
        return None, None

@app.route('/')
def home():
    return render_template('index.html', languages=available_languages)

@app.route('/process', methods=['POST'])
def process():
    youtube_url = request.form.get('url')
    target_lang = request.form.get('language')

    if not youtube_url or not target_lang:
        return jsonify({"error": "Missing YouTube URL or language"}), 400

    update_progress(youtube_url, 5)  # Start progress

    audio_file = download_audio(youtube_url)
    if not audio_file:
        return jsonify({"error": "Audio download failed"}), 400

    transcription = transcribe_audio(audio_file, youtube_url)
    if not transcription:
        return jsonify({"error": "Transcription failed"}), 400

    translated_audio, translated_text = translate_text_to_audio(transcription, target_lang, youtube_url)
    if not translated_audio or not translated_text:
        return jsonify({"error": "Translation or TTS failed"}), 400

    return jsonify({
        "translated_text": translated_text,
        "audio_file": translated_audio  
    })

if __name__ == "__main__":
    app.run(debug=True)
