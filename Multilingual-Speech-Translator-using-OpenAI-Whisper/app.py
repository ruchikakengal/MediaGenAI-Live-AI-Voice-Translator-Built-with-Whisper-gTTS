# ===============================
# Install dependencies
# ===============================
!pip install SpeechRecognition googletrans==4.0.0-rc1 gTTS pydub moviepy soundfile openai-whisper flask flask-ngrok pyngrok yt_dlp -q

# ===============================
# Imports
# ===============================
import os
import io
import base64
from flask import Flask, request, jsonify, send_file
from pyngrok import ngrok
from gtts import gTTS
from googletrans import Translator
from moviepy.editor import VideoFileClip
import soundfile as sf
import whisper
from yt_dlp import YoutubeDL
import uuid

# ===============================
# Set your ngrok authtoken here
# ===============================
NGROK_AUTH_TOKEN = "33mJUw2EeWLbJ5BaQMIXVVxiEOB_3qDxVimYyfB1cvceFEPuU"
ngrok.set_auth_token(NGROK_AUTH_TOKEN)

# ===============================
# Utility function for unique filenames
# ===============================
def unique_name(prefix="file", suffix=""):
    return f"{prefix}_{uuid.uuid4().hex}{suffix}"

# ===============================
# Whisper model
# ===============================
print("⏳ Loading Whisper model...")
whisper_model = whisper.load_model("small")  # change to medium/large if you have GPU
print("✅ Whisper model loaded!")

# ===============================
# Translator & language map
# ===============================
translator = Translator()
lang_code_map = {
    "english": "en","hindi": "hi","bengali": "bn","tamil": "ta",
    "telugu": "te","kannada": "kn","malayalam": "ml","marathi": "mr",
    "gujarati": "gu","punjabi": "pa","nepali": "ne","assamese": "as"
}

# ===============================
# Core functions
# ===============================
def transcribe_audio(file_path):
    try:
        result = whisper_model.transcribe(file_path, fp16=False)
        return result["text"]
    except Exception as e:
        return f"[Transcription failed: {e}]"

def translate_text(text, target_lang):
    try:
        t_code = lang_code_map.get(target_lang, "en")
        return translator.translate(text, dest=t_code).text
    except Exception as e:
        return f"[Translation failed: {e}]"

def generate_tts(text, target_lang):
    t_code = lang_code_map.get(target_lang, "en")
    tts_path = f"uploads/{unique_name('tts','.mp3')}"
    try:
        tts = gTTS(text=text, lang=t_code)
        tts.save(tts_path)
        with open(tts_path, "rb") as f:
            b64_audio = base64.b64encode(f.read()).decode()
        return b64_audio
    except Exception as e:
        print("TTS error:", e)
        return None

def extract_audio_from_video(video_path):
    audio_path = video_path.rsplit('.', 1)[0] + "_audio.wav"
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path, fps=16000)
    return audio_path

def download_youtube_audio(youtube_url):
    """Download audio from YouTube URL and return path to .wav file"""
    os.makedirs("uploads", exist_ok=True)
    out_path = f"uploads/{unique_name('yt', '.wav')}"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_path.replace('.wav', ''),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'quiet': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    return out_path

# ===============================
# HTML frontend
# ===============================
html_code = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>🎧 Media-Gen AI Speech Translator</title>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: "Poppins", sans-serif;
      margin: 0;
      background: linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%);
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      padding: 30px 10px;
    }
    .container {
      background: rgba(255,255,255,0.9);
      border-radius: 20px;
      padding: 40px;
      width: 90%;
      max-width: 900px;
      box-shadow: 0 8px 40px rgba(0,0,0,0.15);
      text-align: left;
    }
    h1 {
      text-align: center;
      color: #1d4ed8;
      margin-bottom: 10px;
    }
    h2 {
      color: #2563eb;
      margin-top: 25px;
      margin-bottom: 10px;
      font-size: 20px;
      border-bottom: 2px solid #93c5fd;
      padding-bottom: 5px;
    }
    p.instruction {
      font-size: 14px;
      color: #1f2937;
      margin-bottom: 10px;
    }
    .upload-box {
      border: 2px dashed #93c5fd;
      border-radius: 12px;
      padding: 08px;
      cursor: pointer;
      font-weight: 600;
      color: #2563eb;
      background: rgba(255,255,255,0.6);
      text-align: center;
      margin-bottom: 10px;
    }
    .upload-box:hover {
      background: #2563eb;
      color: white;
      transform: scale(1.02);
    }
    input[type="file"] { display: none; }
    select, button, input[type="text"] {
      width: 100%;
      padding: 12px;
      border-radius: 10px;
      border: 1px solid #cbd5e1;
      font-size: 16px;
      margin-top: 8px;
      margin-bottom: 12px;
      font-weight: 600;
    }
    select { background-color: rgba(255,255,255,0.9); }
    button {
      background-color: #2563eb;
      color: white;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s ease;
    }
    button:hover:not(:disabled) {
      background-color: #1d4ed8;
      transform: scale(1.03);
    }
    button:disabled {
      background-color: #a5b4fc;
      cursor: not-allowed;
    }
    .filename { font-weight: bold; color: #1e40af; margin-bottom: 10px; }
    .output {
      background: rgba(243,244,246,0.7);
      padding: 15px;
      border-radius: 10px;
      margin-top: 20px;
      max-height: 300px;
      overflow-y: auto;
      font-size: 15px;
      color: #111827;
    }
    audio { width: 100%; margin-top: 10px; border-radius: 8px; }
    footer {
      margin-top: 25px;
      font-size: 13px;
      color: rgba(55,65,81,0.7);
      text-align: center;
    }
    .mic-btn {
      background-color: #2563eb;
      color: white;
      font-size: 16px;
      padding: 12px 0;
      border-radius: 50px;
      font-weight: 600;
      margin-top: 5px;
    }
    .mic-btn:hover { background-color: #dc2626; }
    .mic-btn.recording { background-color: #22c55e; animation: pulse 1s infinite; }
    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(34,197,94,0.7); }
      70% { box-shadow: 0 0 0 12px rgba(34,197,94,0); }
      100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>🎧 Media-Gen AI Speech Translator</h1>
    <p class="instruction">Step 1: Select the target language for translation and TTS output.</p>
    <p class="instruction">Step 2: Upload a YouTube video, audio file, video file, or record your voice.</p>
    <p class="instruction">Step 3: Step 3: Click the respective Process button to get transcription, translation, and audio output.</p>
    <!-- Output instruction -->
    <p class="instruction" style="font-size:13px; color:#1e40af;">
      ⚠️ Scroll down to view the transcription, translation, and audio output.
    </p>

    <!-- Language Selection -->
    <h2>Select Target Translation Language”</h2>
    <select id="langSelect">
      <option value="english">English</option>
      <option value="hindi">Hindi</option>
      <option value="bengali">Bengali</option>
      <option value="tamil">Tamil</option>
      <option value="telugu">Telugu</option>
      <option value="kannada">Kannada</option>
      <option value="malayalam">Malayalam</option>
      <option value="marathi">Marathi</option>
      <option value="gujarati">Gujarati</option>
      <option value="punjabi">Punjabi</option>
      <option value="nepali">Nepali</option>
      <option value="assamese">Assamese</option>
    </select>

    <!-- YouTube URL -->
    <h2>Process YouTube Video</h2>
    <input type="text" id="youtubeUrl" placeholder="Paste YouTube URL here...">
    <button id="processYouTubeBtn">🎬 Process YouTube Video</button>

    <!-- Audio Upload -->
    <h2>Upload Audio File</h2>
    <label class="upload-box">
      Select Audio File
      <input type="file" id="audioInput" accept="audio/*">
    </label>
    <div id="audioName" class="filename"></div>
    <button id="processAudioBtn" disabled>🚀 Process Audio</button>

    <!-- Video Upload -->
    <h2>Upload Video File</h2>
    <label class="upload-box">
      Select Video File
      <input type="file" id="videoInput" accept="video/*">
    </label>
    <div id="videoName" class="filename"></div>
    <button id="processVideoBtn" disabled>🚀 Process Video</button>

    <!-- Mic Recording -->
    <h2>Record Your Voice</h2>
    <button id="recordBtn" class="mic-btn">🎙 Start Recording</button>
    <audio id="recordedAudio" controls hidden></audio>


  <!-- Output -->
    <div class="output" id="outputBox"></div>
  </div>

  <script>
    const audioInput = document.getElementById('audioInput');
    const videoInput = document.getElementById('videoInput');
    const youtubeUrl = document.getElementById('youtubeUrl');
    const processAudioBtn = document.getElementById('processAudioBtn');
    const processVideoBtn = document.getElementById('processVideoBtn');
    const processYouTubeBtn = document.getElementById('processYouTubeBtn');
    const recordBtn = document.getElementById('recordBtn');
    const recordedAudio = document.getElementById('recordedAudio');
    const langSelect = document.getElementById('langSelect');
    const outputBox = document.getElementById('outputBox');
    const audioName = document.getElementById('audioName');
    const videoName = document.getElementById('videoName');

    let selectedAudio = null;
    let selectedVideo = null;
    let mediaRecorder, audioChunks = [];

    audioInput.addEventListener('change', e => {
      selectedAudio = e.target.files[0];
      audioName.innerText = selectedAudio ? selectedAudio.name : "";
      processAudioBtn.disabled = !selectedAudio;
    });

    videoInput.addEventListener('change', e => {
      selectedVideo = e.target.files[0];
      videoName.innerText = selectedVideo ? selectedVideo.name : "";
      processVideoBtn.disabled = !selectedVideo;
    });

    async function processFile(file, youtube_url=null) {
      outputBox.innerHTML = "<p>⏳ Processing... please wait</p>";
      const formData = new FormData();
      if(file) formData.append("file", file);
      if(youtube_url) formData.append("youtube_url", youtube_url);
      formData.append("target_lang", langSelect.value);

      try {
        const res = await fetch("/process", { method: "POST", body: formData });
        const data = await res.json();
        if (data.error) {
          outputBox.innerHTML = `<p style='color:red;'>${data.error}</p>`;
          return;
        }
        outputBox.innerHTML = `<p><strong>🗣 Transcription:</strong> ${data.transcription}</p>
                               <p><strong>🌐 Translation (${langSelect.value}):</strong> ${data.translation}</p>`;
        if (data.tts_base64) {
          const audioEl = document.createElement("audio");
          audioEl.controls = true;
          audioEl.src = "data:audio/mp3;base64," + data.tts_base64;
          outputBox.appendChild(audioEl);
        }
      } catch (err) {
        outputBox.innerHTML = `<p style='color:red;'>⚠ Error: ${err}</p>`;
      }
    }

    processAudioBtn.addEventListener('click', () => processFile(selectedAudio));
    processVideoBtn.addEventListener('click', () => processFile(selectedVideo));
    processYouTubeBtn.addEventListener('click', () => {
      const url = youtubeUrl.value.trim();
      if(!url) return alert("Please enter a YouTube URL!");
      processFile(null, url);
    });

    recordBtn.addEventListener('click', async () => {
      if (recordBtn.textContent.includes("Start")) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = () => {
          const blob = new Blob(audioChunks, { type: 'audio/wav' });
          recordedAudio.src = URL.createObjectURL(blob);
          recordedAudio.hidden = false;
          const file = new File([blob], "mic_recording.wav");
          processFile(file);
        };
        mediaRecorder.start();
        recordBtn.textContent = "⏹ Stop Recording";
        recordBtn.classList.add("recording");
      } else {
        mediaRecorder.stop();
        recordBtn.textContent = "🎙 Start Recording";
        recordBtn.classList.remove("recording");
      }
    });
  </script>
</body>
</html>



"""

# Save HTML
with open("index.html", "w") as f:
    f.write(html_code)

# ===============================
# Flask app
# ===============================
app = Flask(__name__)

@app.route('/')
def home():
    return send_file("index.html")

@app.route("/process", methods=['POST'])
def process_file():
    target_lang = request.form.get("target_lang", "english")
    youtube_url = request.form.get("youtube_url", "").strip()
    file = request.files.get("file")
    os.makedirs("uploads", exist_ok=True)

    try:
        if youtube_url:
            file_path = download_youtube_audio(youtube_url)
        elif file:
            file_path = f"uploads/{file.filename}"
            file.save(file_path)
            if file.filename.lower().endswith(('.mp4','.avi','.mov','.mkv')):
                file_path = extract_audio_from_video(file_path)
        else:
            return jsonify({"error":"No file or YouTube URL provided"}), 400

        transcription = transcribe_audio(file_path)
        translation = translate_text(transcription, target_lang)
        tts_base64 = generate_tts(translation, target_lang)

        return jsonify({"transcription": transcription, "translation": translation, "tts_base64": tts_base64})
    except Exception as e:
        return jsonify({"error": f"Server error: {e}"}), 500

# ===============================
# Start ngrok + Flask
# ===============================
public_url = ngrok.connect(5000).public_url
print("🌍 Public URL:", public_url)

app.run(port=5000)
