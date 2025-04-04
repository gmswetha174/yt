from flask import Flask, render_template, request, jsonify
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import subprocess
import requests
import assemblyai as aai
from yt_dlp import YoutubeDL
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from collections import Counter
import time
import re
from transformers import pipeline

app = Flask(__name__)

progress_status = {}

ASSEMBLYAI_API_KEY = "966db5dbbc914cf4b787cd71c7fa517d"

available_languages = {
    'English (Global)': 'en', 'Spanish': 'es', 'French': 'fr', 'German': 'de',
    'Italian': 'it', 'Portuguese': 'pt', 'Dutch': 'nl', 'Arabic': 'ar',
    'Russian': 'ru', 'Chinese': 'zh', 'Japanese': 'ja', 'Korean': 'ko',
    'Hindi': 'hi', 'Bengali': 'bn', 'Urdu': 'ur', 'Persian': 'fa',
    'Turkish': 'tr', 'Hebrew': 'he', 'Tamil': 'ta', 'Telugu': 'te',
    'Marathi': 'mr', 'Punjabi': 'pa', 'Vietnamese': 'vi', 'Thai': 'th',
    'Indonesian': 'id', 'Malay': 'ms', 'Swahili': 'sw', 'Polish': 'pl',
    'Romanian': 'ro', 'Ukrainian': 'uk', 'Greek': 'el', 'Czech': 'cs',
    'Slovak': 'sk', 'Slovenian': 'sl', 'Serbian': 'sr', 'Croatian': 'hr',
    'Hungarian': 'hu', 'Danish': 'da', 'Swedish': 'sv', 'Norwegian': 'no',
    'Finnish': 'fi', 'Lithuanian': 'lt', 'Latvian': 'lv', 'Estonian': 'et',
    'Bulgarian': 'bg', 'Basque': 'eu', 'Georgian': 'ka', 'Armenian': 'hy',
    'Albanian': 'sq', 'Nepali': 'ne', 'Burmese': 'my', 'Sinhala': 'si',
    'Somali': 'so', 'Pashto': 'ps', 'Lao': 'lo', 'Kazakh': 'kk',
    'Uzbek': 'uz', 'Azerbaijani': 'az', 'Macedonian': 'mk', 'Yoruba': 'yo',
    'Haitian': 'ht'
}

summarizer = pipeline("summarization")

def update_progress(url, value):
    progress_status[url] = value
    print(f"[DEBUG] Progress for {url}: {value}%")  

@app.route('/progress', methods=['GET'])
def get_progress():
    url = request.args.get('url')
    return jsonify({"progress": progress_status.get(url, 0)})

def clear_old_audio():
    try:
        for file in os.listdir("static"):
            if file.startswith("downloaded_audio") or file == "translated_audio.mp3":
                os.remove(os.path.join("static", file))
    except Exception as e:
        print(f"Error clearing old audio files: {e}")

def download_audio(url):
    try:
        clear_old_audio()
        update_progress(url, 10)

        output_filename = "static/downloaded_audio"
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': f"{output_filename}.%(ext)s"}

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        downloaded_files = [f for f in os.listdir("static") if f.startswith("downloaded_audio")]
        audio_file = next((f for f in downloaded_files if f.endswith((".webm", ".m4a", ".mp4"))), None)

        if not audio_file:
            return None

        audio_path = os.path.join("static", audio_file)
        mp3_file = f"{output_filename}.mp3"

        if not audio_file.endswith(".mp3"):
            command = f'ffmpeg -i "{audio_path}" -vn -ar 44100 -ac 2 -b:a 192k "{mp3_file}"'
            subprocess.run(command, shell=True, check=True)
            os.remove(audio_path)

        update_progress(url, 30)
        return mp3_file if os.path.exists(mp3_file) else None
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None

def transcribe_audio(file_path, url):
    try:
        if not os.path.exists(file_path):
            return None

        update_progress(url, 50)

        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(file_path)

        if transcript and transcript.text:
            update_progress(url, 70)
            return transcript.text
        return None
    except Exception as e:
        print(f"Error in transcription: {e}")
        return None

def summarize_text(text):
    try:
        # Use pre-trained summarization model from HuggingFace
        summarized = summarizer(text, max_length=150, min_length=30, do_sample=False)
        return summarized[0]['summary_text']

    except Exception as e:
        print(f"Summarization error: {e}")
        return text

def translate_text(text, target_lang):
    try:
        if target_lang not in available_languages:
            return None
        
        lang_code = available_languages[target_lang]
        return GoogleTranslator(source="auto", target=lang_code).translate(text)

    except Exception as e:
        print(f"Error in translation: {e}")
        return None

def text_to_audio(text, target_lang, url):
    try:
        update_progress(url, 80)

        lang_code = available_languages[target_lang]
        text = text.replace("\n", " ")

        # Split text into <=5000 char chunks
        chunks = [text[i:i+4900] for i in range(0, len(text), 4900)]

        audio_file = f"static/translated_audio.mp3"
        temp_files = []

        for idx, chunk in enumerate(chunks):
            temp_file = f"static/temp_audio_{idx}.mp3"
            tts = gTTS(text=chunk, lang=lang_code)
            tts.save(temp_file)
            temp_files.append(temp_file)

        # Combine all audio chunks into a single file using ffmpeg
        if len(temp_files) == 1:
            os.rename(temp_files[0], audio_file)
        else:
            list_file = "static/audio_list.txt"
            with open(list_file, "w") as f:
                for file in temp_files:
                    f.write(f"file '{file}'\n")
            command = f"ffmpeg -y -f concat -safe 0 -i {list_file} -c copy {audio_file}"
            subprocess.run(command, shell=True, check=True)

            # Clean up
            for f in temp_files:
                os.remove(f)
            os.remove(list_file)

        update_progress(url, 100)
        return audio_file

    except Exception as e:
        print(f"Error in text-to-speech: {e}")
        return None


@app.route('/')
def home():
    return render_template('index.html', languages=available_languages)

@app.route('/process', methods=['POST'])
def process():
    youtube_url = request.form.get('url')
    target_lang = request.form.get('language')

    if not youtube_url or not target_lang:
        return jsonify({"error": "Missing YouTube URL or language"}), 400

    update_progress(youtube_url, 5)

    audio_file = download_audio(youtube_url)
    if not audio_file:
        return jsonify({"error": "Audio download failed"}), 400

    transcription = transcribe_audio(audio_file, youtube_url)
    if not transcription:
        return jsonify({"error": "Transcription failed"}), 400

    translated_text = translate_text(transcription, target_lang)
    if not translated_text:
        return jsonify({"error": "Translation failed"}), 400

    summarized_text = summarize_text(translated_text)

    translated_audio = text_to_audio(translated_text, target_lang, youtube_url)

    return jsonify({
        "translated_text": translated_text,  
        "summarized_text": summarized_text,  
        "audio_file": translated_audio
    })

if __name__ == "__main__":
    app.run(debug=True)