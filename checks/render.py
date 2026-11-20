"""Exercise the Linux/Replit rendering path with no provider credentials."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import media
from demo import scene

with tempfile.TemporaryDirectory() as tmp:
    media.MEDIA = Path(tmp)
    frames = [
        scene(
            "One query, two keys",
            "Each query compares with two keys. Weights determine each value's contribution.",
            ["Query", "Keys", "Values"],
        )
    ]
    result = media.render("check", frames, print)
    root = media.MEDIA / "check"
    streams = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-of",
                "json",
                str(root / "film.mp4"),
            ]
        )
    )["streams"]
    assert {s["codec_name"] for s in streams} == {"h264", "aac"}
    assert result["duration"] > 1 and result["scenes"][0]["start"] == 0
    assert "WEBVTT" in (root / "captions.vtt").read_text()
    assert (root / "0.png").stat().st_size > 1000
