<script>
  import { onMount, onDestroy } from 'svelte';
  import gsap from 'gsap';

  export let controller = null;
  export let showFrame = -1;

  let canvasEl;
  let wrapEl;
  let tl = null;
  let raf = null;
  let manualT = 0;
  let lastTs = 0;
  let duration = 13.34;
  let isPlaying = false;
  let speed = 1;

  const W = 1080;
  const H = 1920;

  function setupCanvasSize() {
    const isPreview = showFrame >= 0 && isFinite(showFrame);
    const availableW = window.innerWidth;
    const availableH = isPreview ? window.innerHeight : window.innerHeight - 160;

    const scale = Math.min(availableW / W, availableH / H) * (isPreview ? 0.95 : 0.92);

    if (!isPreview) {
      document.querySelector('.kamusai-page')?.style.removeProperty('padding-top');
      wrapEl?.style.removeProperty('margin-top');
    } else {
      const page = document.querySelector('.kamusai-page');
      if (page) { page.style.paddingTop = '0'; page.style.marginTop = '0'; }
      if (wrapEl) wrapEl.style.marginTop = '0';
      if (canvasEl) canvasEl.style.overflow = '';
    }

    if (wrapEl) { wrapEl.style.width = W * scale + 'px'; wrapEl.style.height = H * scale + 'px'; }
    if (canvasEl) canvasEl.style.transform = `scale(${scale})`;
  }

  function buildTimeline() {
    tl = gsap.timeline({ paused: true });

    document.querySelectorAll('.kamusai-sec').forEach(el => { el.style.display = 'none'; el.style.opacity = '0'; });

    // === INPUT SECTION (0s – 13.34s) ===
    tl.set('.kamusai-input', { autoAlpha: 1, display: 'flex' }, 0);
    document.querySelectorAll('.kamusai-sec').forEach(el => { if (!el.classList.contains('kamusai-input')) { el.style.display = 'none'; } });
    tl.fromTo('.kamusai-input-title', { autoAlpha: 0, y: -40 }, { autoAlpha: 1, y: 0, duration: 0.6, ease: 'back.out(2)' }, 0);
    tl.fromTo('.kamusai-input-subtitle', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.4 }, 0.5);
    const optItems = document.querySelectorAll('.kamusai-option-item');
    gsap.set(optItems, { autoAlpha: 0, y: 30 });
    tl.to(optItems, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'power2.out', stagger: 0.2 }, 1.0);
    const demoBox = document.querySelector('.kamusai-input-demo-box');
    if (demoBox) gsap.set(demoBox, { autoAlpha: 0, scale: 0.8 });
    tl.fromTo('.demo-content', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.5 }, 2.0);
    if (demoBox) tl.to(demoBox, { autoAlpha: 1, scale: 1, duration: 0.6, ease: 'back.out(2)' }, 2.3);
    tl.fromTo('.kamusai-input-hint', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.4 }, 3.5);

    tl.duration(duration);
  }

  function tick(ts) {
    if (isPlaying) {
      const dt = (ts - lastTs) / 1000 * speed;
      lastTs = ts;
      manualT = Math.min(duration, manualT + dt);
      tl.seek(manualT);
      if (manualT >= duration) { isPlaying = false; }
    } else {
      lastTs = ts;
      if (showFrame && showFrame >= 0) {
        cancelAnimationFrame(raf);
        raf = null;
        return;
      }
    }
    raf = requestAnimationFrame(tick);
  }

  function play() {
    if (manualT >= duration) manualT = 0;
    isPlaying = true;
    lastTs = performance.now();
  }
  function pause() { isPlaying = false; }
  function playPause() { isPlaying ? pause() : play(); }
  function seekTo(t) { t = Math.max(0, Math.min(duration, t)); manualT = t; tl.seek(t); }
  function getTime() { return manualT; }
  function getDuration() { return duration; }
  function isPlayingFn() { return isPlaying; }
  function setSpeed(s) { speed = s || 1; }
  function stepFrame(dir) {
    const fpsVal = 24;
    const frameT = manualT + (dir / fpsVal);
    seekTo(frameT);
  }
  function reset() { manualT = 0; isPlaying = false; tl.seek(0); }

  onMount(() => {
    buildTimeline();

    setupCanvasSize();
    window.addEventListener('resize', setupCanvasSize);

    if (showFrame >= 0 && isFinite(showFrame)) {
      const previewTime = Math.min(showFrame / 24, duration - 0.01);
      console.log('Preview mode, frame:', showFrame, 'time:', previewTime.toFixed(3), 's');

      requestAnimationFrame(() => {
        tl.render(previewTime, true);
        gsap.ticker.pause();
        raf = null;

        if (controller) {
          controller.update((c) => ({ ...c, stageReady: true, W, H, duration, canvasEl, wrapEl, play, pause, playPause, seekTo, getTime, getDuration, isPlaying: isPlayingFn, setSpeed, stepFrame, reset, exportFrame: null, restoreLayout: null }));
        }
      });

      return;
    }

    raf = requestAnimationFrame(tick);

    if (controller) {
      controller.update((c) => ({ ...c, stageReady: true, W, H, duration, canvasEl, wrapEl, play, pause, playPause, seekTo, getTime, getDuration, isPlaying: isPlayingFn, setSpeed, stepFrame, reset }));
    }
  });

  onDestroy(() => {
    cancelAnimationFrame(raf);
    if (tl) tl.kill();
    window.removeEventListener('resize', setupCanvasSize);
  });
</script>

<div class="kamusai-page">
  <div class="kamusai-wrap" bind:this={wrapEl}>
    <div class="kamusai-stage" bind:this={canvasEl}>

      <!-- SECTION 4: INPUT -->
      <div class="kamusai-sec kamusai-input">
        <div class="kamusi-input-container">
          <h1 class="kamusai-input-title">INPUT</h1>
          <p class="kamusai-input-subtitle">Apa yang mau kamu kasih ke AI?</p>
          <div class="kamusai-input-options">
            <div class="kamusai-option-item" data-type="text"><span class="option-emoji">📝</span><br><span class="option-text">TEKS</span></div>
            <div class="kamusai-option-item" data-type="image"><span class="option-emoji">🖼️</span><br><span class="option-text">GAMBAR</span></div>
            <div class="kamusai-option-item" data-type="audio"><span class="option-emoji">🎵</span><br><span class="option-text">SUARA</span></div>
            <div class="kamusai-option-item" data-type="video"><span class="option-emoji">🎥</span><br><span class="option-text">VIDEO</span></div>
          </div>
          <div class="kamusi-input-demo-box">
            <p class="demo-label">DEMO:</p>
            <div class="demo-content">
              <span class="demo-emoji">📝</span><br>
              <span class="demo-text">"Buatkan gambar kucing"</span>
            </div>
          </div>
          <p class="kamusai-input-hint">AI bakal proses ini... ⬇️</p>
        </div>
      </div>

    </div>
  </div>
</div>

<style>
  .kamusai-page{display:flex;flex-direction:column;align-items:center;min-height:100vh;background:#05050d;font-family:'Inter',sans-serif;color:#fff;padding-top:20px}
  .kamusai-wrap{position:relative;overflow:visible;flex-shrink:0;margin-top:80px}
  .kamusai-stage{position:relative;width:1080px;height:1920px;transform-origin:top left;overflow:hidden;background:#0D0D1A;border-radius:12px;box-shadow:0 0 60px rgba(0,191,255,0.15)}
  .kamusai-sec{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;z-index:10}
  .kamusi-input-container{text-align:center;padding:40px;width:100%}
  .kamusai-input-title{font-size:130px;font-weight:900;color:#7AE582;text-shadow:0 0 60px rgba(122,229,130,0.8);margin-bottom:20px}
  .kamusai-input-subtitle{font-size:52px;font-weight:700;color:#aaa;margin-bottom:80px}
  .kamusai-input-options{display:flex;justify-content:center;gap:40px;margin-top:60px;width:100%}
  .kamusai-option-item{background:rgba(0,191,255,0.1);border:3px solid rgba(0,191,255,0.4);border-radius:24px;padding:30px 20px;display:flex;flex-direction:column;align-items:center;width:180px}
  .option-emoji{font-size:70px;display:block;margin-bottom:15px}
  .option-text{font-size:40px;font-weight:900;color:#fff}
  .kamusi-input-demo-box{background:rgba(122,229,130,0.08);border:2px solid rgba(122,229,130,0.5);border-radius:24px;padding:30px;margin-top:60px;width:70%;display:inline-block;text-align:center}
  .demo-label{font-size:36px;color:#7AE582;font-weight:700;margin-bottom:20px}
  .demo-content{background:rgba(0,191,255,0.05);border-radius:16px;padding:20px}
  .demo-emoji{font-size:60px;display:block;margin-bottom:10px}
  .demo-text{font-size:48px;color:#fff;font-weight:700}
  .kamusai-input-hint{font-size:48px;color:#FFD77A;margin-top:40px;opacity:0}
</style>
