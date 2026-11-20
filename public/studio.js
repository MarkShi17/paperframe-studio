const el = id => document.getElementById(id);
const video = el("video");
const fmt = value => {
  const t = Math.max(0, Math.floor(value || 0));
  return Math.floor(t / 60) + ":" + String(t % 60).padStart(2, "0");
};
let active, stack = [], history = [], sceneIndex = -1, busy = false;
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
  const index = Math.max(0, scenes.findLastIndex(s => s.start <= t));
  if (sceneIndex === index) return;
  sceneIndex = index;
  el("sceneTitle").textContent = scenes[index].title;
  [...el("chapters").children].forEach((b, i) => b.setAttribute("aria-current", i === index));
  let ideas = ["Can you give a concrete example?", "How does this support the paper’s conclusion?"];
  if (active.film.id === "demo") ideas = [
    ["Why does “it” attend to “animal”?", "What do the lines represent?"],
    ["Can you show softmax with numbers?", "How are keys different from values?"],
    ["Why use several attention heads?", "How do the heads combine?"],
    ["What does 28.4 BLEU measure?", "Why is training faster?"]
  ][index];
  el("ideas").replaceChildren(...ideas.map(q => button(q, () => {
    if (busy) return;
    el("question").value = q;
    el("question").focus();
  })));
}
function show(item, time = 0, play = false) {
  video.pause();
  active = item;
  sceneIndex = -1;
  const {paper, film} = item;
  el("title").textContent = paper.title;
  el("source").textContent = "arXiv " + paper.id + " ↗";
  el("source").href = paper.source;
  el("byline").textContent = [paper.authors, paper.date].filter(Boolean).join("   ·   ");
  el("filmTitle").textContent = film.question || paper.scope;
  el("voice").textContent = fmt(film.duration) + " · " + film.voice + " narration";
  el("back").hidden = !stack.length;
  el("chapters").replaceChildren(...film.scenes.map(s => {
    const b = button("", () => jump(s.start));
    b.className = "chapter";
    const img = document.createElement("img");
    img.src = s.image;
    img.alt = "";
    const stamp = document.createElement("small");
    stamp.textContent = fmt(s.start);
    b.append(img, stamp, s.title);
    return b;
  }));
  el("transcript").replaceChildren(...film.scenes.map(s => {
    const p = document.createElement("p");
    p.append(button(fmt(s.start), () => jump(s.start)),s.narration);
    return p;
  }));
  video.onloadedmetadata = () => {
    video.currentTime = time;
    sync();
    if (play) video.play().catch(() => {});
  };
  video.poster = film.scenes[0].image;
  video.src = film.url;
  video.replaceChildren();
  if (film.captions) {
    const track = document.createElement("track");
    Object.assign(track, {kind:"captions",label:"English",srclang:"en",src:film.captions});
    video.append(track);
  }
  video.load();
  sync();
}
function tab(transcript) {
  el("chapters").hidden = transcript;
  el("transcript").hidden = !transcript;
  el("chapterTab").setAttribute("aria-pressed", !transcript);
  el("scriptTab").setAttribute("aria-pressed", transcript);
}
el("chapterTab").onclick = () => tab(false);
el("scriptTab").onclick = () => tab(true);
video.ontimeupdate = sync;
el("question").onfocus = () => video.pause();
el("importBtn").onclick = () => {video.pause(); el("dialog").showModal();};
el("close").onclick = () => el("dialog").close();
el("back").onclick = () => {
  if (busy) return;
  const previous = stack.pop();
  show(previous.item, previous.time);
  el("status").textContent = "";
};
function drawHistory() {
  el("history").hidden = !history.length;
  el("answers").replaceChildren(...history.map(entry => button(fmt(entry.time) + " · " + entry.item.film.question, () => {
    if (busy) return;
    stack = [...entry.path];
    show(entry.item, 0, true);
  })));
}
async function generate(payload, status) {
  const response = await fetch("/api/generate", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  const job = await response.json();
  if (!response.ok) throw Error(job.label || "Generation could not start.");
  for (;;) {
    const r = await fetch("/api/job/" + job.job, {cache:"no-store"});
    if (!r.ok) throw Error("The server lost this render. Please try again.");
    const result = await r.json();
    if (result.state === "error") throw Error(result.label);
    if (result.state === "done") return result.item;
    status.textContent = result.label + "…";
    await new Promise(resolve => setTimeout(resolve, 800));
  }
}
function pending(value) {
  busy = value;
  for (const node of document.querySelectorAll("#ask button,#paperForm button,#importBtn,#back")) node.disabled = value;
}
el("dialog").oncancel = e => { if (busy) e.preventDefault(); };
el("ask").onsubmit = async e => {
  e.preventDefault();
  const question = el("question").value.trim();
  if (busy || !active || !question) return;
  video.pause();
  const parent = {item:active,time:video.currentTime};
  pending(true);
  el("status").textContent = "Starting answer video…";
  try {
    const item = await generate({question,parent:parent.item.film.id,time:parent.time},el("status"));
    stack.push(parent);
    history.unshift({item,time:parent.time,path:[...stack]});
    drawHistory();
    show(item, 0, true);
    el("question").value = "";
    el("status").textContent = "Answer video ready · " + item.film.method;
  } catch (err) { el("status").textContent = err.message; }
  finally { pending(false); }
};
el("paperForm").onsubmit = async e => {
  e.preventDefault();
  if (busy) return;
  pending(true);
  el("importStatus").textContent = "Reading paper…";
  try {
    const item = await generate({paper:el("paper").value},el("importStatus"));
    stack = []; history = []; drawHistory(); tab(false);
    show(item);
    el("dialog").close();
    el("paper").value = el("question").value = el("status").textContent = el("importStatus").textContent = "";
  } catch (err) { el("importStatus").textContent = err.message; }
  finally { pending(false); }
};
fetch("/media/demo/story.json").then(r => r.json()).then(item => show(item)).catch(() => {
  el("status").textContent = "The demo could not load. Import a paper to start.";
});
