import argparse
import json
import math
import os
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from media import MEDIA, ROOT, render, setting
from studio import assign_references, build_story, current_words, load_paper
from demo import DEMO

jobs = {}
lock = threading.Lock()
pool = ThreadPoolExecutor(max_workers=2)


def update(job, **changes):
    with lock:
        jobs[job].update(changes)


def story_from_id(identifier):
    if not isinstance(identifier, str) or not re.fullmatch(
        r"demo(?:-deep)?|[a-f0-9]{32}", identifier
    ):
        raise ValueError("Choose an existing video.")
    path = MEDIA / identifier / "story.json"
    if not path.is_file():
        raise ValueError("This video has expired. Import the paper again.")
    return json.loads(path.read_text())


def generate(job, data):
    try:
        if data.get("revoice"):
            if not setting("ELEVENLABS_API_KEY"):
                raise ValueError(
                    "Add ELEVENLABS_API_KEY to Replit Secrets or the local .env to enable sponsor narration."
                )
            original = story_from_id(data["revoice"])
            previous = original["film"]
            new_film = render(
                job,
                previous["scenes"],
                lambda msg: update(job, label=msg),
                120 if previous.get("mode") == "overview" else None,
            )
            item = {"paper": original["paper"], "film": {**previous, **new_film}}
            (MEDIA / job / "story.json").write_text(json.dumps(item))
            update(job, state="done", item=item)
            return
        question = str(data.get("question", "")).strip()[:800]
        mode = data.get("mode", "overview")
        if mode not in ("deep", "overview"):
            raise ValueError("Choose an overview or technical deep dive.")
        current = None
        moment = 0
        if question:
            parent = str(data.get("parent", ""))
            source = story_from_id(parent)
            paper = source["paper"]
            film = source["film"]
            moment = float(data.get("time", 0))
            if not math.isfinite(moment):
                raise ValueError("Invalid timestamp.")
            moment = max(0, min(moment, film["duration"]))
            current = next(s for s in reversed(film["scenes"]) if s["start"] <= moment)
        elif data.get("sourceFilm"):
            paper = story_from_id(data["sourceFilm"])["paper"]
        else:
            update(job, label="Reading the paper from arXiv")
            paper = load_paper(str(data.get("paper", "")))
        if (
            not question
            and paper["id"] == DEMO["id"]
            and not setting("ELEVENLABS_API_KEY")
        ):
            item = story_from_id("demo-deep" if mode == "deep" else "demo")
        else:
            update(job, label="Writing the illustrated explanation")
            scenes, method = build_story(paper, question, current, moment, mode)
            assign_references(scenes, paper)
            film = render(
                job,
                scenes,
                lambda message: update(job, label=message),
                120 if mode == "overview" and not question else None,
            )
            film.update(
                method=method, question=question, mode="answer" if question else mode
            )
            if question:
                film["parent"] = {
                    "id": parent,
                    "time": moment,
                    "title": current["title"],
                    "heard": current_words(current, moment),
                }
            item = dict(film=film, paper=paper)
            (MEDIA / job / "story.json").write_text(json.dumps(item))
        update(job, state="done", item=item)
    except Exception as err:
        message = (
            str(err)
            if isinstance(err, ValueError)
            else f"Generation failed ({type(err).__name__}). Check your connection and try again."
        )
        update(job, state="error", label=message)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "public"), **kwargs)

    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/generate":
            return self.reply(404, {})
        origin = self.headers.get("Origin")
        hosts = {self.headers.get("Host"), os.getenv("REPLIT_DEV_DOMAIN")}
        hosts.update(h.strip() for h in os.getenv("REPLIT_DOMAINS", "").split(","))
        if origin and urlsplit(origin).netloc not in hosts:
            return self.reply(403, {})
        try:
            n = int(self.headers.get("Content-Length", 0))
            if (
                not 0 < n <= 12000
                or self.headers.get_content_type() != "application/json"
            ):
                raise ValueError()
            data = json.loads(self.rfile.read(n))
            if not isinstance(data, dict):
                raise ValueError()
        except ValueError:
            return self.reply(400, {"label": "Invalid request."})
        job = uuid.uuid4().hex
        with lock:
            if sum(v["state"] == "working" for v in jobs.values()) >= 4:
                return self.reply(
                    429, {"label": "Four videos are rendering. Try again shortly."}
                )
            jobs[job] = dict(state="working", label="Queued for rendering")
        pool.submit(generate, job, data)
        self.reply(202, dict(job=job))

    def do_GET(self):
        if self.path.startswith("/api/job/"):
            with lock:
                status = dict(jobs.get(self.path.split("/")[-1], {}))
            return self.reply(200 if status else 404, status)
        if self.path == "/api/voice":
            return self.reply(200, {"elevenlabs": bool(setting("ELEVENLABS_API_KEY"))})
        path = self.translate_path(self.path)
        if path.endswith(".mp4") and (
            match := re.fullmatch(r"bytes=(\d+)-(\d*)", self.headers.get("Range", ""))
        ):
            from pathlib import Path

            file = Path(path)
            if not file.is_file():
                return self.send_error(404)
            size = file.stat().st_size
            start = int(match[1])
            end = min(int(match[2]) if match[2] else size - 1, size - 1)
            if start > end:
                return self.send_error(416)
            self.send_response(206)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(end - start + 1))
            self.end_headers()
            with file.open("rb") as f:
                f.seek(start)
                remaining = end - start + 1
                while remaining:
                    chunk = f.read(min(remaining, 65536))
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            return
        super().do_GET()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8765)))
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    port = args.port
    print(f"Paperframe running at http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer((args.host, port), Handler).serve_forever()
