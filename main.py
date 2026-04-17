import os
import tempfile
import subprocess
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from openai import OpenAI

app = FastAPI()
templates = Jinja2Templates(directory="templates")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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
                "-q:a", "0", "-map", "a",
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