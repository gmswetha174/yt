

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
        start_time = time.time()  # Start timing
        clear_old_audio()
        update_progress(url, 10)

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

        update_progress(url, 30)
        return mp3_file if os.path.exists(mp3_file) else None
    except Exception as e:
        return None

def transcribe_audio(file_path, url):
    try:
        start_time = time.time()
        if not os.path.exists(file_path):
            return None

        update_progress(url, 50)

        # Set API key
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        
        # Initialize Transcriber
        transcriber = aai.Transcriber()
        
        # Upload file and transcribe
        transcript = transcriber.transcribe(file_path)

        if transcript and transcript.text:
            update_progress(url, 70)
            return transcript.text
        else:
            return None
    except Exception as e:
        print(f"[ERROR] Exception in transcribe_audio: {e}")
        return None

def summarize_text(text):
    try:
        sentences = sent_tokenize(text)
        if len(sentences) <= 3:
            return text  

        words = word_tokenize(text)
        word_frequencies = Counter(words)

        sentence_scores = {}
        for sentence in sentences:
            for word in word_tokenize(sentence.lower()):
                if word in word_frequencies:
                    sentence_scores[sentence] = sentence_scores.get(sentence, 0) + word_frequencies[word]

        ranked_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)
        summary_sentences = ranked_sentences[:max(3, len(sentences) // 3)]  

        return " ".join(summary_sentences)

    except Exception as e:
        print(f"Error in text summarization: {e}")
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
        audio_file = f"static/translated_audio.mp3"
        tts = gTTS(text=text.replace("\n", " "), lang=lang_code)
        tts.save(audio_file)

        update_progress(url, 100)
        return audio_file  

    except Exception as e:
        print(f"Error in text-to-sspeech: {e}")
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
