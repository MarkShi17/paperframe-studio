import math
import os
import subprocess
import tempfile
import shutil
from functools import lru_cache
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MEDIA = ROOT / "public/media"
FONT = Path("/System/Library/Fonts/Supplemental")
INK, LAV, GOLD = "#191d48", "#c0bcff", "#ffd989"

def setting(key, default=""):
    if os.environ.get(key):
        return os.environ[key]
    file = ROOT / ".env"
    if file.exists():
        for line in file.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() == key:
                return value.strip().strip('"').strip("'")
    return default

@lru_cache(maxsize=32)
def font(size, bold=False, serif=False):
    face = "Georgia" if serif else "Arial"
    if FONT.exists():
        path = FONT / (face + (" Bold" if bold else "") + ".ttf")
    else:
        family = "DejaVu Serif" if serif else "DejaVu Sans"
        path = run(["fc-match","-f","%{file}",family + (":style=Bold" if bold else "")])
    return ImageFont.truetype(str(path), size)

def lines(draw, text, face, width):
    rows = [""]
    for word in text.split():
        candidate = (rows[-1] + " " + word).strip()
        if rows[-1] and draw.textlength(candidate, font=face) > width:
            rows.append(word)
        else:
            rows[-1] = candidate
    return rows

def poster(scene, index, count, path):
    im = Image.new("RGB", (1280,720), INK)
    d = ImageDraw.Draw(im)
    for x in range(0,1280,32):
        for y in range(0,720,32):
            d.ellipse((x,y,x+2,y+2),fill="#363962")
    d.rounded_rectangle((64,48,112,91),radius=12,outline="#8f8aad",width=2)
    d.text((88,70),f"{index+1:02}",font=font(21),anchor="mm",fill="white")
    d.text((130,70),"PAPERFRAME   /   FIGURE STUDY",font=font(19,True),fill=LAV,anchor="lm")
    titlefont = font(64,serif=True)
    for n,row in enumerate(lines(d,scene["title"],titlefont,1150)[:2]):
        d.text((64,112+n*68),row,font=titlefont,fill="#fffcfa")
    labels = scene["labels"]
    if scene.get("art") == "attention":
        xs=[152,395,635,875,1122]
        for i,x in enumerate(xs):
            if i==3: continue
            height=[205,145,100,0,129][i]
            p=[(x+(875-x)*t/120,465-height*math.sin(math.pi*t/120)) for t in range(121)]
            color=GOLD if i==0 else "#8782c2"
            d.line(p,fill=color,width=6 if i==0 else 3)
            d.ellipse((x-5,459,x+5,469),fill=color)
        for i,(x,label) in enumerate(zip(xs,labels)):
            d.rounded_rectangle((x-92,474,x+92,542), radius=13, fill=GOLD if i==3 else "#34355f",outline=GOLD if i in (0,3) else "#7775a3",width=2)
            d.text((x,508),label,font=font(30),fill=INK if i==3 else "white",anchor="mm")
        d.text((514,225),"illustrative attention weight",font=font(20),fill=GOLD,anchor="mm")
    else:
        step=1144/len(labels)
        for i,label in enumerate(labels):
            x=68+i*step
            d.rounded_rectangle((x,300,x+step-38,515),radius=20,fill=["#d7d5fc","#b4b7ed","#ffdc9d"][i%3])
            d.text((x+23,324),f"{i+1:02}",font=font(21),fill=INK)
            nft=font(34,True)
            for n,row in enumerate(lines(d,label,nft,step-84)[:3]):
                d.text((x+23,373+n*41),row,font=nft,fill=INK)
            if i<len(labels)-1:
                d.line((x+step-34,408,x+step-8,408),fill=LAV,width=3)
                d.polygon([(x+step-8,402),(x+step-1,408),(x+step-8,414)],fill=LAV)
    d.line((64,634,1216,634),fill="#515477",width=2)
    d.text((64,657),"Paperframe Studio",font=font(21,serif=True),fill="#dfddfe")
    d.text((1216,658),f"FIG. {index+1:02}   /   {count:02}",font=font(18),fill=LAV,anchor="ra")
    im.save(path)

def run(args):
    return subprocess.run(args,check=True,capture_output=True,timeout=120).stdout.decode().strip()

def render(identifier, scenes, progress):
    directory=MEDIA/identifier
    directory.mkdir(parents=True,exist_ok=True)
    key=setting("ELEVENLABS_API_KEY")
    voice="ElevenLabs" if key else ("macOS" if shutil.which("say") else "eSpeak")
    elapsed=0
    with tempfile.TemporaryDirectory() as tmp:
        work=Path(tmp)
        for i,s in enumerate(scenes):
            progress(f"Voicing scene {i+1} of {len(scenes)} · {voice}")
            audio=work/f"voice{i}.{'mp3' if key else 'aiff'}"
            if key:
                response=requests.post("https://api.elevenlabs.io/v1/text-to-speech/"+setting("ELEVENLABS_VOICE_ID","JBFqnCBsd6RMkjVDRZzb"), headers={"xi-api-key":key}, json={"text":s["narration"],"model_id":"eleven_multilingual_v2"},timeout=60)
                if not response.ok:
                    raise ValueError(f"ElevenLabs returned HTTP {response.status_code}. Check your key, voice access and credits.")
                audio.write_bytes(response.content)
            elif voice=="eSpeak":
                audio=work/f"voice{i}.wav"
                run(["espeak-ng","-s","160","-w",str(audio),s["narration"]])
            else:
                run(["say","-r","169","-o",str(audio),s["narration"]])
            progress(f"Rendering diagram {i+1} of {len(scenes)}")
            png=directory/f"{i}.png"
            poster(s,i,len(scenes),png)
            video=work/f"{i}.mp4"
            run(["ffmpeg","-loglevel","error","-y","-loop","1","-framerate","12","-i",str(png),"-i",str(audio),"-vf","format=yuv420p","-c:v","libx264","-preset","ultrafast","-tune","stillimage","-c:a","aac","-ar","44100","-ac","1","-shortest",str(video)])
            duration=float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(video)]))
            if duration < 1: raise ValueError("Speech synthesis returned empty audio.")
            s.update(start=elapsed,image=f"/media/{identifier}/{i}.png")
            elapsed+=duration
        manifest=work/"parts.txt"
        manifest.write_text("".join(f"file '{i}.mp4'\n" for i in range(len(scenes))))
        run(["ffmpeg","-loglevel","error","-y","-f","concat","-safe","0","-i",str(manifest),"-c","copy","-movflags","+faststart",str(directory/"film.mp4")])
    return dict(id=identifier,scenes=scenes,voice=voice,duration=elapsed,url=f"/media/{identifier}/film.mp4")
