<script>
  import { onMount, onDestroy } from 'svelte';
  import html2canvas from 'html2canvas';
  import { FFmpeg } from '@ffmpeg/ffmpeg';
  import { toBlobURL } from '@ffmpeg/util';

  export let controller;

  let progressEl;
  let timeEl;
  let frameLink;
  let frameEl;
  let playBtn;

  function previewPath() {
    return $controller._previewPath || 'kamusai';
  }

  let renderState = { phase: 'idle', active: false, received: 0, total: 0, renderPct: 0, name: null, message: '', pending: false };
  let renderList = [];
  let sidebarOpen = true;
  let renderSidebarEl;
  let renderStatusEl;
  let renderModeEl;
  let renderListEl;
  let renderBtnEl;
  let renderCheckEl;
  let renderContinueEl;
  let renderCancelEl;
  let renderFolderBtnEl;
  let dirHandle = null;
  let frameMode = 'idb';
  let db = null;
  let ffmpegPromise = null;
  let ffmpegReady = false;
  let uiRaf = null;

  function dur() {
    return $controller.getDuration ? $controller.getDuration() : 60;
  }
  function fps() {
    return $controller.fps || 24;
  }

  function uiTick() {
    const t = $controller.getTime ? $controller.getTime() : 0;
    const d = dur();
    if (timeEl) timeEl.textContent = `${t.toFixed(1)}s / ${d.toFixed(1)}s`;
    if (frameLink && frameEl) {
      const f = Math.round(t * fps());
      frameLink.href = `/${previewPath()}/${f}`;
      frameEl.textContent = f;
    }
    if (progressEl) progressEl.value = d ? (t / d) * 100 : 0;
    if (playBtn) playBtn.textContent = $controller.isPlaying && $controller.isPlaying() ? '⏸' : '▶';
    uiRaf = requestAnimationFrame(uiTick);
  }

  function scrub(e) {
    const t = (parseFloat(e.target.value) / 100) * dur();
    if ($controller.seekTo) $controller.seekTo(t);
  }

  function keyHandler(e) {
    if (e.code === 'Space') { e.preventDefault(); if ($controller.playPause) $controller.playPause(); }
    if (e.code === 'ArrowLeft') { e.preventDefault(); if ($controller.stepFrame) $controller.stepFrame(-1); }
    if (e.code === 'ArrowRight') { e.preventDefault(); if ($controller.stepFrame) $controller.stepFrame(1); }
    if (e.code === 'ArrowUp') { e.preventDefault(); const t = $controller.getTime ? $controller.getTime() : 0; if ($controller.seekTo) $controller.seekTo(t - 1); }
    if (e.code === 'ArrowDown') { e.preventDefault(); const t = $controller.getTime ? $controller.getTime() : 0; if ($controller.seekTo) $controller.seekTo(t + 1); }
  }

  function pad5(i) {
    return String(i).padStart(5, '0');
  }

  function setError(msg) {
    renderState = { phase: 'error', active: false, received: 0, total: 0, renderPct: 0, name: null, message: msg, pending: false };
    updateRenderUi();
  }

  function enterRenderMode() {
    const el = $controller.canvasEl;
    const wr = $controller.wrapEl;
    if (el) {
      el.style.transform = 'none';
      const v = el.querySelector('.vignette');
      if (v) v.style.opacity = '0';
    }
    if (wr) {
      wr.style.width = $controller.W + 'px';
      wr.style.height = $controller.H + 'px';
    }
  }

  function exitRenderMode() {
    const el = $controller.canvasEl;
    const v = el && el.querySelector('.vignette');
    if (v) v.style.opacity = '';
    if ($controller.restoreLayout) $controller.restoreLayout();
  }

  function captureFrameBlob() {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const el = $controller.canvasEl;
        const W = $controller.W;
        const H = $controller.H;
        html2canvas(el, { scale: 1, width: W, height: H, windowWidth: W })
          .then((c) => new Promise((res) => c.toBlob(res, 'image/jpeg', 0.9)))
          .then(resolve)
          .catch((e) => {
            console.error('captureFrameBlob error', e);
            reject(e);
          });
      }, 40);
    });
  }

  async function setRenderFolder() {
    if (!window.isSecureContext || !window.showDirectoryPicker) {
      const why = !window.isSecureContext
        ? 'halaman dibuka via HTTP biasa (bukan secure context).'
        : 'browser ini tidak mendukung API pilih folder.';
      alert(`Mode folder butuh HTTPS. Saat ini ${why}\nBuka lewat https://video.misbahwork.my.id atau localhost, dan gunakan Chrome/Edge.\nSekarang memakai IndexedDB sebagai fallback.`);
      frameMode = 'idb';
      updateRenderUi();
      return;
    }
    try {
      dirHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
      if (dirHandle.requestPermission) {
        const perm = await dirHandle.requestPermission({ mode: 'readwrite' });
        if (perm !== 'granted') {
          alert('Izin tulis ke folder ditolak oleh Chrome. Coba pilih folder lain / beri izin.\nSekarang memakai IndexedDB.');
          dirHandle = null;
          frameMode = 'idb';
          updateRenderUi();
          return;
        }
      }
      const testName = '_videoweb_test.txt';
      try {
        const fh = await dirHandle.getFileHandle(testName, { create: true });
        const w = await fh.createWritable();
        await w.write('ok');
        await w.close();
        const r = await fh.getFile();
        await r.text();
        await dirHandle.removeEntry(testName);
        frameMode = 'folder';
        if (renderFolderBtnEl) renderFolderBtnEl.textContent = `📁 ${dirHandle.name || '(folder)'} (bisa tulis)`;
      } catch (e) {
        frameMode = 'idb';
        alert(`Tidak bisa TULIS ke folder "${dirHandle.name}". Error: ${e.message}\nSekarang memakai IndexedDB.`);
      }
    } catch {
      return;
    }
    updateRenderUi();
  }

  async function saveFrame(i, blob) {
    if (frameMode === 'folder' && dirHandle) {
      try {
        const fh = await dirHandle.getFileHandle(`frame_${pad5(i)}.jpeg`, { create: true });
        const w = await fh.createWritable();
        await w.write(blob);
        await w.close();
        console.log('saved frame', i, '->', `frame_${pad5(i)}.jpeg`);
      } catch (e) {
        console.error('saveFrame folder error', e);
        throw new Error('Gagal tulis frame ke folder: ' + e.message);
      }
    } else {
      await idbPut(db, 'frames', `f_${i}`, blob);
    }
  }

  async function readFrame(i) {
    if (frameMode === 'folder' && dirHandle) {
      return await (await dirHandle.getFileHandle(`frame_${pad5(i)}.jpeg`)).getFile();
    }
    return await idbGet(db, 'frames', `f_${i}`);
  }

  async function countFrames() {
    if (frameMode === 'folder' && dirHandle) {
      const re = /^frame_(\d{5})\.jpeg$/;
      const present = new Set();
      for await (const entry of dirHandle.values()) {
        if (entry.kind === 'file') {
          const m = entry.name.match(re);
          if (m) present.add(parseInt(m[1], 10));
        }
      }
      let n = 0;
      while (present.has(n)) n++;
      return n;
    }
    return (await idbKeys(db, 'frames')).length;
  }

  async function clearFrames() {
    if (frameMode === 'folder' && dirHandle) {
      for await (const entry of dirHandle.values()) {
        if (entry.kind === 'file' && /^frame_\d{5}\.jpeg$/.test(entry.name)) {
          try {
            await dirHandle.removeEntry(entry.name);
          } catch {}
        }
      }
    } else {
      await idbClear(db, 'frames');
    }
  }

  async function restoreJobHandle() {
    const meta = await idbGet(db, 'job', 'meta');
    if (meta && meta.frameMode === 'folder' && !dirHandle) {
      try {
        dirHandle = await idbGet(db, 'job', 'dirHandle');
      } catch {}
      if (dirHandle) frameMode = 'folder';
    }
  }

  async function getFfmpeg() {
    if (!ffmpegPromise) {
      ffmpegPromise = (async () => {
        const mt = !!window.crossOriginIsolated;
        const base = mt ? '/ffmpeg/' : '/ffmpeg/st/';
        const ff = new FFmpeg();
        const opts = {
          coreURL: await toBlobURL(base + 'ffmpeg-core.js', 'text/javascript'),
          wasmURL: await toBlobURL(base + 'ffmpeg-core.wasm', 'application/wasm'),
        };
        if (mt) opts.workerURL = await toBlobURL(base + 'ffmpeg-core.worker.js', 'text/javascript');
        await ff.load(opts);
        return ff;
      })();
    }
    return ffmpegPromise;
  }

  async function checkFfmpeg() {
    if (renderState.active) return;
    renderState = { phase: 'check', active: true, received: 0, total: 0, renderPct: 0, name: null, message: '', pending: false };
    updateRenderUi();
    try {
      await getFfmpeg();
      ffmpegReady = true;
      const mt = window.crossOriginIsolated ? 'multithread' : 'single-thread';
      renderState = { phase: 'done', active: false, received: 0, total: 0, renderPct: 100, name: 'FFmpeg wasm siap', message: `core: ${mt}`, pending: false };
    } catch (e) {
      ffmpegReady = false;
      renderState = { phase: 'error', active: false, received: 0, total: 0, renderPct: 0, name: null, message: 'Gagal muat ffmpeg: ' + e.message, pending: false };
    }
    updateRenderUi();
  }

  async function runCaptureLoop(from, total, jobName) {
    renderState = { phase: 'capture', active: true, received: from, total, renderPct: 0, name: jobName, message: '', pending: false };
    updateRenderUi();
    enterRenderMode();
    try {
      for (let i = from; i < total; i++) {
        if ($controller.seekTo) $controller.seekTo(Math.min(dur(), i / fps()));
        const blob = await captureFrameBlob();
        await saveFrame(i, blob);
        renderState = { ...renderState, received: i + 1 };
        updateRenderUi();
        if (i % 5 === 4) {
          try {
            const n = await countFrames();
            if (renderModeEl) renderModeEl.textContent = `📁 Folder: ${n} frame_*.jpeg tersimpan`;
          } catch {}
        }
      }
    } catch (e) {
      console.error('capture loop error', e);
      setError(e.message);
      return;
    } finally {
      exitRenderMode();
    }
    await encodeVideo(total, jobName);
  }

  async function encodeVideo(total, jobName) {
    renderState = { ...renderState, phase: 'encode', renderPct: 0 };
    updateRenderUi();
    const ff = await getFfmpeg();
    for (let i = 0; i < total; i++) {
      const blob = await readFrame(i);
      await ff.writeFile(`frame_${pad5(i)}.jpg`, new Uint8Array(await blob.arrayBuffer()));
    }
    const onPct = ({ progress }) => {
      renderState = { ...renderState, renderPct: Math.round(progress * 100) };
      updateRenderUi();
    };
    ff.on('progress', onPct);
    try {
      await ff.exec(['-y', '-framerate', String(fps()), '-i', 'frame_%05d.jpg', '-c:v', 'libx264', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', 'out.mp4']);
    } finally {
      ff.off('progress', onPct);
    }
    const outData = await ff.readFile('out.mp4');
    const outBlob = new Blob([outData.slice(0)], { type: 'video/mp4' });
    let savedInFolder = false;
    if (frameMode === 'folder' && dirHandle) {
      try {
        const fh = await dirHandle.getFileHandle(jobName, { create: true });
        const w = await fh.createWritable();
        await w.write(outBlob);
        await w.close();
        savedInFolder = true;
      } catch (e) {
        console.error('gagal simpan mp4 ke folder', e);
      }
    }
    await idbPut(db, 'videos', jobName, { name: jobName, blob: outBlob, size: outBlob.size, at: Date.now() });
    await idbClear(db, 'frames');
    await idbDelete(db, 'job', 'meta');
    await idbDelete(db, 'job', 'dirHandle');
    if (!savedInFolder) triggerDownload(jobName, outBlob);
    renderState = {
      phase: 'done',
      active: false,
      received: total,
      total,
      renderPct: 100,
      name: jobName,
      message: savedInFolder
        ? `✅ MP4 tersimpan di folder "${dirHandle.name}" (${(outBlob.size / 1048576).toFixed(1)} MB)`
        : `tersimpan di browser (${(outBlob.size / 1048576).toFixed(1)} MB)`,
      pending: false,
    };
    updateRenderUi();
    refreshRenderList();
  }

  function triggerDownload(name, blob) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);
  }

  async function renderVideo() {
    if (renderState.active) return;
    if ($controller.pause) $controller.pause();
    try {
      const total = Math.round(dur() * fps());
      frameMode = dirHandle ? 'folder' : 'idb';
      const jobName = await nextLocalName();
      await clearFrames();
      await idbPut(db, 'job', 'meta', { total, name: jobName, startedAt: Date.now(), frameMode });
      if (frameMode === 'folder' && dirHandle) {
        try {
          await idbPut(db, 'job', 'dirHandle', dirHandle);
        } catch {}
      }
      await runCaptureLoop(0, total, jobName);
    } catch (e) {
      setError(e.message);
    }
  }

  async function continueRender() {
    if (renderState.active) return;
    const meta = await idbGet(db, 'job', 'meta');
    if (!meta) {
      setError('tidak ada job tersimpan');
      return;
    }
    await restoreJobHandle();
    if (meta.frameMode === 'folder' && !dirHandle) {
      const ok = await setRenderFolder();
      frameMode = dirHandle ? 'folder' : 'idb';
    } else if (!dirHandle && meta.frameMode === 'idb') {
      frameMode = 'idb';
    }
    const count = await countFrames();
    if ($controller.pause) $controller.pause();
    await runCaptureLoop(count, meta.total, meta.name);
  }

  async function cancelRender() {
    if (db) {
      await clearFrames();
      await idbDelete(db, 'job', 'meta');
      await idbDelete(db, 'job', 'dirHandle');
    }
    dirHandle = null;
    frameMode = 'idb';
    renderState = { phase: 'idle', active: false, received: 0, total: 0, renderPct: 0, name: null, message: '', pending: false };
    updateRenderUi();
  }

  async function nextLocalName() {
    const keys = await idbKeys(db, 'videos');
    let idx = 0;
    while (keys.includes(`jargon${idx ? `(${idx})` : ''}.mp4`)) idx++;
    return idx === 0 ? 'jargon.mp4' : `jargon(${idx}).mp4`;
  }

  async function checkPendingJob() {
    if (!db) return;
    const meta = await idbGet(db, 'job', 'meta');
    if (!meta) return;
    await restoreJobHandle();
    const count = await countFrames();
    renderState = { ...renderState, phase: 'idle', pending: true, received: Math.min(count, meta.total), total: meta.total, name: meta.name };
    updateRenderUi();
  }

  function updateRenderUi() {
    if (!renderStatusEl) return;
    const s = renderState;
    let html = '';
    if (s.phase === 'idle') {
      html = `<div class="rs-idle">Render lokal siap — semua proses di browser ini, tidak ada upload.</div>`;
      if (!window.isSecureContext) html += `<div class="rs-idle" style="color:#ffb74d">⚠ Untuk mode folder: buka <b>https://video.misbahwork.my.id</b> (HTTPS), bukan http://</div>`;
    } else if (s.phase === 'check') {
      html = `<div class="rs-phase">⏳ Memuat ffmpeg.wasm…</div>`;
    } else if (s.phase === 'capture') {
      html = `<div class="rs-phase">📸 Capture frame <b>${s.received}</b> / <b>${s.total}</b></div>`;
      html += `<div class="rs-bar"><div class="rs-fill" style="width:${s.total ? (s.received / s.total) * 100 : 0}%"></div></div>`;
    } else if (s.phase === 'encode') {
      html = `<div class="rs-phase">🎞 Encode ffmpeg.wasm… <b>${s.renderPct}%</b></div>`;
      html += `<div class="rs-bar"><div class="rs-fill" style="width:${s.renderPct}%"></div></div>`;
    } else if (s.phase === 'done') {
      html = `<div class="rs-phase rs-done">✅ <b>${s.name}</b></div>`;
      if (s.message) html += `<div class="rs-phase" style="font-size:11px;color:#888">${s.message}</div>`;
    } else if (s.phase === 'error') {
      html = `<div class="rs-phase rs-error">❌ Error</div>`;
      if (s.message) html += `<div class="rs-phase rs-error" style="font-size:11px">${s.message}</div>`;
    }
    renderStatusEl.innerHTML = html;
    if (renderBtnEl) {
      renderBtnEl.disabled = s.active;
      renderBtnEl.textContent = s.active ? '⏳ Rendering…' : '🎬 Render Video';
    }
    if (renderCheckEl) {
      renderCheckEl.textContent = ffmpegReady ? '✓ FFmpeg siap' : '🔍 Cek FFmpeg';
      renderCheckEl.style.display = s.active ? 'none' : 'block';
    }
    const canContinue = s.phase === 'idle' && s.pending;
    if (renderContinueEl) {
      renderContinueEl.style.display = canContinue ? 'block' : 'none';
      renderContinueEl.textContent = `▶ Lanjutkan render (dari frame ${s.received})`;
    }
    if (renderCancelEl) {
      renderCancelEl.style.display = s.active ? 'block' : 'none';
    }
    if (renderModeEl) {
      const folder = frameMode === 'folder' && dirHandle;
      renderModeEl.textContent = folder
        ? '📁 Frames: folder terpilih (frame_00000.jpeg…), bisa dicek & dilanjutkan'
        : '💾 Frames: IndexedDB browser';
      renderModeEl.style.color = folder ? '#7ae582' : '#aaa';
    }
    const fs = document.getElementById('folder-status');
    if (fs) {
      if (frameMode === 'folder' && dirHandle) {
        fs.textContent = `📁 Folder: ${dirHandle.name || '(terpilih)'}`;
        fs.style.color = '#7ae582';
      } else {
        fs.textContent = '';
      }
    }
  }

  function renderSidebarList() {
    if (!renderListEl) return;
    if (!renderList.length) {
      renderListEl.innerHTML = '<div class="rs-empty">Belum ada hasil render.</div>';
      return;
    }
    renderListEl.innerHTML = renderList
      .map(
        (f) =>
          `<div class="rs-file" onclick="__player_download('${f.name.replace(/'/g, "\\'")}')">📁 ${f.name} <span class="rs-size">${(f.size / 1048576).toFixed(1)}MB</span></div>`
      )
      .join('');
  }

  function refreshRenderList() {
    if (!db) return;
    idbKeys(db, 'videos')
      .then((keys) => Promise.all(keys.map((k) => idbGet(db, 'videos', k))))
      .then((recs) => {
        renderList = recs
          .map((r) => ({ name: r.name, size: r.size, at: r.at }))
          .sort((a, b) => b.at - a.at);
        renderSidebarList();
      })
      .catch(() => {});
  }

  function openDB() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open('jargon-render-db', 1);
      req.onupgradeneeded = () => {
        const d = req.result;
        if (!d.objectStoreNames.contains('frames')) d.createObjectStore('frames');
        if (!d.objectStoreNames.contains('videos')) d.createObjectStore('videos');
        if (!d.objectStoreNames.contains('job')) d.createObjectStore('job');
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  function idbPut(d, store, key, val) {
    return new Promise((res, rej) => {
      const tx = d.transaction(store, 'readwrite');
      tx.objectStore(store).put(val, key);
      tx.oncomplete = res;
      tx.onerror = () => rej(tx.error);
    });
  }
  function idbGet(d, store, key) {
    return new Promise((res, rej) => {
      const tx = d.transaction(store, 'readonly');
      const r = tx.objectStore(store).get(key);
      r.onsuccess = () => res(r.result);
      r.onerror = () => rej(r.error);
    });
  }
  function idbKeys(d, store) {
    return new Promise((res, rej) => {
      const tx = d.transaction(store, 'readonly');
      const r = tx.objectStore(store).getAllKeys();
      r.onsuccess = () => res(r.result);
      r.onerror = () => rej(r.error);
    });
  }
  function idbDelete(d, store, key) {
    return new Promise((res, rej) => {
      const tx = d.transaction(store, 'readwrite');
      tx.objectStore(store).delete(key);
      tx.oncomplete = res;
      tx.onerror = () => rej(tx.error);
    });
  }
  function idbClear(d, store) {
    return new Promise((res, rej) => {
      const tx = d.transaction(store, 'readwrite');
      tx.objectStore(store).clear();
      tx.oncomplete = res;
      tx.onerror = () => rej(tx.error);
    });
  }

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
    if (!sidebarOpen) return;
    refreshRenderList();
  }

  function openSidebar() {
    sidebarOpen = true;
    refreshRenderList();
  }

  onMount(() => {
    uiRaf = requestAnimationFrame(uiTick);
    window.addEventListener('keydown', keyHandler);
    window.__player_download = async (name) => {
      if (!db) return;
      const rec = await idbGet(db, 'videos', name);
      if (!rec) return;
      triggerDownload(rec.name, rec.blob);
    };
    window.__renderUI = {
      renderVideo, checkFfmpeg, continueRender, cancelRender,
      getRenderState: () => renderState,
      getFfmpeg, encodeVideo,
    };
    openDB().then((d) => {
      db = d;
      checkPendingJob();
      refreshRenderList();
      updateRenderUi();
    });
  });

  onDestroy(() => {
    cancelAnimationFrame(uiRaf);
    window.removeEventListener('keydown', keyHandler);
  });
</script>

<div class="video-ui">
  {#if !sidebarOpen}
    <button id="sidebar-open-btn" title="Buka sidebar render" on:click={openSidebar}>▮</button>
  {/if}
  <div class="render-sidebar" class:collapsed={!sidebarOpen} bind:this={renderSidebarEl}>
    <div class="rs-header">
      <span>Render Lokal</span>
      <button class="rs-toggle" title="Toggle sidebar" on:click={toggleSidebar}>{sidebarOpen ? '»' : '«'}</button>
    </div>
    <div class="rs-body">
      <button bind:this={renderFolderBtnEl} class="btn-folder" on:click={setRenderFolder}>📁 Set Folder</button>
      <span id="folder-status" style="font-size:11px;color:#aaa;padding-left:4px;"></span>
      <button bind:this={renderBtnEl} class="btn-render" on:click={renderVideo}>🎬 Render Video</button>
      <button bind:this={renderCheckEl} class="btn-check" on:click={checkFfmpeg}>🔍 Cek FFmpeg</button>
      <button bind:this={renderContinueEl} class="btn-continue" on:click={continueRender}>▶ Lanjutkan render</button>
      <button bind:this={renderCancelEl} class="btn-cancel" on:click={cancelRender}>✖ Cancel Render</button>
      <div class="rs-status" bind:this={renderStatusEl}></div>
      <div class="rs-mode" bind:this={renderModeEl}></div>
      <div class="rs-title">Hasil Render (local)</div>
      <div class="rs-list" bind:this={renderListEl}></div>
    </div>
  </div>

  <div class="controls">
    <div class="ctrl-row">
      <button bind:this={playBtn} class="btn-play" on:click={() => $controller.playPause && $controller.playPause()}>▶</button>
      <button class="btn" title="Frame prev (←)" on:click={() => $controller.stepFrame && $controller.stepFrame(-1)}>⏮</button>
      <button class="btn" title="Frame next (→)" on:click={() => $controller.stepFrame && $controller.stepFrame(1)}>⏭</button>
      <button class="btn" title="Reset" on:click={() => $controller.reset && $controller.reset()}>↺</button>
      <button class="btn" title="Export frame PNG" on:click={() => $controller.exportFrame && $controller.exportFrame()}>🖼</button>
      <a bind:this={frameLink} class="frame-pos-link" href="/kamusai/0">#<span bind:this={frameEl} class="frame-num">0</span></a>
    </div>
    <div class="ctrl-row">
      <input type="range" bind:this={progressEl} min="0" max="100" value="0" on:input={scrub} class="seek" />
      <span bind:this={timeEl} class="time">0.0s / 60.0s</span>
    </div>
  </div>
</div>

<style>
  .video-ui { position: fixed; inset: 0; pointer-events: none; z-index: 60; }
  .video-ui .controls,
  .video-ui .render-sidebar,
  .video-ui #sidebar-open-btn,
  .video-ui .rs-toggle { pointer-events: auto; }

  .controls {
    position: fixed;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: min(640px, 90vw);
    padding: 16px;
    background: rgba(10, 12, 28, 0.85);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  .ctrl-row { display: flex; align-items: center; gap: 8px; }
  .btn-play, .btn {
    background: rgba(0, 191, 255, 0.15);
    border: 1px solid rgba(0, 191, 255, 0.4);
    color: #fff;
    font-size: 18px;
    padding: 8px 14px;
    border-radius: 8px;
    cursor: pointer;
  }
  .btn-play:hover, .btn:hover { background: rgba(0, 191, 255, 0.3); }
  .btn-play { min-width: 56px; font-size: 20px; }
   .seek { flex: 1; accent-color: #00BFFF; }
   .frame-pos-link { text-decoration: none; display: inline-flex; align-items: center; background: rgba(0, 191, 255, 0.12); border: 1px solid rgba(0, 191, 255, 0.3); border-radius: 6px; padding: 4px 10px; cursor: pointer; transition: background 0.2s, border-color 0.2s; }
   .frame-pos-link:hover { background: rgba(0, 191, 255, 0.3); border-color: rgba(0, 191, 255, 0.6); }
   .frame-num { font-size: 14px; color: #9adcff; font-weight: 700; font-variant-numeric: tabular-nums; }
   .time { font-size: 13px; color: #aaa; white-space: nowrap; }

  .render-sidebar {
    position: fixed;
    top: 0;
    right: 0;
    height: 100vh;
    width: 300px;
    background: rgba(10, 12, 28, 0.95);
    border-left: 1px solid rgba(0, 191, 255, 0.2);
    box-shadow: -10px 0 40px rgba(0, 0, 0, 0.4);
    z-index: 50;
    display: flex;
    flex-direction: column;
    transition: transform 0.25s ease;
  }
  .render-sidebar.collapsed {
    transform: translateX(100%);
  }
  #sidebar-open-btn {
    position: fixed;
    top: 12px;
    right: 8px;
    z-index: 51;
    background: rgba(10, 12, 28, 0.95);
    border-left: 1px solid rgba(0, 191, 255, 0.3);
    color: #9adcff;
    font-size: 16px;
    padding: 4px 10px;
    cursor: pointer;
    border-radius: 4px 0 0 4px;
  }
  .btn-folder {
    background: rgba(0, 230, 118, 0.12);
    border: 1px solid rgba(0, 230, 118, 0.5);
    color: #7ae582;
    font-size: 14px;
    font-weight: 600;
    padding: 10px;
    border-radius: 10px;
    cursor: pointer;
    text-align: center;
  }
  .btn-folder:hover { background: rgba(0, 230, 118, 0.25); }
  .rs-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 14px;
    font-weight: 700;
    font-size: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    color: #9adcff;
  }
  .rs-toggle {
    background: rgba(0, 191, 255, 0.15);
    border: 1px solid rgba(0, 191, 255, 0.4);
    color: #fff;
    border-radius: 6px;
    padding: 2px 10px;
    cursor: pointer;
  }
  .rs-body { padding: 14px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }
  .btn-render {
    background: linear-gradient(90deg, rgba(0, 191, 255, 0.3), rgba(0, 230, 118, 0.25));
    border: 1px solid rgba(0, 191, 255, 0.5);
    color: #fff;
    font-size: 16px;
    font-weight: 700;
    padding: 12px;
    border-radius: 10px;
    cursor: pointer;
  }
  .btn-render:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-check {
    background: rgba(255, 180, 0, 0.15);
    border: 1px solid rgba(255, 180, 0, 0.5);
    color: #ffd77a;
    font-size: 14px;
    font-weight: 600;
    padding: 10px;
    border-radius: 10px;
    cursor: pointer;
  }
  .btn-check:hover { background: rgba(255, 180, 0, 0.3); }
  .btn-cancel {
    display: none;
    background: rgba(255, 82, 82, 0.15);
    border: 1px solid rgba(255, 82, 82, 0.5);
    color: #ff9c9c;
    font-size: 14px;
    font-weight: 600;
    padding: 10px;
    border-radius: 10px;
    cursor: pointer;
  }
  .btn-cancel:hover { background: rgba(255, 82, 82, 0.3); }
  .btn-continue {
    display: none;
    background: rgba(0, 230, 118, 0.15);
    border: 1px solid rgba(0, 230, 118, 0.5);
    color: #a5ffd4;
    font-size: 14px;
    font-weight: 600;
    padding: 10px;
    border-radius: 10px;
    cursor: pointer;
  }
  .btn-continue:hover { background: rgba(0, 230, 118, 0.3); }
  .rs-status { display: flex; flex-direction: column; gap: 8px; }
  :global(.rs-idle) { color: #888; font-size: 13px; }
  :global(.rs-phase) { font-size: 13px; color: #eee; }
  :global(.rs-done) { color: #00e676; }
  :global(.rs-error) { color: #ff5252; }
  :global(.rs-bar) { height: 10px; background: rgba(255, 255, 255, 0.08); border-radius: 6px; overflow: hidden; }
  :global(.rs-fill) { height: 100%; background: linear-gradient(90deg, #00BFFF, #00E676); width: 0; transition: width 0.3s; }
  .rs-title { font-size: 13px; font-weight: 700; color: #9adcff; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 10px; }
  .rs-mode { font-size: 11px; color: #aaa; padding: 6px 0 2px; border-bottom: 1px dashed rgba(255, 255, 255, 0.08); margin-bottom: 6px; }
  .rs-list { display: flex; flex-direction: column; gap: 6px; }
  :global(.rs-file) {
    color: #9adcff;
    text-decoration: none;
    font-size: 13px;
    padding: 8px 10px;
    background: rgba(0, 191, 255, 0.08);
    border: 1px solid rgba(0, 191, 255, 0.2);
    border-radius: 8px;
  }
  :global(.rs-file:hover) { background: rgba(0, 191, 255, 0.2); }
  :global(.rs-size) { float: right; color: #666; font-size: 11px; }
  :global(.rs-empty) { color: #666; font-size: 12px; }
</style>
