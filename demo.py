def scene(title, narration, labels, art="flow"):
    return dict(title=title, narration=narration, labels=labels, art=art)


SCENES = [
    scene(
        "How attention works",
        "The animal crossed the street because it was tired. What does it refer to? You probably chose the animal. But change tired to wide, and the street becomes a better answer. The word it stayed the same. Its meaning changed with the words around it. This is the problem at the heart of the Transformer: how can a machine build a representation of a word that reflects its context?",
        ["animal", "crossed", "street", "it", "tired"],
        "attention",
    ),
    scene(
        "Queries, keys & values",
        "Imagine reading the sentence from the position of it. The model makes a query for that position and a key for every position in the sentence. Comparing the query with each key gives a score. A bigger score means a stronger connection. The model then blends information, called values, using those connections as weights. The highlighted line illustrates one possible connection. It is an example, not a measurement from the paper.",
        ["Score connections", "Weight the words", "Blend information"],
    ),
    scene(
        "Many heads, one layer",
        "One set of connections gives you one view of the sentence. A Transformer builds several views at once. Each attention head has different learned settings, so different heads can emphasize different relationships. The model combines their outputs into a new representation for each word. It also adds information about position. Otherwise, attention would have no way to tell whether animal came before street or after it.",
        ["Parallel heads", "Concatenate", "Project"],
        "heads",
    ),
    scene(
        "What changed",
        "Why did this matter for translation? A recurrent encoder passes information from one position to the next. Attention lets distant words interact within a single layer, and an encoder can update all positions together. In the paper's English-to-German experiment, the Transformer reached 28.4 BLEU, a translation quality score. There are trade-offs. Standard attention compares every pair of positions, and the decoder still generates the translation one word at a time. The advance was changing how context is computed.",
        ["Parallel encoding", "Translation test", "28.4 BLEU"],
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


def math_scene(title, narration, formula, steps, reference, anchor):
    return {
        **scene(title, narration, steps, "math"),
        "formula": formula,
        "reference": {
            "title": reference,
            "url": "https://arxiv.org/html/1706.03762#" + anchor,
        },
    }


DEEP = [
    math_scene(
        "Start with the shapes",
        "Take an encoder sequence of n tokens. Put one token representation in each row of X. In the base model each row has five hundred and twelve coordinates. One head multiplies X by three different learned matrices to make queries, keys, and values. Its query and key vectors have sixty-four coordinates. These are learned changes of representation. They are not discrete labels saying what a token means.",
        "Q = XWQ      K = XWK      V = XWV",
        ["X: n × 512", "Q and K: n × 64", "V: n × 64"],
        "3.2.2 Multi-Head Attention",
        "S3.SS2.SSS2",
    ),
    math_scene(
        "Score every pair",
        "Multiply Q by the transpose of K. The result has n rows and n columns. Entry i j is the dot product of query i with key j. Divide each score by the square root of the key dimension. Here is the paper's motivation. If corresponding query and key coordinates are independent with zero mean and unit variance, the dot product has variance equal to the key dimension. Scaling keeps large scores from pushing softmax into regions with very small gradients.",
        "S = QKᵀ / √dₖ",
        ["One row per query", "One column per key", "64 dimensions → divide by 8"],
        "3.2.1 Scaled Dot-Product Attention",
        "S3.SS2.SSS1",
    ),
    math_scene(
        "Work one row by hand",
        "Take a toy row with two scores after scaling: zero and the natural log of three. Exponentiating gives one and three. Divide each by their sum of four. The attention weights are one quarter and three quarters. Suppose the first value vector is four, zero, and the second is zero, eight. The weighted sum is one, six. The second position contributes more, but the first still contributes. These are numbers chosen to illustrate Equation One.",
        "¼ (4, 0) + ¾ (0, 8) = (1, 6)",
        ["Scores: 0 and ln 3", "Weights: ¼ and ¾", "Output: (1, 6)"],
        "3.2.1 Scaled Dot-Product Attention, Eq. 1",
        "S3.SS2.SSS1",
    ),
    math_scene(
        "Combine the heads",
        "Softmax is applied separately to each row before multiplying the weight matrix by V. Repeat that operation with eight independent sets of projections in the base model. Each head produces sixty-four values per token. Concatenating eight outputs restores five hundred and twelve coordinates. A learned output projection mixes information across heads. The heads can specialize, but the architecture does not assign one head to grammar and another to meaning.",
        "MultiHead = Concat(head₁, …, head₈) Wᴼ",
        ["8 projections", "8 × 64 = 512", "Learned output mix"],
        "3.2.2 Multi-Head Attention",
        "S3.SS2.SSS2",
    ),
    math_scene(
        "Mask the decoder",
        "During training the decoder sees a shifted sequence of target tokens. To predict the next token without looking ahead, it sets scores for forbidden future positions to negative infinity before softmax. Their exponentials become zero. The remaining weights normalize over the allowed prefix. This permits parallel computation of training losses at many positions. At inference the next input token still depends on the previous prediction, so generation proceeds sequentially.",
        "j > i   ⇒   Sᵢⱼ = −∞   ⇒   Aᵢⱼ = 0",
        ["Shift targets", "Mask future scores", "Normalize allowed prefix"],
        "3.2.3 Applications of Attention in our Model",
        "S3.SS2.SSS3",
    ),
    math_scene(
        "Read the scaling claim",
        "There is a cost to giving each word direct access to every other word. With sequence length n and representation dimension d, the paper's comparison gives order n squared d operations for self-attention versus order n d squared for a recurrent layer. These are layer-level comparisons under the paper's assumptions. They do not imply that attention always trains faster. Sequence length, model dimension, and hardware all matter. The shorter path between positions and the quadratic score matrix are two sides of the same design.",
        "Self-attention: O(n²d)     Recurrent: O(nd²)",
        ["n = sequence length", "d = feature dimension", "Compare at the same n and d"],
        "4 Why Self-Attention, Table 1",
        "S4",
    ),
]
