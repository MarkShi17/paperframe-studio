def scene(title, narration, labels, art="flow"):
    return dict(title=title, narration=narration, labels=labels, art=art)


SCENES = [
    scene(
        "How attention works",
        "Read the sentence: the animal crossed the street because it was tired. To interpret it, you connect that word back to animal. Self-attention gives a model a way to learn connections like this. Each token gathers information from other tokens, with different weights for different relationships.",
        ["animal", "crossed", "street", "it", "tired"],
        "attention",
    ),
    scene(
        "Queries, keys & values",
        "Each token produces a query, a key, and a value. The query is compared with the keys to score possible connections. Softmax turns those scores into weights that add up to one. A weighted sum of the values gives the token its new representation.",
        ["Compare queries & keys", "Normalize scores", "Mix values"],
    ),
    scene(
        "Many heads, one layer",
        "A single set of weights gives one view of a sentence. The Transformer runs several attention heads in parallel, each with its own learned projections. It concatenates their outputs and mixes them with a learned matrix, so one token can incorporate several kinds of information.",
        ["Parallel heads", "Concatenate", "Project"],
        "heads",
    ),
    scene(
        "What changed",
        "Earlier recurrent translation models processed a sentence one position at a time. The Transformer encoder computes representations for all positions in a layer together. In the paper's English-to-German translation experiment, the model reached 28.4 BLEU. The decoder still generates translated words one at a time.",
        ["Parallel encoding", "Translation", "28.4 BLEU"],
    ),
]
DETAILS = [
    (
        "example pronoun animal it reference simple analogy",
        scene(
            "Which word does “it” refer to?",
            "At the word it, imagine comparing animal and street. The phrase was tired makes animal a plausible referent. A head could place more weight on animal, mixing more of its value into the representation of it. The drawing illustrates the idea. It does not show measured model weights.",
            ["animal", "crossed", "street", "it", "tired"],
            "attention",
        ),
    ),
    (
        "queries keys values query key value softmax weight scaled square root math scores",
        scene(
            "From scores to a mixture",
            "Suppose a query gives two keys scores of zero and one after scaling. Softmax turns them into weights of roughly twenty-seven and seventy-three percent. The output is that weighted mixture of the two value vectors. Keys determine relevance, while values supply the information carried forward.",
            ["Scores 0 and 1", "27% and 73%", "Weighted sum"],
        ),
    ),
    (
        "position order positional encoding order sequence",
        scene(
            "Where word order enters",
            "Self-attention alone has no signal telling it which token came first. The authors add a position-dependent vector to each input embedding. The resulting queries and keys can reflect both the token and its position, helping distinguish sentences that contain the same words in a different order.",
            ["Word embedding", "Add position", "Attention input"],
        ),
    ),
    ("heads different multihead multiple parallel relationships", SCENES[2]),
    ("speed recurrent parallel training sequential faster results bleu", SCENES[3]),
    (
        "mask future decoder causality cheating generation",
        scene(
            "Hide future words",
            "During training, the decoder receives a shifted target sentence. A mask blocks attention to later positions before softmax. The model can train on multiple positions together while each prediction only uses the words that would already be available at that point in generation.",
            ["Target sequence", "Mask future keys", "Predict next word"],
        ),
    ),
]
DEMO = dict(
    id="1706.03762",
    title="Attention Is All You Need",
    authors="Ashish Vaswani et al.",
    date="June 2017",
    source="https://arxiv.org/abs/1706.03762",
    sections=[(s["title"], s["narration"]) for s in SCENES],
    scope="Paper walkthrough",
)

REFERENCES = [
    ("How attention works", "3.2 Attention", "S3.SS2"),
    ("Queries, keys & values", "3.2.1 Scaled Dot-Product Attention", "S3.SS2.SSS1"),
    ("Many heads, one layer", "3.2.2 Multi-Head Attention", "S3.SS2.SSS2"),
    ("What changed", "6.1 Machine Translation", "S6.SS1"),
]
DEMO["references"] = {
    title: {"title": name, "url": f"https://arxiv.org/html/1706.03762#{anchor}"}
    for title, name, anchor in REFERENCES
}
for frame in SCENES:
    frame["reference"] = DEMO["references"][frame["title"]]

DETAILS.extend(
    [
        (
            "bleu metric score measure evaluation translations",
            scene(
                "Reading a BLEU score",
                "BLEU compares short word sequences in a machine translation with human reference translations and penalizes outputs that are too short. The paper reports 28.4 on English to German. A score of 28.4 is not a percentage of sentences translated correctly.",
                ["Model translation", "Reference overlap", "BLEU score"],
            ),
        ),
        (
            "lines line arcs thickness represent visual diagram connection",
            scene(
                "Reading the arcs",
                "Read the diagram from the highlighted word it. Each line shows a possible connection to a different word. The thicker gold line illustrates a larger attention weight. More of the value associated with animal would flow into the new representation for it.",
                ["animal", "crossed", "street", "it", "tired"],
                "attention",
            ),
        ),
    ]
)
