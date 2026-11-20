"""Verify the Replit startup command exposes both tracks and a playable answer."""

import time
import requests

base = "http://127.0.0.1:3000"


def generate(data):
    r = requests.post(base + "/api/generate", json=data, timeout=5)
    r.raise_for_status()
    endpoint = base + "/api/job/" + r.json()["job"]
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        job = requests.get(endpoint, timeout=5).json()
        if job["state"] == "error":
            raise RuntimeError(job["label"])
        if job["state"] == "done":
            return job["item"]["film"]
        time.sleep(0.3)
    raise TimeoutError("Render took longer than 90 seconds")


overview = generate({"paper": "1706.03762", "mode": "overview"})
assert abs(overview["duration"] - 120) < 1 and overview["mode"] == "overview"
deep = generate({"paper": "1706.03762", "mode": "deep"})
assert deep["duration"] > overview["duration"] and deep["mode"] == "deep"
answer = generate(
    {
        "parent": deep["id"],
        "time": 65,
        "question": "How does softmax compute the weights?",
    }
)
assert answer["parent"]["time"] == 65 and answer["parent"]["id"] == deep["id"]
r = requests.get(base + answer["url"], headers={"Range": "bytes=0-63"}, timeout=5)
assert r.status_code == 206 and len(r.content) == 64
assert requests.get(base + answer["captions"], timeout=5).text.startswith("WEBVTT")
print(
    "Replit startup, both video tracks, paused questions, captions and streamed MP4 verified."
)
