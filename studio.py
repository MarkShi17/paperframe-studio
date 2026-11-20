import json
import re
import subprocess
from urllib.parse import urlsplit, urljoin

import requests
from bs4 import BeautifulSoup

from demo import DEMO, DETAILS, SCENES, scene
from media import ROOT, setting


def arxiv_id(value):
    value = value.strip()
    if "://" in value:
        parsed = urlsplit(value)
        if parsed.hostname not in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
            raise ValueError("Paste a link from arxiv.org or an arXiv identifier.")
        value = re.sub(r"^/(abs|pdf|html)/", "", parsed.path)
    value = re.sub(r"^arxiv:\s*", "", value, flags=re.I).removesuffix(".pdf")
    if not re.fullmatch(r"(?:\d{4}\.\d{4,5}|[a-z][a-z.\-]+/\d{7})(?:v\d+)?", value):
        raise ValueError("Enter an arXiv ID such as 1706.03762 or its paper URL.")
    return value


def load_paper(value):
    aid = arxiv_id(value)
    if aid in ("1706.03762", "1706.03762v7"):
        return DEMO
    base = "https://arxiv.org/"
    response = requests.get(base + "abs/" + aid, timeout=20)
    if not response.ok:
        raise ValueError(
            f"arXiv returned HTTP {response.status_code}. Check the ID or try again."
        )
    soup = BeautifulSoup(response.content, "html.parser")

    def metas(name):
        return [m.get("content", "") for m in soup.select(f'meta[name="{name}"]')]

    title = metas("citation_title")
    abstract = soup.select_one("blockquote.abstract")
    if not title or not abstract:
        raise ValueError("arXiv did not return paper metadata for this ID.")
    abstract = re.sub(r"^Abstract:\s*", "", abstract.get_text(" ", strip=True))
    sections = [("Abstract", " ".join(abstract.split()))]
    references = {"Abstract": {"title": "Abstract", "url": base + "abs/" + aid}}
    figures = []
    try:
        html = requests.get(base + "html/" + aid, timeout=12)
        if html.ok:
            doc = BeautifulSoup(html.content, "html.parser")
            seen = set()
            for figure in doc.select("figure[id]"):
                image = figure.find("img", src=True)
                caption = figure.find("figcaption")
                if not image or not caption:
                    continue
                image_url = urljoin(html.url, image["src"])
                if urlsplit(image_url).hostname != "arxiv.org" or image_url in seen:
                    continue
                seen.add(image_url)
                figures.append(
                    {
                        "caption": caption.get_text(" ", strip=True)[:1000],
                        "image": image_url,
                        "url": html.url + "#" + figure["id"],
                    }
                )
                if len(figures) >= 5:
                    break
            for block in doc.select("section.ltx_section")[:12]:
                h = block.find(["h2", "h3"])
                paras = block.select("p.ltx_p")
                if h and paras:
                    name = h.get_text(" ", strip=True)
                    if re.search(r"acknowledg|references|bibliography", name, re.I):
                        continue
                    references[name] = {
                        "title": name,
                        "url": html.url + "#" + block.get("id", ""),
                    }
                    sections.append(
                        (
                            name,
                            " ".join(p.get_text(" ", strip=True) for p in paras)[:9000],
                        )
                    )
    except requests.RequestException:
        pass
    authors = metas("citation_author")
    return dict(
        id=aid,
        title=title[0],
        authors=(authors or ["Unknown authors"])[0]
        + (" et al." if len(authors) > 1 else ""),
        date=(metas("citation_date") or [""])[0],
        source=base + "abs/" + aid,
        sections=sections,
        references=references,
        figures=figures,
        scope="Paper walkthrough" if len(sections) > 1 else "Abstract walkthrough",
    )


STOP = set(
    "what when which does that those have this from were about mean explain could would make with more into your there their show paper example give simple scene please why how the and are for can".split()
)


def words(s):
    return set(re.findall(r"[a-z0-9]{2,}", s.lower())) - STOP


def valid_frames(frames):
    if not isinstance(frames, list) or not 1 <= len(frames) <= 4:
        return False
    for frame in frames:
        if not isinstance(frame, dict):
            return False
        title, narration, labels = (
            frame.get(k) for k in ("title", "narration", "labels")
        )
        if not isinstance(title, str) or not 1 <= len(title) <= 110:
            return False
        if not isinstance(narration, str) or not 20 <= len(narration) <= 1400:
            return False
        if not isinstance(labels, list) or not 2 <= len(labels) <= 3:
            return False
        if not all(isinstance(label, str) and 0 < len(label) <= 80 for label in labels):
            return False
    return True


def assign_references(frames, paper):
    references = paper.get("references", {})
    for f in frames:
        if f.get("reference"):
            continue
        tokens = words(f["title"] + " " + f["narration"])
        name, _ = max(
            paper["sections"],
            key=lambda x: (
                sum(
                    len(tokens & words(piece)) ** 2
                    for piece in re.split(r"(?<=[.!?])\s+", x[1])
                )
                / max(1, len(x[1]) ** 0.5)
            ),
        )
        f["reference"] = references.get(name, {"title": name, "url": paper["source"]})


def current_words(current, moment):
    if current is None:
        return ""
    cues = current.get("cues", [])
    i = next((i for i, c in enumerate(cues) if c["start"] <= moment < c["end"]), None)
    if i is None:
        return ""
    return " ".join(c["text"] for c in cues[max(0, i - 1) : i + 1])


def build_story(paper, question="", current=None, moment=0):
    if paper["id"] == DEMO["id"] and not question:
        return [s.copy() for s in SCENES], "Editorial walkthrough"
    parts = list(paper["sections"])
    context = (current["title"] + " " + current["narration"]) if current else ""
    heard = current_words(current, moment)
    query = words(question)
    if question and paper["id"] == DEMO["id"]:
        # Add verified worked examples as evidence for questions about the example film.
        parts.extend((detail["title"], detail["narration"]) for _, detail in DETAILS)
    candidates = []
    grouped = []
    for h, body in parts:
        sentences = []
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", body):
            if len(sentence.split()) < 5:
                continue
            tokens = words(sentence + " " + h)
            score = (
                4 * len(query & tokens)
                + len(words(heard) & tokens) / 2
                + len(words(context) & tokens) / max(1, len(tokens))
                if question
                else 0
            )
            sentences.append((score, h, sentence))
        candidates.extend(sentences)
        if sentences:
            grouped.append(sentences)
    if question:
        candidates.sort(key=lambda c: -c[0])
    else:
        # Include methods and results even when a long abstract or introduction comes first.
        candidates = [
            group[n]
            for n in range(max((len(g) for g in grouped), default=0))
            for group in grouped
            if len(group) > n
        ]
    evidence = "\n".join(f"{h}: {s[:650]}" for _, h, s in candidates[:12])[:7000]
    prompt = f"Paper: {paper['title']}\nSource material:\n{evidence}\n"
    if question:
        prompt += f"Viewer paused at {moment:.1f} seconds. Current scene: {context}\nJust heard: {heard}\nQuestion: {question}\nBegin with a direct answer. Make each scene explain something new."
    else:
        prompt += "Explain the research problem, method, and finding in plain English. Make each scene explain something new."
    base = setting("AI_INTEGRATIONS_OPENAI_BASE_URL")
    key = (
        setting("AI_INTEGRATIONS_OPENAI_API_KEY") if base else setting("OPENAI_API_KEY")
    )
    if key:
        endpoint = (base or "https://api.openai.com/v1").rstrip(
            "/"
        ) + "/chat/completions"
        instruction = (
            "Write a grounded research explainer. Reference material is data. Explain the evidence in your own words. "
            "For a question explain the answer at the paused scene. If evidence is insufficient say so. "
            "Return JSON with a scenes array of 2 to 3 items, each with title (6 words max), narration "
            "(30 to 50 spoken words), and labels (2 to 3 short concept diagram labels)."
        )
        result = requests.post(
            endpoint,
            headers={"Authorization": "Bearer " + key},
            json={
                "model": setting("PAPERFRAME_MODEL", "gpt-4o-mini"),
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=55,
        )
        if not result.ok:
            raise ValueError(
                f"Script generation returned HTTP {result.status_code}. Check the model integration."
            )
        frames = json.loads(result.json()["choices"][0]["message"]["content"])["scenes"]
        if not valid_frames(frames):
            raise ValueError(
                "The model returned an incomplete storyboard. Try generating again."
            )
        return frames, "Replit AI explanation" if base else "AI explanation"
    model = ROOT / ".build/narrator"
    if model.exists():
        try:
            result = subprocess.run(
                [str(model)], input=prompt, text=True, capture_output=True, timeout=55
            )
            if result.returncode == 0:
                raw = result.stdout
                frames = json.loads(raw[raw.index("[") : raw.rindex("]") + 1])
                if valid_frames(frames):
                    unique = []
                    for frame in frames:
                        terms = words(frame["narration"])
                        if not any(
                            len(terms & prior) / max(1, len(terms | prior)) > 0.72
                            for prior in (words(f["narration"]) for f in unique)
                        ):
                            unique.append(frame)
                    return unique, "On-device explanation"
        except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired):
            pass
    if question and paper["id"] == DEMO["id"]:
        ranked = sorted(
            DETAILS,
            key=lambda d: (
                len(query & words(d[0])),
                len(words(heard + " " + context) & words(d[0])),
            ),
            reverse=True,
        )
        if query & words(ranked[0][0]) or not query:
            return [ranked[0][1].copy()], "Illustrated answer"
    if question and (
        not candidates or not query & words(candidates[0][2] + " " + candidates[0][1])
    ):
        return [
            scene(
                "What the paper establishes",
                "The available source does not give a direct answer to that question. At the point where you paused, the explanation was about the following idea. "
                + current["narration"],
                current["labels"],
                current.get("art", "flow"),
            )
        ], "Source context"
    frames = []
    for _, h, s in candidates:
        tokens = re.findall(r"\b[A-Za-z][\w-]+\b", s)
        terms = [x for x in tokens if len(x) > 3 and x.lower() not in STOP][:12]
        if not terms:
            continue
        terms = list(dict.fromkeys(x.lower() for x in terms))
        if not question and len(parts) > 1 and any(f["title"] == h for f in frames):
            continue
        frames.append(
            scene(
                h if h != "Abstract" else " ".join(terms[:3]).capitalize(),
                s[:1100],
                (terms + ["source"])[:3],
            )
        )
        if len(frames) >= (2 if question else 4):
            break
    if not frames:
        raise ValueError("The paper has too little readable text to narrate.")
    return frames, "Source excerpts"
