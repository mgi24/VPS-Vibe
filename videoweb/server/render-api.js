import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import JSZip from 'jszip';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const TEMP_DIR = path.join(ROOT, 'temp', 'render');
const RENDER_DIR = path.join(ROOT, 'renders');

const FPS = 24;
const VIDEO_NAME = 'jargon';

let job = null;

function sendJson(res, code, obj) {
  res.statusCode = code;
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify(obj));
}

function sendText(res, code, text, type) {
  res.statusCode = code;
  res.setHeader('Content-Type', type || 'text/plain; charset=utf-8');
  res.end(text);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

function ensureDirs() {
  fs.mkdirSync(TEMP_DIR, { recursive: true });
  fs.mkdirSync(RENDER_DIR, { recursive: true });
}

function nextOutputName() {
  ensureDirs();
  const existing = fs.readdirSync(RENDER_DIR).filter((f) => f.endsWith('.mp4'));
  let idx = 0;
  while (existing.includes(`${VIDEO_NAME}${idx ? `(${idx})` : ''}.mp4`)) {
    idx++;
  }
  return idx === 0 ? `${VIDEO_NAME}.mp4` : `${VIDEO_NAME}(${idx}).mp4`;
}

function getStatus() {
  if (!job) {
    return { active: false, phase: 'idle', received: 0, total: 0, name: null, message: 'idle' };
  }
  const pct = job.total ? Math.round((job.received / job.total) * 100) : 0;
  let message = job.phase;
  if (job.phase === 'upload') message = `upload ${job.received}/${job.total}`;
  if (job.phase === 'render') message = `rendering ${job.renderPct}%`;
  if (job.phase === 'done') message = `done: ${job.name}`;
  if (job.phase === 'error') message = `error: ${job.error}`;
  return {
    id: path.basename(job.dir),
    active: job.phase === 'upload' || job.phase === 'render',
    phase: job.phase,
    received: job.received,
    total: job.total,
    renderPct: job.renderPct || 0,
    name: job.name || null,
    message,
  };
}

function startRender(res, total) {
  if (job && (job.phase === 'upload' || job.phase === 'render')) {
    sendJson(res, 503, { error: 'render already in progress' });
    return;
  }
  ensureDirs();
  cleanupStaleJobs();
  const dir = path.join(TEMP_DIR, `job_${Date.now()}`);
  fs.mkdirSync(dir, { recursive: true });
  job = {
    dir,
    phase: 'upload',
    received: 0,
    total: total || 0,
    renderPct: 0,
    name: null,
    error: null,
    startedAt: Date.now(),
  };
  sendJson(res, 200, { ok: true, dir, id: path.basename(dir) });
}

function cleanupStaleJobs() {
  try {
    for (const entry of fs.readdirSync(TEMP_DIR, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const dir = path.join(TEMP_DIR, entry.name);
      const ageMs = Date.now() - fs.statSync(dir).mtimeMs;
      if (ageMs > 60 * 60 * 1000) fs.rmSync(dir, { recursive: true, force: true });
    }
  } catch {}
}

function countContiguous(dir) {
  let n = 0;
  while (fs.existsSync(path.join(dir, `frame_${String(n).padStart(5, '0')}.jpg`))) n++;
  return n;
}

function startFfmpeg(res) {
  job.name = nextOutputName();
  job.phase = 'render';
  job.renderPct = 0;
  const out = path.join(RENDER_DIR, job.name);
  const ff = spawn('ffmpeg', [
    '-y',
    '-framerate', String(FPS),
    '-i', path.join(job.dir, 'frame_%05d.jpg'),
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart',
    '-progress', 'pipe:1',
    '-nostats',
    out,
  ]);
  job.ff = ff;
  let progressBuf = '';
  ff.stdout.on('data', (d) => {
    if (!job || job.ff !== ff) return;
    progressBuf += d.toString();
    const m = progressBuf.match(/out_time_us=(\d+)/g);
    if (m) {
      const us = parseInt(m[m.length - 1].split('=')[1], 10);
      job.renderPct = job.total ? Math.min(100, Math.round((us / 1e6 / (job.total / FPS)) * 100)) : 0;
    }
  });
  ff.stderr.on('data', () => {});
  ff.on('close', (code) => {
    if (!job || job.ff !== ff) return;
    if (code === 0) {
      job.phase = 'done';
      job.renderPct = 100;
      fs.rmSync(job.dir, { recursive: true, force: true });
    } else {
      job.phase = 'error';
      job.error = `ffmpeg exited ${code}`;
    }
  });
  sendJson(res, 200, { ok: true, name: job.name });
}

function runFfmpeg(res, req) {
  void req;
  if (!job) {
    sendJson(res, 404, { error: 'no render job' });
    return;
  }
  if (job.phase !== 'upload') {
    sendJson(res, 409, { error: 'render is not in upload phase' });
    return;
  }
  if (job.received < job.total) {
    sendJson(res, 400, { error: `only ${job.received}/${job.total} frames uploaded` });
    return;
  }
  startFfmpeg(res);
}

async function handleZipUpload(res, req) {
  if (!job) {
    sendJson(res, 404, { error: 'no render job' });
    return;
  }
  if (job.phase !== 'upload') {
    sendJson(res, 409, { error: 'render is not in upload phase' });
    return;
  }
  const body = await readBody(req);
  const zip = await JSZip.loadAsync(body);
  const files = zip.file(/^frame_\d{5}\.(png|jpg)$/).filter((f) => !f.dir);
  if (!files.length) {
    sendJson(res, 400, { error: 'zip berisi 0 frame' });
    return;
  }
  if (files.length < job.total) {
    sendJson(res, 400, { error: `zip hanya berisi ${files.length}/${job.total} frame` });
    return;
  }
  for (const f of files) {
    const buf = await f.async('nodebuffer');
    fs.writeFileSync(path.join(job.dir, f.name), buf);
  }
  job.received = files.length;
  startFfmpeg(res);
}

function handler(req, res) {
  const url = new URL(req.url, 'http://localhost');
  const p = url.pathname;

  if (req.method === 'POST' && p === '/api/render/start') {
    const total = parseInt(url.searchParams.get('total') || '0', 10);
    startRender(res, total);
    return;
  }

  if (req.method === 'POST' && p === '/api/render/frame') {
    (async () => {
      if (!job) {
        sendJson(res, 404, { error: 'no render job' });
        return;
      }
      if (job.phase !== 'upload') {
        sendJson(res, 409, { error: 'render is not in upload phase' });
        return;
      }
      const index = parseInt(url.searchParams.get('index') || '-1', 10);
      if (index < 0) {
        sendJson(res, 400, { error: 'invalid index' });
        return;
      }
      const body = await readBody(req);
      const file = path.join(job.dir, `frame_${String(index).padStart(5, '0')}.jpg`);
      fs.writeFileSync(file, body);
      job.received = countContiguous(job.dir);
      sendJson(res, 200, { ok: true, received: job.received, total: job.total });
    })().catch((e) => sendJson(res, 500, { error: e.message }));
    return;
  }

  if (req.method === 'POST' && p === '/api/render/finish') {
    runFfmpeg(res, req);
    return;
  }

  if (req.method === 'POST' && p === '/api/render/zip') {
    handleZipUpload(res, req).catch((e) => sendJson(res, 500, { error: e.message }));
    return;
  }

  if (req.method === 'POST' && p === '/api/render/cancel') {
    if (!job) {
      sendJson(res, 200, { ok: true, message: 'no job to cancel' });
      return;
    }
    const j = job;
    job = null;
    try { j.ff?.kill('SIGKILL'); } catch {}
    try { fs.rmSync(j.dir, { recursive: true, force: true }); } catch {}
    sendJson(res, 200, { ok: true, cancelled: j.name || null });
    return;
  }

  if (req.method === 'GET' && p === '/api/render/status') {
    sendJson(res, 200, getStatus());
    return;
  }

  if (req.method === 'GET' && p === '/api/render/list') {
    ensureDirs();
    const files = fs.readdirSync(RENDER_DIR).filter((f) => f.endsWith('.mp4')).sort();
    sendJson(res, 200, { renders: files });
    return;
  }

  if (p.startsWith('/renders/')) {
    const name = path.basename(p);
    const full = path.join(RENDER_DIR, name);
    if (!full.startsWith(RENDER_DIR) || !fs.existsSync(full)) {
      sendText(res, 404, 'not found');
      return;
    }
    res.setHeader('Content-Type', 'video/mp4');
    fs.createReadStream(full).pipe(res);
    return;
  }

  return null;
}

export function renderApiPlugin() {
  return {
    name: 'render-api',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const handled = handler(req, res);
        if (handled === null) next();
      });
    },
  };
}
