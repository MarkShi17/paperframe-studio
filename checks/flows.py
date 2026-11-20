"""Check the citation contract, timestamp grounding, and sponsor speech adapter."""

import base64
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo import DEMO
from media import captions_for, voice_audio
from scriptwriter import grounded_frames
from studio import current_words
from technical import technical_story

passages = [("Methods", "A query is compared with each key to obtain a row of scores.")]
frame = {
    "title": "Score one row",
    "narration": "Compare a query with each key to obtain a row of scores.",
    "labels": ["Query", "Keys", "Scores"],
    "source_ids": [0],
}
paper = {
    "source": "https://arxiv.org/abs/1706.03762",
    "references": {
        "Methods": {
            "title": "Methods",
            "url": "https://arxiv.org/html/1706.03762#S3.SS2",
        }
    },
}


def validate():
    return grounded_frames(json.dumps({"scenes": [frame]}), passages, paper)


assert validate()[0]["evidence"] == passages[0][1]
frame["source_ids"] = [99]
assert validate() == []
with tempfile.TemporaryDirectory() as tmp:
    alignment = {
        "characters": list("A B."),
        "character_end_times_seconds": [0.2, 0.3, 0.5, 0.8],
    }
    reply = Mock(ok=True)
    reply.json.return_value = {
        "audio_base64": base64.b64encode(b"audio fixture").decode(),
        "alignment": alignment,
    }
    with patch("media.requests.post", return_value=reply) as call:
        audio, actual = voice_audio(Path(tmp), 0, "A B.", "fixture-key", "ElevenLabs")
    assert audio.read_bytes() == b"audio fixture" and actual == alignment
    assert call.call_args.args[0].endswith("/with-timestamps")
    assert call.call_args.kwargs["headers"]["xi-api-key"] == "fixture-key"
    assert call.call_args.kwargs["json"]["text"] == "A B."
    assert captions_for("A B.", 0.8, alignment) == [(0.0, 0.8, "A B.")]
frames, method = technical_story(DEMO)
assert len(frames) >= 5 and all(f.get("reference") and f.get("tex") for f in frames)
scene = {
    "cues": [
        {"start": 10, "end": 13, "text": "The first operation."},
        {"start": 13, "end": 16, "text": "The next operation."},
    ]
}
assert current_words(scene, 14) == "The first operation. The next operation."
try:
    technical_story({"id": "example", "sections": [("Abstract", "An abstract.")]})
except ValueError as exc:
    assert "full paper" in str(exc)
else:
    raise AssertionError("Technical track accepted abstract-only evidence")
print(
    "Verified cited scenes, cue grounding, technical evidence requirements, and the ElevenLabs request contract."
)
