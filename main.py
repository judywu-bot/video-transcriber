{\rtf1\ansi\ansicpg1252\cocoartf2868
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fmodern\fcharset0 Courier;}
{\colortbl;\red255\green255\blue255;\red119\green61\blue243;\red245\green245\blue245;\red14\green16\blue19;
\red89\green152\blue85;\red20\green104\blue220;\red218\green109\blue27;\red253\green154\blue15;}
{\*\expandedcolortbl;;\cssrgb\c54510\c36078\c96471;\cssrgb\c96863\c96863\c96863;\cssrgb\c6667\c7843\c9412;
\cssrgb\c41569\c65098\c40784;\cssrgb\c7451\c49804\c89020;\cssrgb\c89020\c50588\c13333;\cssrgb\c100000\c66667\c5098;}
\margl1440\margr1440\vieww34360\viewh20320\viewkind0
\deftab720
\pard\pardeftab720\partightenfactor0

\f0\fs28 \cf2 \cb3 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 import\cf4 \strokec4  os\
\cf2 \strokec2 import\cf4 \strokec4  tempfile\
\cf2 \strokec2 import\cf4 \strokec4  subprocess\
\cf2 \strokec2 from\cf4 \strokec4  fastapi \cf2 \strokec2 import\cf4 \strokec4  FastAPI, UploadFile, File, Request\
\cf2 \strokec2 from\cf4 \strokec4  fastapi.responses \cf2 \strokec2 import\cf4 \strokec4  HTMLResponse, JSONResponse\
\cf2 \strokec2 from\cf4 \strokec4  fastapi.templating \cf2 \strokec2 import\cf4 \strokec4  Jinja2Templates\
\cf2 \strokec2 from\cf4 \strokec4  openai \cf2 \strokec2 import\cf4 \strokec4  OpenAI\
\
app = FastAPI()\
templates = Jinja2Templates(directory=\cf5 \strokec5 "templates"\cf4 \strokec4 )\
\
client = OpenAI(api_key=os.environ.get(\cf5 \strokec5 "OPENAI_API_KEY"\cf4 \strokec4 ))\
\
@app.get(\cf5 \strokec5 "/"\cf4 \strokec4 , response_class=HTMLResponse)\
\cf2 \strokec2 async\cf4 \strokec4  \cf2 \strokec2 def\cf6 \strokec6  home(\cf4 \strokec4 request: Request\cf6 \strokec6 ):\cf4 \strokec4 \
    \cf2 \strokec2 return\cf4 \strokec4  templates.TemplateResponse(\cf5 \strokec5 "index.html"\cf4 \strokec4 , \{\cf5 \strokec5 "request"\cf4 \strokec4 : request\})\
\
@app.post(\cf5 \strokec5 "/transcribe"\cf4 \strokec4 )\
\cf2 \strokec2 async\cf4 \strokec4  \cf2 \strokec2 def\cf6 \strokec6  transcribe(\cf4 \strokec4 file: UploadFile = File(...)\cf6 \strokec6 ):\cf4 \strokec4 \
    \cf2 \strokec2 try\cf4 \strokec4 :\
        \cf2 \strokec2 with\cf4 \strokec4  tempfile.TemporaryDirectory() \cf2 \strokec2 as\cf4 \strokec4  tmpdir:\
            \cf7 \strokec7 # Save uploaded video\cf4 \strokec4 \
            video_path = os.path.join(tmpdir, file.filename)\
            \cf2 \strokec2 with\cf4 \strokec4  \cf8 \strokec8 open\cf4 \strokec4 (video_path, \cf5 \strokec5 "wb"\cf4 \strokec4 ) \cf2 \strokec2 as\cf4 \strokec4  f:\
                content = \cf2 \strokec2 await\cf4 \strokec4  file.read()\
                f.write(content)\
\
            \cf7 \strokec7 # Extract audio using FFmpeg\cf4 \strokec4 \
            audio_path = os.path.join(tmpdir, \cf5 \strokec5 "audio.mp3"\cf4 \strokec4 )\
            subprocess.run([\
                \cf5 \strokec5 "ffmpeg"\cf4 \strokec4 , \cf5 \strokec5 "-i"\cf4 \strokec4 , video_path,\
                \cf5 \strokec5 "-q:a"\cf4 \strokec4 , \cf5 \strokec5 "0"\cf4 \strokec4 , \cf5 \strokec5 "-map"\cf4 \strokec4 , \cf5 \strokec5 "a"\cf4 \strokec4 ,\
                audio_path, \cf5 \strokec5 "-y"\cf4 \strokec4 \
            ], check=\cf8 \strokec8 True\cf4 \strokec4 , capture_output=\cf8 \strokec8 True\cf4 \strokec4 )\
\
            \cf7 \strokec7 # Transcribe with OpenAI Whisper\cf4 \strokec4 \
            \cf2 \strokec2 with\cf4 \strokec4  \cf8 \strokec8 open\cf4 \strokec4 (audio_path, \cf5 \strokec5 "rb"\cf4 \strokec4 ) \cf2 \strokec2 as\cf4 \strokec4  audio_file:\
                transcript = client.audio.transcriptions.create(\
                    model=\cf5 \strokec5 "whisper-1"\cf4 \strokec4 ,\
                    file=audio_file,\
                    response_format=\cf5 \strokec5 "text"\cf4 \strokec4 \
                )\
\
            \cf2 \strokec2 return\cf4 \strokec4  JSONResponse(\{\cf5 \strokec5 "transcript"\cf4 \strokec4 : transcript\})\
\
    \cf2 \strokec2 except\cf4 \strokec4  subprocess.CalledProcessError:\
        \cf2 \strokec2 return\cf4 \strokec4  JSONResponse(\{\cf5 \strokec5 "error"\cf4 \strokec4 : \cf5 \strokec5 "Failed to extract audio. Ensure the file is a valid video."\cf4 \strokec4 \}, status_code=\cf8 \strokec8 400\cf4 \strokec4 )\
    \cf2 \strokec2 except\cf4 \strokec4  Exception \cf2 \strokec2 as\cf4 \strokec4  e:\
        \cf2 \strokec2 return\cf4 \strokec4  JSONResponse(\{\cf5 \strokec5 "error"\cf4 \strokec4 : \cf8 \strokec8 str\cf4 \strokec4 (e)\}, status_code=\cf8 \strokec8 500\cf4 \strokec4 )}