// Speaker-embedding worker for Slovo Listen.
// Runs WavLM-Base-Plus-SV (x-vector head) on-device via Transformers.js and returns
// 512-dim speaker embeddings for 16 kHz mono Float32 audio. Nothing leaves the phone.
import { AutoProcessor, AutoModel, env } from "https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2";

env.allowLocalModels = false;
env.useBrowserCache = true;

const MODEL_ID = "Xenova/wavlm-base-plus-sv";
let processor = null, model = null, loading = null;
const files = {};

function report(p) {
  if (p && p.status === "progress" && p.file) {
    files[p.file] = { loaded: p.loaded || 0, total: p.total || 0 };
    let loaded = 0, total = 0;
    for (const f of Object.values(files)) { loaded += f.loaded; total += f.total; }
    postMessage({ type: "progress", pct: total ? Math.round(loaded / total * 100) : 0 });
  }
}

function load() {
  if (!loading) {
    loading = (async () => {
      processor = await AutoProcessor.from_pretrained(MODEL_ID);
      model = await AutoModel.from_pretrained(MODEL_ID, { quantized: true, progress_callback: report });
      postMessage({ type: "ready" });
    })().catch(err => { loading = null; throw err; });
  }
  return loading;
}

onmessage = async (e) => {
  const { type, id, audio } = e.data || {};
  try {
    if (type === "load") { await load(); return; }
    if (type === "embed") {
      await load();
      const inputs = await processor(audio);
      const out = await model(inputs);
      const emb = out.embeddings ? out.embeddings.data : null;
      if (!emb) throw new Error("model returned no embeddings");
      postMessage({ type: "emb", id, emb: Array.from(emb) });
    }
  } catch (err) {
    postMessage({ type: "error", id, message: String(err && err.message || err) });
  }
};
