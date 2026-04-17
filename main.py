import os
import re
import tempfile
import subprocess
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Video Transcriber</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 700px; margin: 60px auto; padding: 0 20px; background: #f9f9f9; }
    h1 { color: #333; }
    .drop-zone { border: 2px dashed #aaa; border-radius: 12px; padding: 40px; text-align: center; cursor: pointer; background: #fff; }
    .drop-zone input { display: none; }
    button { margin-top: 20px; padding: 12px 30px; background: #4f46e5; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; }
    button:disabled { background: #aaa; cursor: not-allowed; }
    #status { margin-top: 16px; color: #555; font-style: italic; }
    #result { margin-top: 24px; background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 20px; white-space: pre-wrap; display: none; font-family: monospace; font-size: 14px; line-height: 1.8; }
    #download { display: none; margin-top: 12px; background: #10b981; }
  </style>
</head>
<body>
  <h1>🎬 Video Transcriber</h1>
  <p>Upload a video and get an AI-powered transcript with timestamps instantly.</p>
  <div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
    <input type="file" id="fileInput" accept="video/*" />
    <p>📁 Drag & drop your video here, or <strong>click to browse</strong></p>
    <p id="fileName" style="color:#4f46e5; font-weight:bold;"></p>
  </div>
  <button id="uploadBtn" onclick="uploadFile()" disabled>Transcribe Video</button>
  <p id="status"></p>
  <div id="result"></div>
  <button id="download" onclick="downloadTranscript()">⬇️ Download Transcript</button>
  <script>
    const fileInput = document.getElementById('fileInput');
    let selectedFile = null;
    fileInput.addEventListener('change', (e) => {
      selectedFile = e.target.files[0];
      if (selectedFile) {
        document.getElementById('fileName').textContent = 'Selected: ' + selectedFile.name;
        document.getElementById('uploadBtn').disabled = false;
      }
    });
    async function uploadFile() {
      if (!selectedFile) return;
      const formData = new FormData();
      formData.append('file', selectedFile);
      document.getElementById('uploadBtn').disabled = true;
      document.getElementById('status').textContent = '⏳ Processing video... this may take a few minutes for large files.';
      document.getElementById('result').style.display = 'none';
      document.getElementById('download').style.display = 'none';
      try {
        const res = await fetch('/transcribe', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.transcript) {
          document.getElementById('result').textContent = data.transcript;
          document.getElementById('result').style.display = 'block';
          document.getElementById('download').style.display = 'inline-block';
          document.getElementById('status').textContent = '✅ Transcription complete!';
        } else {
          document.getElementById('status').textContent = '❌ Error: ' + data.error;
        }
      } catch (err) {
        document.getElementById('status').textContent = '❌ Unexpected error: ' + err.message;
      }
      document.getElementById('uploadBtn').disabled = false;
    }
    function downloadTranscript() {
      const text = document.getElementById('result').textContent;
      const blob = new Blob([text], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'transcript.txt';
      a.click();
    }
  </script>
</body>
</html>
"""

class VideoURL(BaseModel):
    url: str

def resolve_google_drive_url(url: str) -> str:
    """Convert Google Drive sharing link to direct download link."""
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&confirm=t&id={file_id}"
    return url

def format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"[{minutes:02d}:{secs:02d}]"

def transcribe_audio(audio_path: str) -> str:
    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )
    lines = []
    for segment in response.segments:
        timestamp = format_timestamp(segment.start)
        lines.append(f"{timestamp} {segment.text.strip()}")
    return "\n".join(lines)

def extract_audio(video_path: str, tmpdir: str) -> str:
    audio_path = os.path.join(tmpdir, "audio.mp3")
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-map", "a",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "32k",
        audio_path, "-y"
    ], check=True, capture_output=True)
    return audio_path

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, file.filename)
            with open(video_path, "wb") as f:
                content = await file.read()
                f.write(content)
            audio_path = extract_audio(video_path, tmpdir)
            transcript = transcribe_audio(audio_path)
            return JSONResponse({"transcript": transcript})
    except subprocess.CalledProcessError:
        return JSONResponse({"error": "Failed to extract audio."}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/transcribe-url")
async def transcribe_url(body: VideoURL):
    try:
        url = body.url
        # Auto-convert Google Drive sharing links
        if "drive.google.com" in url:
            url = resolve_google_drive_url(url)

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            session = requests.Session()
            response = session.get(url, stream=True, timeout=120)
            with open(video_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            audio_path = extract_audio(video_path, tmpdir)
            transcript = transcribe_audio(audio_path)
            return JSONResponse({"transcript": transcript})
    except subprocess.CalledProcessError:
        return JSONResponse({"error": "Failed to extract audio."}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)