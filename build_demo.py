"""Render the two built-in films. Run locally with macOS voice or ElevenLabs."""

import argparse
import json

from demo import DEEP, DEMO, SCENES
from media import MEDIA, render

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["overview", "deep"])
    mode = parser.parse_args().mode
    identifier, frames = ("demo", SCENES) if mode == "overview" else ("demo-deep", DEEP)
    film = render(identifier, frames, print, 120 if mode == "overview" else None)
    film.update(mode=mode, method="Editorial walkthrough")
    (MEDIA / identifier / "story.json").write_text(
        json.dumps({"film": film, "paper": DEMO})
    )
    print(mode, film["duration"], flush=True)
