from io import BytesIO
from threading import Lock
from urllib.parse import urlsplit
import base64
import math
import re
import os
import subprocess
import tempfile
import shutil
from functools import lru_cache
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont
from figures import attention_mix, referent, translation

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
        path = run(
            ["fc-match", "-f", "%{file}", family + (":style=Bold" if bold else "")]
        )
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


math_lock = Lock()


@lru_cache(maxsize=24)
def equation_picture(tex):
    # MathText uses a local parser. External TeX execution stays disabled.
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import math_to_image

    clean = tex.replace(r"\displaystyle", "").strip().rstrip(",")
    if len(clean) > 700 or "$" in clean:
        return None
    try:
        with math_lock:
            output = BytesIO()
            math_to_image(
                "$" + clean + "$",
                output,
                prop=FontProperties(size=20),
                dpi=175,
                format="png",
                color="#27264c",
            )
        output.seek(0)
        with Image.open(output) as source:
            result = source.convert("RGBA")
        result.thumbnail((1088, 248), Image.Resampling.LANCZOS)
        return result
    except (ValueError, RuntimeError, IndexError):
        return None


@lru_cache(maxsize=10)
def original_figure(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "arxiv.org":
        return None
    try:
        with requests.get(
            url, stream=True, timeout=(3, 8), allow_redirects=False
        ) as response:
            if response.status_code != 200:
                return None
            data = BytesIO()
            for chunk in response.iter_content(65536):
                if data.tell() + len(chunk) > 8 * 1024 * 1024:
                    return None
                data.write(chunk)
        data.seek(0)
        with Image.open(data) as source:
            if source.width * source.height > 15000000:
                return None
            source.thumbnail((1100, 355), Image.Resampling.LANCZOS)
            return source.convert("RGBA")
    except (
        requests.RequestException,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ):
        return None


def poster(scene, index, count, path, stage=None, progression=1.0):
    im = Image.new("RGB", (1280, 720), INK)
    d = ImageDraw.Draw(im)
    for x in range(0, 1280, 32):
        for y in range(0, 720, 32):
            d.ellipse((x, y, x + 2, y + 2), fill="#363962")
    d.rounded_rectangle((64, 48, 112, 91), radius=12, outline="#8f8aad", width=2)
    d.text((88, 70), f"{index + 1:02}", font=font(21), anchor="mm", fill="white")
    d.text(
        (130, 70),
        "PAPERFRAME   /   FIGURE STUDY",
        font=font(19, True),
        fill=LAV,
        anchor="lm",
    )
    titlefont = font(64, serif=True)
    for n, row in enumerate(lines(d, scene["title"], titlefont, 1150)[:2]):
        d.text((64, 112 + n * 68), row, font=titlefont, fill="#fffcfa")
    labels = scene["labels"]
    picture = equation_picture(scene["tex"]) if scene.get("tex") else None
    diagram = {
        "referent": referent,
        "mix": attention_mix,
        "translation": translation,
    }.get(scene.get("art"))
    source_figure = scene.get("source_figure", {})
    original = original_figure(source_figure["image"]) if source_figure else None
    if original is not None:
        d.rounded_rectangle((64, 245, 1216, 610), radius=13, fill="white")
        im.paste(
            original,
            ((1280 - original.width) // 2, 427 - original.height // 2),
            original,
        )
    elif diagram:
        diagram(d, font, stage, progression)
    elif picture is not None and scene.get("art") != "math":
        d.rounded_rectangle((64, 237, 1216, 525), radius=15, fill="white")
        im.paste(
            picture, ((1280 - picture.width) // 2, 380 - picture.height // 2), picture
        )
        d.text((65, 557), scene["reference"]["title"][:85], font=font(24), fill=LAV)
    elif scene.get("art") == "math":
        expression = scene["formula"]
        size = 54
        mathfont = font(size)
        while size > 19 and d.textlength(expression, font=mathfont) > 1120:
            size -= 2
            mathfont = font(size)
        d.rounded_rectangle(
            (64, 244, 1216, 415), radius=16, fill="#2b2c54", outline="#747299", width=2
        )
        if picture is not None:
            # Recolor the dark equation pixels gold on the film's dark panel.
            alpha = picture.convert("L").point(lambda value: max(0, 255 - value))
            stamp = Image.new("RGBA", picture.size, GOLD)
            im.paste(
                stamp, ((1280 - picture.width) // 2, 330 - picture.height // 2), alpha
            )
        else:
            d.text((640, 330), expression, font=mathfont, fill=GOLD, anchor="mm")
        for j, label in enumerate(labels):
            x = 76 + j * (1128 / len(labels))
            active = stage is None or stage == j
            d.line((x, 458, x + 102, 458), fill=GOLD if active else "#5d5d82", width=4)
            for n, row in enumerate(lines(d, label, font(25), 1030 / len(labels))[:3]):
                d.text(
                    (x, 478 + n * 32),
                    row,
                    font=font(25),
                    fill="white" if active else "#a3a3bf",
                )
    elif scene.get("art") == "attention":
        xs = [152, 395, 635, 875, 1122]
        for i, x in enumerate(xs):
            if i == 3 or (
                stage is not None and (stage == 0 or (stage == 1 and i != 0))
            ):
                continue
            height = [205, 145, 100, 0, 129][i]
            p = [
                (x + (875 - x) * t / 120, 465 - height * math.sin(math.pi * t / 120))
                for t in range(121)
            ]
            color = GOLD if i == 0 else "#8782c2"
            d.line(p, fill=color, width=6 if i == 0 else 3)
            d.ellipse((x - 5, 459, x + 5, 469), fill=color)
        for i, (x, label) in enumerate(zip(xs, labels)):
            d.rounded_rectangle(
                (x - 92, 474, x + 92, 542),
                radius=13,
                fill=GOLD if i == 3 else "#34355f",
                outline=GOLD if i in (0, 3) else "#7775a3",
                width=2,
            )
            d.text(
                (x, 508),
                label,
                font=font(30),
                fill=INK if i == 3 else "white",
                anchor="mm",
            )
        note = (
            "Read the tokens"
            if stage == 0
            else (
                "Possible referent" if stage == 1 else "Illustrative attention weights"
            )
        )
        d.text((514, 225), note, font=font(22), fill=GOLD, anchor="mm")
    elif scene.get("art") == "heads":
        colors = ["#c0bcff", "#ffda95", "#a6dae7"]
        for i, color in enumerate(colors):
            y = 309 + i * 75
            lit = stage is None or stage > 0 or i == 0
            ink = color if lit else "#686985"
            d.line([(253, 397), (398, y), (516, y)], fill=ink, width=4)
            d.rounded_rectangle((516, y - 23, 734, y + 23), radius=12, fill=ink)
            d.text(
                (625, y), f"Head {i + 1}", font=font(23, True), fill=INK, anchor="mm"
            )
            if stage is None or stage >= 2:
                d.line([(735, y), (849, y), (982, 397)], fill=ink, width=4)
        for x, label in [(190, "Tokens"), (1045, "Mix")]:
            d.ellipse((x - 67, 330, x + 67, 464), fill="#34355f", outline=LAV, width=3)
            d.text((x, 397), label, font=font(25), fill="white", anchor="mm")
        d.text(
            (640, 545),
            "Independent attention patterns",
            font=font(24),
            fill=LAV,
            anchor="mm",
        )
    else:
        step = 1144 / len(labels)
        for i, label in enumerate(labels):
            x = 68 + i * step
            lit = stage is None or stage >= i
            card = ["#d7d5fc", "#b4b7ed", "#ffdc9d"][i % 3] if lit else "#303254"
            fg = INK if lit else "#a7a7bc"
            d.rounded_rectangle((x, 300, x + step - 38, 515), radius=20, fill=card)
            d.text((x + 23, 324), f"{i + 1:02}", font=font(21), fill=fg)
            nft = font(34, True)
            for n, row in enumerate(lines(d, label, nft, step - 84)[:3]):
                d.text((x + 23, 373 + n * 41), row, font=nft, fill=fg)
            if i < len(labels) - 1:
                d.line((x + step - 34, 408, x + step - 8, 408), fill=LAV, width=3)
                d.polygon(
                    [(x + step - 8, 402), (x + step - 1, 408), (x + step - 8, 414)],
                    fill=LAV,
                )
    d.line((64, 634, 1216, 634), fill="#515477", width=2)
    d.text(
        (64, 657),
        source_figure["credit"] if original is not None else "Paperframe Studio",
        font=font(21, serif=True),
        fill="#dfddfe",
    )
    d.text(
        (1216, 658),
        f"FIG. {index + 1:02}   /   {count:02}",
        font=font(18),
        fill=LAV,
        anchor="ra",
    )
    im.save(path)


def run(args):
    return (
        subprocess.run(args, check=True, capture_output=True, timeout=120)
        .stdout.decode()
        .strip()
    )


def duration_of(path):
    return float(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(path),
            ]
        )
    )


def captions_for(text, duration, alignment=None):
    # Keep each cue short enough to read without covering the diagram.
    words = list(re.finditer(r"\S+", text))
    ends = (alignment or {}).get("character_end_times_seconds", [])
    aligned = "".join((alignment or {}).get("characters", [])) == text and len(
        ends
    ) == len(text)
    cues = []
    start, first = 0.0, 0
    for i, word in enumerate(words):
        length = i - first + 1
        if (
            length >= 10
            or i == len(words) - 1
            or (length >= 4 and word.group().endswith((".", "?", "!", ";", ",")))
        ):
            end = ends[word.end() - 1] if aligned else duration * (i + 1) / len(words)
            if i == len(words) - 1:
                end = duration
            cues.append((start, end, text[words[first].start() : word.end()]))
            start, first = end, i + 1
    return cues


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    minutes, ms = divmod(milliseconds, 60000)
    sec, ms = divmod(ms, 1000)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{sec:02}.{ms:03}"


def voice_audio(work, i, text, key, voice):
    if key:
        voice_id = setting("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps",
            headers={"xi-api-key": key},
            json={"text": text, "model_id": "eleven_multilingual_v2"},
            timeout=60,
        )
        if not response.ok:
            raise ValueError(
                f"ElevenLabs returned HTTP {response.status_code}. Check the key, voice access and credits."
            )
        payload = response.json()
        audio = work / f"voice{i}.mp3"
        audio.write_bytes(base64.b64decode(payload["audio_base64"], validate=True))
        return audio, payload.get("alignment")
    if voice == "eSpeak":
        audio = work / f"voice{i}.wav"
        run(["espeak-ng", "-s", "160", "-w", str(audio), "--", text])
    else:
        audio = work / f"voice{i}.aiff"
        run(["say", "-r", "169", "-o", str(audio), "--", text])
    return audio, None


def render(identifier, scenes, progress, target_seconds=None):
    directory = MEDIA / identifier
    directory.mkdir(parents=True, exist_ok=True)
    key = setting("ELEVENLABS_API_KEY")
    voice = "ElevenLabs" if key else ("macOS" if shutil.which("say") else "eSpeak")
    elapsed = 0.0
    captions = ["WEBVTT", ""]
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        tracks = []
        for i, s in enumerate(scenes):
            progress(f"Voicing scene {i + 1} of {len(scenes)} · {voice}")
            audio, alignment = voice_audio(work, i, s["narration"], key, voice)
            spoken = duration_of(audio)
            if spoken < 0.5:
                raise ValueError("Speech synthesis returned empty audio.")
            tracks.append((audio, alignment, spoken))
        raw_duration = sum(track[2] for track in tracks)
        # Short excerpts retain natural speech when the source cannot support two minutes.
        tempo = raw_duration / target_seconds if target_seconds else 1.0
        if not 0.76 <= tempo <= 1.32:
            tempo = 1.0
        for i, (s, (audio, alignment, original_duration)) in enumerate(
            zip(scenes, tracks)
        ):
            spoken = original_duration / tempo
            progress(f"Animating diagram {i + 1} of {len(scenes)}")
            poster(s, i, len(scenes), directory / f"{i}.png")
            files = []
            stages = (
                3
                if s.get("art") in ("attention", "heads")
                else min(3, len(s["labels"]))
            )
            boundaries = [spoken * k / stages for k in range(stages)] + [spoken]
            beats = s.get("beats", [])
            if beats:
                boundaries = [0.0]
                for phrase in beats:
                    offset = s["narration"].find(phrase)
                    if offset <= 0:
                        continue
                    ends = (alignment or {}).get("character_end_times_seconds", [])
                    if len(ends) == len(s["narration"]):
                        t = ends[offset - 1] / tempo
                    else:
                        t = (
                            spoken
                            * len(s["narration"][:offset].split())
                            / len(s["narration"].split())
                        )
                    if boundaries[-1] < t < spoken:
                        boundaries.append(t)
                boundaries.append(spoken)
            for stage, (begin, end) in enumerate(zip(boundaries, boundaries[1:])):
                animated = s.get("art") in ("referent", "mix") and stage > 0
                steps = 6 if animated else 1
                transition = min(0.7, (end - begin) * 0.4)
                for tick in range(steps):
                    frame = work / f"frame{i}-{stage}-{tick}.png"
                    poster(s, i, len(scenes), frame, stage, (tick + 1) / steps)
                    hold = (
                        transition / steps
                        if tick < steps - 1
                        else end - begin - (steps - 1) * transition / steps
                    )
                    files.extend([f"file '{frame.name}'", f"duration {hold:.6f}"])
            files.append(f"file '{frame.name}'")
            frames = work / f"frames{i}.txt"
            frames.write_text("\n".join(files) + "\n")
            video = work / f"{i}.mp4"
            run(
                [
                    "ffmpeg",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(frames),
                    "-i",
                    str(audio),
                    "-vf",
                    "fps=12,format=yuv420p",
                    "-c:v",
                    "libx264",
                    "-threads",
                    "2",
                    "-preset",
                    "veryfast",
                    "-af",
                    f"atempo={tempo:.8f},apad",
                    "-c:a",
                    "aac",
                    "-ar",
                    "44100",
                    "-ac",
                    "1",
                    "-t",
                    f"{spoken:.3f}",
                    str(video),
                ]
            )
            s["cues"] = []
            for start, end, line in captions_for(
                s["narration"], original_duration, alignment
            ):
                start, end = start / tempo, end / tempo
                s["cues"].append(
                    dict(start=elapsed + start, end=elapsed + end, text=line)
                )
                captions.extend(
                    [
                        f"{timestamp(elapsed + start)} --> {timestamp(elapsed + end)}",
                        line,
                        "",
                    ]
                )
            s.update(start=elapsed, image=f"/media/{identifier}/{i}.png")
            elapsed += duration_of(video)
        manifest = work / "parts.txt"
        manifest.write_text("".join(f"file '{i}.mp4'\n" for i in range(len(scenes))))
        run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(manifest),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(directory / "film.mp4"),
            ]
        )
    (directory / "captions.vtt").write_text("\n".join(captions))
    return dict(
        id=identifier,
        scenes=scenes,
        voice=voice,
        duration=duration_of(directory / "film.mp4"),
        url=f"/media/{identifier}/film.mp4",
        captions=f"/media/{identifier}/captions.vtt",
    )
