"""Read page-level evidence when arXiv has not published an HTML edition."""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import requests


def pdf_pages(url):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "paper.pdf"
        with requests.get(url, timeout=(5, 15), stream=True) as response:
            if not response.ok:
                return []
            with path.open("wb") as out:
                for chunk in response.iter_content(65536):
                    if out.tell() + len(chunk) > 24 * 1024 * 1024:
                        return []
                    out.write(chunk)
        with path.open("rb") as src:
            if b"%PDF-" not in src.read(1024):
                return []
        reader = subprocess.run(
            [sys.executable, __file__, str(path)],
            text=True,
            capture_output=True,
            timeout=18,
        )
        return json.loads(reader.stdout) if reader.returncode == 0 else []


def parse_pages(path):
    from pypdf import PdfReader

    pages = []
    reader = PdfReader(path, strict=False)
    for i, page in enumerate(reader.pages):
        if i >= 20:
            break
        raw = page.extract_text() or ""
        # References are rarely useful for explaining the paper's contribution.
        body = re.split(
            r"(?im)^\s*(?:\d+\.?\s+)?(?:References|Bibliography)\s*$", raw, maxsplit=1
        )[0]
        text = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", body)
        text = " ".join(text.split())
        if len(text) >= 140:
            pages.append((i + 1, text[:7500]))
        if body != raw:
            break
    return pages


if __name__ == "__main__":
    print(json.dumps(parse_pages(sys.argv[1])))
