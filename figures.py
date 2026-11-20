"""Diagrams for the sample overview. Each stage corresponds to a spoken beat."""

import math

INK = "#191d48"
GOLD = "#ffd989"
LAV = "#c0bcff"


def referent(draw, font, stage, progress):
    full = stage is None
    alternative = stage == 2
    focus = 2 if alternative else 0
    labels = ["animal", "crossed", "street", "it", "wide" if alternative else "tired"]
    xs = [153, 396, 635, 876, 1122]
    draw.text(
        (64, 231),
        f"“… because it was {labels[-1]}.”",
        font=font(31, serif=True),
        fill="white",
    )
    for i, x in enumerate(xs):
        if i == 3:
            continue
        height = [145, 103, 80, 0, 98][i]
        points = [
            (x + (876 - x) * t / 100, 465 - height * math.sin(math.pi * t / 100))
            for t in range(101)
        ]
        if stage == 0:
            continue
        lit = i == focus
        if lit:
            points = points[: max(2, round(progress * 100) + 1)]
        draw.line(points, fill=GOLD if lit else "#66668f", width=6 if lit else 2)
    for i, (x, label) in enumerate(zip(xs, labels)):
        bright = i == 3
        draw.rounded_rectangle(
            (x - 94, 474, x + 94, 549),
            radius=13,
            fill=GOLD if bright else "#35375e",
            outline=GOLD if i in (focus, 3) and stage != 0 else "#767698",
            width=2,
        )
        draw.text(
            (x, 512), label, font=font(31), fill=INK if bright else "white", anchor="mm"
        )
    draw.text(
        (64, 579),
        "Illustrative connections"
        if full or stage != 0
        else "Which word does “it” refer to?",
        font=font(22),
        fill=LAV,
    )


def attention_mix(d, font, stage, progress):
    shown = 2 if stage is None else stage
    d.text((92, 275), "Query", font=font(24, True), fill=LAV)
    d.rounded_rectangle((77, 348, 290, 438), radius=13, fill=GOLD)
    d.text((184, 392), "it", font=font(42, serif=True), fill=INK, anchor="mm")
    d.text((461, 275), "Keys", font=font(24, True), fill=LAV)
    for i, (name, y) in enumerate([("animal", 352), ("street", 455)]):
        d.line(
            [(292, 390), (457, y + 13)],
            fill=GOLD if i == 0 else LAV,
            width=4 if i == 0 else 2,
        )
        d.rounded_rectangle(
            (459, y - 16, 660, y + 46), radius=10, fill="#36385e", outline=LAV, width=2
        )
        d.text((560, y + 15), name, font=font(28), fill="white", anchor="mm")
    d.text((755, 275), "Relative weight", font=font(24, True), fill=LAV)
    for i, (width, y) in enumerate([(232, 352), (77, 455)]):
        d.rounded_rectangle((756, y, 1020, y + 32), radius=7, fill="#33365d")
        if shown > 0:
            w = width * (progress if stage == 1 else 1)
            d.rounded_rectangle(
                (756, y, 756 + max(w, 3), y + 32),
                radius=6,
                fill=GOLD if i == 0 else LAV,
            )
    if shown >= 2:
        d.line((1072, 366, 1072, 472), fill=LAV, width=3)
        d.text((1112, 419), "mix", font=font(30, serif=True), fill="white", anchor="mm")
    d.text(
        (78, 568),
        "Illustrative weights for two candidate words",
        font=font(22),
        fill=LAV,
    )


def translation(d, font, stage, progress):
    shown = 2 if stage is None else stage
    for row, name in enumerate(["Recurrent encoder", "Transformer encoder"]):
        y = 291 + row * 148
        d.text((70, y), name, font=font(25, True), fill=LAV)
        for i in range(5):
            x = 73 + i * 103
            lit = row == 0 or shown >= 1
            d.rounded_rectangle(
                (x, y + 49, x + 59, y + 96),
                radius=8,
                fill="#bcb9ef" if lit else "#37385e",
            )
            d.text(
                (x + 30, y + 72),
                str(i + 1),
                font=font(21, True),
                fill=INK if lit else LAV,
                anchor="mm",
            )
            if row == 0 and i < 4:
                d.line((x + 60, y + 73, x + 96, y + 73), fill=LAV, width=2)
                d.polygon(
                    [(x + 90, y + 67), (x + 98, y + 73), (x + 90, y + 79)], fill=LAV
                )
            elif row == 1 and lit:
                d.line((x + 30, y + 33, x + 30, y + 46), fill=GOLD, width=3)
    d.line((648, 277, 648, 546), fill="#75739c", width=2)
    d.text((714, 297), "English → German", font=font(29), fill=LAV)
    if shown >= 2:
        d.text((705, 350), "28.4", font=font(94, serif=True), fill=GOLD)
        d.text((717, 482), "BLEU · WMT 2014", font=font(25), fill="white")
    else:
        d.text(
            (715, 399), "Translation quality", font=font(29, serif=True), fill="white"
        )
