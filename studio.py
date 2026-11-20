import json
import re
import subprocess
from urllib.parse import urlsplit, urljoin

import requests
from bs4 import BeautifulSoup

from demo import DEMO, DETAILS, SCENES, scene
from scriptwriter import draft, grounded_frames
from pdf_source import pdf_pages
from technical import (
    extract_equations,
    technical_story,
    readable_sentences,
    text_without_math_markup,
)


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
    equations = []
    try:
        html = requests.get(base + "html/" + aid, timeout=12)
        if html.ok:
            doc = BeautifulSoup(html.content, "html.parser")
            equations = extract_equations(doc, html.url)
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
                            " ".join(text_without_math_markup(p) for p in paras)[:9000],
                        )
                    )
    except requests.RequestException:
        pass
    scope = "Paper walkthrough" if len(sections) > 1 else "Abstract walkthrough"
    if len(sections) == 1:
        pdf_url = base + "pdf/" + aid
        try:
            for number, body in pdf_pages(pdf_url):
                name = f"Page {number}"
                sections.append((name, body))
                references[name] = {"title": name, "url": f"{pdf_url}#page={number}"}
                scope = "PDF walkthrough"
        except (requests.RequestException, subprocess.TimeoutExpired, ValueError):
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
        equations=equations,
        scope=scope,
    )


STOP = set(
    "what when which does that those have this from were about mean explain could would make with more into your there their show paper example give simple scene please why how the and are for can".split()
)


def words(s):
    return set(re.findall(r"[a-z0-9]{2,}", s.lower())) - STOP


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


def build_story(paper, question="", current=None, moment=0, mode="overview"):
    if mode == "deep" and not question:
        return technical_story(paper)
    if paper["id"] == DEMO["id"] and not question:
        return [s.copy() for s in SCENES], "Editorial walkthrough"
    parts = list(paper["sections"])
    context = (current["title"] + " " + current["narration"]) if current else ""
    heard = current_words(current, moment)
    query = words(question)
    if question and paper["id"] == DEMO["id"]:
        # Add verified worked examples as evidence for questions about the example film.
        parts.extend((detail["title"], detail["narration"]) for _, detail in DETAILS)
        from demo import DEEP

        parts.extend((f["title"], f["narration"]) for f in DEEP)
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
    # Keep every evidence ID tied to a complete sentence and its source section.
    passages = []
    for _, heading, line in candidates:
        if not question and re.search(r"related work|bibliography", heading, re.I):
            continue
        if len(line) > 800 or (heading, line) in passages:
            continue
        passages.append((heading, line))
        if len(passages) >= 50:
            break
    figure_refs = {}
    for figure in paper.get("figures", []):
        name = figure["caption"].split(":")[0][:50]
        figure_refs[name] = figure
        passages.append((name, figure["caption"]))
    if not passages:
        raise ValueError("The source has too little readable text.")
    request = (
        (
            f"At {moment:.1f}s the viewer saw {context}. Just heard: {heard}. "
            f"Answer this question directly in 1–2 scenes, 50–90 spoken words total: {question}"
        )
        if question
        else (
            "Make a two-minute overview in four scenes, totaling 275–300 spoken words. Open with a concrete "
            "problem, show the central mechanism with a small example, describe the test, and close with "
            "the specific finding and its boundary. Cite a provided figure caption when illustrating that figure. Keep it conversational. Each chapter title should name "
            "the actual idea instead of generic labels such as 'The problem'."
        )
    )
    packet = {
        "paper": paper["title"],
        "assignment": request,
        "passages": [
            {"id": i, "section": heading, "text": txt}
            for i, (heading, txt) in enumerate(passages)
        ],
    }
    try:
        raw, provider = draft(json.dumps(packet, ensure_ascii=False))
        sources = {
            **paper,
            "references": {
                **paper.get("references", {}),
                **{
                    name: {"title": name, "url": f["url"]}
                    for name, f in figure_refs.items()
                },
            },
        }
        frames = grounded_frames(raw, passages, sources)
        for f in frames:
            figure = next(
                (
                    figure_refs[ref["title"]]
                    for ref in f["citations"]
                    if ref["title"] in figure_refs
                ),
                None,
            )
            if figure:
                f["source_figure"] = {
                    "image": figure["image"],
                    "credit": paper["id"]
                    + " · "
                    + figure["caption"].split(":")[0][:50],
                }
        if frames:
            return frames, provider
    except subprocess.TimeoutExpired:
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
                "flow",
            )
        ], "Source context"
    if not question:
        frames = []
        selected = set()
        for name, body in parts:
            if len(parts) > 2 and re.search(
                r"related work|background|introduction", name, re.I
            ):
                continue
            lines = readable_sentences(body)
            if not lines:
                continue
            excerpt = []
            for line in lines:
                if line in selected or len(line.split()) > 65:
                    continue
                excerpt.append(line)
                selected.add(line)
                if sum(len(x.split()) for x in excerpt) >= 60:
                    break
            if not excerpt:
                continue
            ref = paper.get("references", {}).get(
                name, {"title": name, "url": paper["source"]}
            )
            f = scene(name, " ".join(excerpt), [name, "Paper excerpt"])
            f.update(reference=ref, evidence=" ".join(excerpt))
            frames.append(f)
            if len(frames) >= 5:
                break
        if frames:
            return frames, "Cited source reading"
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
