import os
import tempfile
import subprocess
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
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
    #result { margin-top: 24px; background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 20px; white-space: pre-wrap; display: none; }
    #download { display: none; margin-top: 12px; background: #10b981; }
  </style>
</head>
<body>
  <h1>🎬 Video Transcriber</h1>
  <p>Upload a video and get an AI-powered transcript instantly.</p>
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

            audio_path = os.path.join(tmpdir, "audio.mp3")
            subprocess.run([
                "ffmpeg", "-i", video_path,
                "-map", "a",
                "-ar", "16000",
                "-ac", "1",
                "-b:a", "32k",
                audio_path, "-y"
            ], check=True, capture_output=True)

            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )

            return JSONResponse({"transcript": transcript})

    except subprocess.CalledProcessError:
        return JSONResponse({"error": "Failed to extract audio."}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)