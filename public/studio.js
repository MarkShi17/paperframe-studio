const el = (id) => document.getElementById(id);
const video = el("video");
const fmt = (value) => {
  const t = Math.max(0, Math.floor(value || 0));
  return Math.floor(t / 60) + ":" + String(t % 60).padStart(2, "0");
};
let active,
  stack = [],
  history = [],
  sceneIndex = -1,
  busy = false;
const saved = new Map();
const idPattern = /^(demo(?:-deep)?|[a-f0-9]{32})$/;
function readStored(name, fallback) {
  try {
    return JSON.parse(localStorage.getItem("paperframe-" + name)) ?? fallback;
  } catch {
    return fallback;
  }
}
function writeStored(name, value) {
  try {
    localStorage.setItem("paperframe-" + name, JSON.stringify(value));
  } catch {}
}
async function fetchFilm(id) {
  if (!idPattern.test(id)) throw Error("Invalid video link.");
  if (saved.has(id)) return saved.get(id);
  const response = await fetch("/media/" + id + "/story.json");
  if (!response.ok)
    throw Error("This video is no longer available on this server.");
  const item = await response.json();
  saved.set(id, item);
  return item;
}
function recent(item) {
  const items = readStored("papers", []);
  if (!item.film.question)
    writeStored(
      "papers",
      [
        { id: item.film.id, title: item.paper.title },
        ...items.filter((row) => row.id !== item.film.id),
      ].slice(0, 8),
    );
}
function drawRecent() {
  const items = readStored("papers", []).filter((row) =>
    idPattern.test(row.id),
  );
  const list = el("recent");
  list.replaceChildren();
  if (!items.length) return;
  const h = document.createElement("h4");
  h.textContent = "Recently watched";
  list.append(
    h,
    ...items.slice(0, 4).map((row) =>
      button(row.title, async () => {
        if (busy) return;
        try {
          await openFilm(row.id);
          el("dialog").close();
        } catch (e) {
          el("importStatus").textContent = e.message;
        }
      }),
    ),
  );
}
function sourceLink(ref) {
  const a = document.createElement("a");
  a.textContent = ref.title + " ↗";
  a.href = ref.url;
  a.rel = "noopener";
  a.target = "_blank";
  return a;
}
function drawSources(scene) {
  const { paper } = active;
  const panel = el("sources");
  const heading = document.createElement("h4");
  heading.textContent = "Related section";
  panel.replaceChildren(
    heading,
    sourceLink(scene.reference || { title: paper.title, url: paper.source }),
  );
  if (scene.evidence) {
    const excerpt = document.createElement("blockquote");
    excerpt.textContent = scene.evidence;
    panel.append(excerpt);
  }
  for (const ref of (scene.citations || []).slice(1)) {
    const text = document.createElement("blockquote");
    text.textContent = ref.excerpt;
    panel.append(sourceLink(ref), text);
  }
  if (scene.tex || scene.formula) {
    const expression = document.createElement("pre");
    expression.textContent = scene.tex || scene.formula;
    panel.append(expression);
  }
  for (const f of paper.figures || []) {
    const details = document.createElement("details");
    const title = document.createElement("summary");
    const caption = document.createElement("p");
    title.textContent = f.caption.split(/(?<=\.)\s/)[0].slice(0, 110);
    caption.textContent = f.caption;
    const img = document.createElement("img");
    img.loading = "lazy";
    img.alt = f.caption;
    img.src = f.image;
    details.append(
      title,
      img,
      caption,
      sourceLink({ title: "Figure in paper", url: f.url }),
    );
    panel.append(details);
  }
}

function button(text, fn) {
  const node = document.createElement("button");
  node.textContent = text;
  node.type = "button";
  node.onclick = fn;
  return node;
}
function jump(t) {
  video.currentTime = t;
  video.play().catch(() => {});
}
function sync() {
  if (!active) return;
  const t = video.currentTime || 0;
  el("stamp").textContent = fmt(t);
  const scenes = active.film.scenes;
  const index = Math.max(
    0,
    scenes.findLastIndex((s) => s.start <= t),
  );
  const scene = scenes[index];
  const cue = (scene.cues || []).find((c) => c.start <= t && t < c.end);
  const sentences = scene.narration.match(/[^.!?]+(?:[.!?]+(?=\s|$)|$)/g) || [
    scene.narration,
  ];
  const phrase = cue?.text.split(" ").slice(0, 3).join(" ");
  const excerpt = (
    (phrase && sentences.find((sentence) => sentence.includes(phrase))) ||
    cue?.text ||
    sentences[0]
  ).trim();
  if (el("quote").textContent !== excerpt) el("quote").textContent = excerpt;
  if (sceneIndex === index) return;
  drawSources(scene);
  sceneIndex = index;
  el("sceneTitle").textContent = scenes[index].title;
  [...el("chapters").children].forEach((b, i) =>
    b.setAttribute("aria-current", i === index),
  );
  let ideas = [
    "Can you give a concrete example?",
    "How does this support the paper’s conclusion?",
  ];
  if (active.film.id === "demo")
    ideas = [
      ["Why does “it” attend to “animal”?", "What do the lines represent?"],
      [
        "Can you show softmax with numbers?",
        "How are keys different from values?",
      ],
      ["Why use several attention heads?", "How do the heads combine?"],
      ["What does 28.4 BLEU measure?", "Why is training faster?"],
    ][index];
  el("ideas").replaceChildren(
    ...ideas.map((q) =>
      button(q, () => {
        if (busy) return;
        el("question").value = q;
        el("question").focus();
      }),
    ),
  );
}
async function voiceStatus() {
  try {
    const r = await fetch("/api/voice", { cache: "no-store" });
    const { elevenlabs } = await r.json();
    el("revoice").hidden =
      !elevenlabs ||
      !active ||
      active.film.voice === "ElevenLabs" ||
      Boolean(active.film.question);
    el("voiceSetup").textContent = elevenlabs
      ? "Narrated by ElevenLabs."
      : "Using the device voice. ElevenLabs narration activates with ELEVENLABS_API_KEY.";
  } catch {}
}
el("revoice").onclick = async () => {
  if (busy || !active) return;
  video.pause();
  const chapter = Math.max(0, sceneIndex);
  pending(true);
  try {
    const item = await generate({ revoice: active.film.id }, el("trackStatus"));
    show(item, item.film.scenes[chapter].start);
    el("trackStatus").textContent = "ElevenLabs narration is ready.";
  } catch (e) {
    el("trackStatus").textContent = e.message;
  } finally {
    pending(false);
  }
};
function show(item, time = 0, play = false) {
  video.pause();
  active = item;
  voiceStatus();
  saved.set(item.film.id, item);
  recent(item);
  const link = new URL(location.href);
  link.search = "";
  if (item.film.id !== "demo") link.searchParams.set("film", item.film.id);
  window.history.replaceState(null, "", link);
  sceneIndex = -1;
  const { paper, film } = item;
  el("title").textContent = paper.title;
  el("source").textContent = "arXiv " + paper.id + " ↗";
  el("source").href = paper.source;
  el("byline").textContent = [paper.authors, paper.date]
    .filter(Boolean)
    .join("   ·   ");
  const mode = film.mode || "overview";
  const isAnswer = Boolean(film.question);
  el("overviewBtn").setAttribute(
    "aria-pressed",
    !isAnswer && mode === "overview",
  );
  el("deepBtn").setAttribute("aria-pressed", !isAnswer && mode === "deep");
  if (!isAnswer) writeStored("track-" + paper.id + "-" + mode, film.id);
  el("filmTitle").textContent =
    film.question ||
    (mode === "deep" ? "Technical deep dive" : "High-level overview");
  el("trackStatus").textContent =
    paper.scope === "Abstract walkthrough"
      ? "Based on the abstract. Full text was unavailable."
      : "";
  el("voice").textContent =
    fmt(film.duration) + " · " + film.voice + " narration";
  el("back").hidden = !stack.length;
  el("chapters").replaceChildren(
    ...film.scenes.map((s) => {
      const b = button("", () => jump(s.start));
      b.className = "chapter";
      const img = document.createElement("img");
      img.src = s.image;
      img.alt = "";
      const stamp = document.createElement("small");
      stamp.textContent = fmt(s.start);
      b.append(img, stamp, s.title);
      return b;
    }),
  );
  el("transcript").replaceChildren(
    ...film.scenes.map((s) => {
      const p = document.createElement("p");
      p.append(
        button(fmt(s.start), () => jump(s.start)),
        s.narration,
      );
      return p;
    }),
  );
  video.onloadedmetadata = () => {
    if (time > 0) video.currentTime = time;
    sync();
    if (play) video.play().catch(() => {});
  };
  video.poster = film.scenes[0].image;
  video.src = film.url;
  video.replaceChildren();
  if (film.captions) {
    const track = document.createElement("track");
    Object.assign(track, {
      kind: "captions",
      label: "English",
      srclang: "en",
      src: film.captions,
    });
    video.append(track);
  }
  video.load();
  sync();
}
function tab(selected) {
  for (const [name, id] of [
    ["chapters", "chapterTab"],
    ["transcript", "scriptTab"],
    ["sources", "sourceTab"],
  ]) {
    el(name).hidden = name !== selected;
    el(id).setAttribute("aria-pressed", name === selected);
  }
}
el("chapterTab").onclick = () => tab("chapters");
el("scriptTab").onclick = () => tab("transcript");
el("sourceTab").onclick = () => tab("sources");
video.ontimeupdate = sync;
el("question").onfocus = () => video.pause();
el("importBtn").onclick = () => {
  video.pause();
  voiceStatus();
  drawRecent();
  el("dialog").showModal();
};
el("close").onclick = () => el("dialog").close();
el("back").onclick = () => {
  if (busy) return;
  const previous = stack.pop();
  show(previous.item, previous.time);
  el("status").textContent = "";
};
function drawHistory() {
  el("history").hidden = !history.length;
  el("answers").replaceChildren(
    ...history.map((entry) =>
      button(fmt(entry.time) + " · " + entry.item.film.question, () => {
        if (busy) return;
        stack = [...entry.path];
        show(entry.item, 0, true);
      }),
    ),
  );
}
async function generate(payload, status) {
  const response = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const job = await response.json();
  if (!response.ok) throw Error(job.label || "Generation could not start.");
  for (;;) {
    const r = await fetch("/api/job/" + job.job, { cache: "no-store" });
    if (!r.ok) throw Error("The server lost this render. Please try again.");
    const result = await r.json();
    if (result.state === "error") throw Error(result.label);
    if (result.state === "done") return result.item;
    status.textContent = result.label + "…";
    await new Promise((resolve) => setTimeout(resolve, 800));
  }
}
function pending(value) {
  busy = value;
  for (const node of document.querySelectorAll(
    "#ask button,#paperForm button,#importBtn,#back,#overviewBtn,#deepBtn,#revoice",
  ))
    node.disabled = value;
}
el("dialog").oncancel = (e) => {
  if (busy) e.preventDefault();
};
el("ask").onsubmit = async (e) => {
  e.preventDefault();
  const question = el("question").value.trim();
  if (busy || !active || !question) return;
  video.pause();
  const parent = { item: active, time: video.currentTime };
  pending(true);
  el("status").textContent = "Starting answer video…";
  try {
    const item = await generate(
      { question, parent: parent.item.film.id, time: parent.time },
      el("status"),
    );
    stack.push(parent);
    history.unshift({ item, time: parent.time, path: [...stack] });
    const root = stack[0].item.film.id;
    writeStored(
      "history-" + root,
      history.slice(0, 20).map((row) => row.item.film.id),
    );
    drawHistory();
    show(item, 0, true);
    el("question").value = "";
    el("status").textContent = "Answer video ready · " + item.film.method;
  } catch (err) {
    el("status").textContent = err.message;
  } finally {
    pending(false);
  }
};
async function switchTrack(mode) {
  if (
    busy ||
    !active ||
    (!active.film.question && (active.film.mode || "overview") === mode)
  )
    return;
  video.pause();
  const id = readStored("track-" + active.paper.id + "-" + mode, null);
  pending(true);
  try {
    let item;
    if (id) {
      try {
        item = await fetchFilm(id);
      } catch {}
    }
    if (!item)
      item = await generate(
        { paper: active.paper.id, sourceFilm: active.film.id, mode },
        el("trackStatus"),
      );
    await openFilm(item.film.id);
    el("status").textContent = "";
    tab("chapters");
  } catch (e) {
    el("trackStatus").textContent = e.message;
  } finally {
    pending(false);
  }
}
el("deepBtn").onclick = () => switchTrack("deep");
el("overviewBtn").onclick = () => switchTrack("overview");
el("paperForm").onsubmit = async (e) => {
  e.preventDefault();
  if (busy) return;
  pending(true);
  el("importStatus").textContent = "Reading paper…";
  try {
    const item = await generate(
      { paper: el("paper").value, mode: el("depth").value },
      el("importStatus"),
    );
    stack = [];
    history = [];
    drawHistory();
    tab("chapters");
    show(item);
    el("dialog").close();
    el("paper").value =
      el("question").value =
      el("status").textContent =
      el("importStatus").textContent =
        "";
  } catch (err) {
    el("importStatus").textContent = err.message;
  } finally {
    pending(false);
  }
};
async function ancestors(item) {
  const chain = [];
  const seen = new Set([item.film.id]);
  let node = item;
  while (node.film.parent && chain.length < 20) {
    const p = node.film.parent;
    if (seen.has(p.id)) break;
    seen.add(p.id);
    node = await fetchFilm(p.id);
    chain.unshift({ item: node, time: p.time });
  }
  return chain;
}
async function openFilm(id) {
  const item = await fetchFilm(id);
  const route = await ancestors(item);
  const root = route[0]?.item.film.id || item.film.id;
  const branchIds = readStored("history-" + root, []).slice(0, 20);
  const loaded = await Promise.allSettled(
    branchIds.map(async (id) => {
      const answer = await fetchFilm(id);
      return {
        item: answer,
        time: answer.film.parent.time,
        path: await ancestors(answer),
      };
    }),
  );
  stack = route;
  history = loaded.filter((r) => r.status === "fulfilled").map((r) => r.value);
  drawHistory();
  show(item);
}
openFilm(new URLSearchParams(location.search).get("film") || "demo").catch(
  async (e) => {
    el("status").textContent = e.message;
    await openFilm("demo");
  },
);
