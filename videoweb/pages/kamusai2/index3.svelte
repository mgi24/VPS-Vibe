<script>
  import { onMount, onDestroy } from 'svelte';
  import gsap from 'gsap';
  export let controller = null;
  export let showFrame = -1;
  let canvasEl; let wrapEl; let tl = null; let raf = null;
  let manualT = 0, lastTs = 0, duration = 15.66, isPlaying = false, speed = 1;
  const W = 1080, H = 1920;

  function setupCanvasSize() {
    const isPreview = showFrame >= 0 && isFinite(showFrame);
    const availableW = window.innerWidth, availableH = isPreview ? window.innerHeight : window.innerHeight - 160;
    const scale = Math.min(availableW / W, availableH / H) * (isPreview ? 0.95 : 0.92);
    if (!isPreview) { document.querySelector('.kamusai-page')?.style.removeProperty('padding-top'); wrapEl?.style.removeProperty('margin-top'); }
    else { const page = document.querySelector('.kamusai-page'); if (page) { page.style.paddingTop = '0'; page.style.marginTop = '0'; } if (wrapEl) wrapEl.style.marginTop = '0'; if (canvasEl) canvasEl.style.overflow = ''; }
    if (wrapEl) { wrapEl.style.width = W * scale + 'px'; wrapEl.style.height = H * scale + 'px'; }
    if (canvasEl) canvasEl.style.transform = `scale(${scale})`;
  }

  function buildTimeline() {
    tl = gsap.timeline({ paused: true });
    document.querySelectorAll('.kamusai-sec').forEach(el => { el.style.display = 'none'; el.style.opacity = '0'; });
    tl.set('.kamusai-multimodal', { autoAlpha: 1, display: 'flex' }, 0);
    document.querySelectorAll('.kamusai-sec').forEach(el => { if (!el.classList.contains('kamusai-multimodal')) { el.style.display = 'none'; } });
    tl.fromTo('.kamusai-multi-title', { autoAlpha: 0, y: -40 }, { autoAlpha: 1, y: 0, duration: 0.6, ease: 'back.out(2)' }, 0);
    tl.fromTo('.kamusai-multi-subtitle', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.4 }, 0.5);
    const multiItems = document.querySelectorAll('.kamusai-multi-item');
    gsap.set(multiItems, { autoAlpha: 0, y: 30 });
    tl.to(multiItems, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'power2.out', stagger: 0.2 }, 1.0);
    tl.fromTo('.kamusai-multi-arrow', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.3 }, 2.0);
    tl.fromTo('.kamusai-multi-model-box', { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.6, ease: 'back.out(2)' }, 2.4);
    tl.fromTo('.kamusai-multi-arrow2', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.3 }, 3.2);
    const resultItems = document.querySelectorAll('.kamusai-result-item');
    gsap.set(resultItems, { autoAlpha: 0, y: -20 });
    tl.to(resultItems, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'power2.out', stagger: 0.3 }, 3.6);
    tl.duration(duration);
  }

  function tick(ts) {
    if (isPlaying) { const dt = (ts - lastTs) / 1000 * speed; lastTs = ts; manualT = Math.min(duration, manualT + dt); tl.seek(manualT); if (manualT >= duration) isPlaying = false; } else { lastTs = ts; if (showFrame && showFrame >= 0) { cancelAnimationFrame(raf); raf = null; return; } }
    raf = requestAnimationFrame(tick);
  }
  function play() { if (manualT >= duration) manualT = 0; isPlaying = true; lastTs = performance.now(); }
  function pause() { isPlaying = false; }
  function playPause() { isPlaying ? pause() : play(); }
  function seekTo(t) { t = Math.max(0, Math.min(duration, t)); manualT = t; tl.seek(t); }
  function getTime() { return manualT; } function getDuration() { return duration; }
  function isPlayingFn() { return isPlaying; } function setSpeed(s) { speed = s || 1; }
  function stepFrame(dir) { const fpsVal = 24; seekTo(manualT + (dir / fpsVal)); }
  function reset() { manualT = 0; isPlaying = false; tl.seek(0); }

  onMount(() => {
    buildTimeline();
    setupCanvasSize(); window.addEventListener('resize', setupCanvasSize);
    if (showFrame >= 0 && isFinite(showFrame)) { const previewTime = Math.min(showFrame / 24, duration - 0.01); requestAnimationFrame(() => { tl.render(previewTime, true); gsap.ticker.pause(); raf = null; if (controller) controller.update(c => ({ ...c, stageReady: true, W, H, duration, canvasEl, wrapEl, play, pause, playPause, seekTo, getTime, getDuration, isPlaying: isPlayingFn, setSpeed, stepFrame, reset })); }); }
    else { tl.seek(0); raf = requestAnimationFrame(tick); if (controller) controller.update(c => ({ ...c, stageReady: true, W, H, duration, canvasEl, wrapEl, play, pause, playPause, seekTo, getTime, getDuration, isPlaying: isPlayingFn, setSpeed, stepFrame, reset })); }
  });

  onDestroy(() => { cancelAnimationFrame(raf); window.removeEventListener('resize', setupCanvasSize); if (tl) tl.kill(); if (controller) controller.update(c => ({ ...c, stageReady: false })); });
</script>
<div class="kamusai-page"><div class="kamusai-wrap" bind:this={wrapEl}><div class="kamusai-stage" bind:this={canvasEl}>
  <div class="kamusai-sec kamusai-multimodal">
    <div class="kamusai-multi-container">
      <h1 class="kamusai-multi-title">MULTIMODAL</h1>
      <p class="kamusai-multi-subtitle">Bisa Banyak Input!</p>
      <div class="kamusai-multi-grid">
        <div class="kamusai-multi-item"><span class="multi-emoji">📝</span><br><span class="multi-label">TEKS</span></div>
        <div class="kamusai-multi-item"><span class="multi-emoji">🖼️</span><br><span class="multi-label">GAMBAR</span></div>
        <div class="kamusai-multi-item"><span class="multi-emoji">🎵</span><br><span class="multi-label">SUARA</span></div>
        <div class="kamusai-multi-item"><span class="multi-emoji">🎥</span><br><span class="multi-label">VIDEO</span></div>
      </div>
      <p class="kamusai-multi-arrow">⬇️</p>
      <div class="kamusai-multi-model-box">
        <span class="multi-emoji-large">🤖</span><br><span class="model-text">AI MODEL</span>
      </div>
      <p class="kamusai-multi-arrow2">⬇️</p>
      <div class="kamusai-multi-results">
        <div class="kamusai-result-item"><span class="multi-emoji">📄</span><br><span class="result-text">TEKS</span></div>
        <div class="kamusai-result-item"><span class="multi-emoji">🖼️</span><br><span class="result-text">GAMBAR</span></div>
      </div>
    </div>
  </div>
</div></div></div>

<style>
.kamusai-page{display:flex;flex-direction:column;align-items:center;min-height:100vh;background:#05050d;font-family:'Inter',sans-serif;color:#fff;padding-top:20px}
.kamusai-wrap{position:relative;overflow:visible;flex-shrink:0;margin-top:80px}
.kamusai-stage{position:relative;width:1080px;height:1920px;transform-origin:top left;overflow:hidden;background:#0D0D1A;border-radius:12px;box-shadow:0 0 60px rgba(0,191,255,0.15)}
.kamusai-sec{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;z-index:10}
.kamusai-multi-container{text-align:center;padding:40px;width:100%}
.kamusai-multi-title{font-size:120px;font-weight:900;color:#FFD77A;text-shadow:0 0 60px rgba(255,215,122,0.8);margin-bottom:20px}
.kamusai-multi-subtitle{font-size:56px;font-weight:700;color:#aaa;margin-bottom:80px}
.kamusai-multi-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:30px;margin-top:60px;width:100%}
.kamusai-multi-item{background:rgba(0,191,255,0.1);border:2px solid rgba(0,191,255,0.4);border-radius:24px;padding:30px;display:flex;flex-direction:column;align-items:center}
.multi-emoji{font-size:70px;display:block;margin-bottom:15px}
.multi-label{font-size:44px;font-weight:900;color:#fff}
.kamusai-multi-arrow,.kamusai-multi-arrow2{font-size:60px;color:#00BFFF;margin-top:30px;margin-bottom:30px;opacity:0}
.kamusai-multi-model-box{background:rgba(122,229,130,0.1);border:3px solid rgba(122,229,130,0.5);border-radius:30px;padding:40px;display:inline-block;margin-top:20px}
.multi-emoji-large{font-size:90px;display:block}
.model-text{font-size:56px;font-weight:900;color:#7AE582}
.kamusai-multi-results{display:flex;justify-content:center;gap:40px;margin-top:40px;width:100%}
.kamusai-result-item{background:rgba(255,215,122,0.1);border:2px solid rgba(255,215,122,0.4);border-radius:20px;padding:30px;display:flex;flex-direction:column;align-items:center}
.result-text{font-size:44px;font-weight:900;color:#FFD77A;margin-top:10px}
</style>
