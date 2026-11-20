"""Build the technical track from the paper's equations and cited passages."""

import re

from bs4 import NavigableString
from demo import DEEP, DEMO, scene


def text_without_math_markup(node):
    # LaTeXML stores both presentation text and a duplicate TeX annotation.
    return " ".join(
        " ".join(
            str(node_text).strip()
            for node_text in node.descendants
            if isinstance(node_text, NavigableString)
            and not node_text.find_parent("annotation")
        ).split()
    )


def extract_equations(doc, url):
    equations = []
    for block in doc.select("tbody[id], table.ltx_equation[id], div.ltx_equation[id]"):
        anchor = block.get("id", "")
        if not re.search(r"(?:^|\.)E\d+[a-z]?$", anchor):
            continue
        rows = block.select("math[alttext]")
        if not rows:
            continue
        tex = " ".join(m["alttext"].replace("\\displaystyle", "").strip() for m in rows)
        if not 3 < len(tex) < 700:
            continue
        container = block.find_parent(class_="ltx_para") or block
        before = container.find_previous("p", class_="ltx_p")
        after = container.find_next("p", class_="ltx_p")
        passage = " ".join(
            text_without_math_markup(p)[:700] for p in (before, after) if p
        )
        section = block.find_parent("section")
        heading = section.find(["h2", "h3", "h4"]) if section else None
        n = re.search(r"E(\d+[a-z]?)$", anchor).group(1)
        if passage:
            equations.append(
                dict(
                    title=f"Equation {n}",
                    tex=tex,
                    url=url + "#" + anchor,
                    section=heading.get_text(" ", strip=True) if heading else "Method",
                    passage=passage,
                )
            )
        if len(equations) >= 12:
            break
    return equations


def readable_sentences(text):
    result = []
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text):
        s = " ".join(s.split())
        if (
            6 <= len(s.split()) <= 90
            and "\\displaystyle" not in s
            and not s.startswith("[")
        ):
            result.append(s)
    return result


def technical_story(paper):
    if paper["id"] == DEMO["id"]:
        return [dict(f) for f in DEEP], "Worked derivation"
    sections = paper["sections"][1:]
    if not sections:
        raise ValueError(
            "Only the abstract is readable. A technical walkthrough needs methods or results from the full paper."
        )
    frames = []
    # Use source passages as the technical narration. Preserve the exact formula and citation.
    for equation in paper.get("equations", []):
        lines = readable_sentences(equation["passage"])
        if not lines:
            continue
        excerpt = " ".join(lines[:2])
        if any(f.get("evidence") == excerpt for f in frames):
            continue
        reference = {
            "title": equation["title"] + " · " + equation["section"],
            "url": equation["url"],
        }
        f = scene(
            equation["title"],
            "In the discussion around "
            + equation["title"].lower()
            + ", the authors write: "
            + excerpt,
            [equation["title"], equation["section"]],
        )
        f.update(tex=equation["tex"], reference=reference, evidence=excerpt)
        frames.append(f)
        if len(frames) >= 4:
            break
    for name, text in sections:
        if re.search(r"related work|introduction|appendix|references", name, re.I):
            continue
        lines = readable_sentences(text)
        if not lines:
            continue
        ranked = sorted(
            enumerate(lines),
            key=lambda item: (
                -len(
                    re.findall(
                        r"\b(?:because|measure|train|loss|compared|assume|outperform|parameter|limitation|estimate|significant|experiment|observe)\w*",
                        item[1],
                        re.I,
                    )
                )
            ),
        )
        chosen = sorted(ranked[:3])
        excerpt = " ".join(sentence for _, sentence in chosen)
        if not excerpt or any(f.get("evidence") == excerpt for f in frames):
            continue
        label = re.sub(r"^[\d.]+\s+", "", name)
        f = scene(label, excerpt, [label, "Evidence in the paper"])
        f.update(
            reference=paper["references"].get(
                name, {"title": name, "url": paper["source"]}
            ),
            evidence=excerpt,
        )
        frames.append(f)
        if len(frames) >= 8:
            break
    if not frames:
        raise ValueError(
            "The readable sections contain too little technical evidence for a deep dive."
        )
    return frames, "Cited technical reading"
