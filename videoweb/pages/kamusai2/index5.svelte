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
  let duration = 12.3;
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

    // === THINKING SECTION (0s – 12.3s) ===
    tl.set('.kamusai-thinking', { autoAlpha: 1, display: 'flex' }, 0);
    document.querySelectorAll('.kamusai-sec').forEach(el => { if (!el.classList.contains('kamusai-thinking')) { el.style.display = 'none'; } });
    tl.fromTo('.kamusai-think-title', { autoAlpha: 0, y: -40 }, { autoAlpha: 1, y: 0, duration: 0.6, ease: 'back.out(2)' }, 0);
    tl.fromTo('.kamusai-think-subtitle', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.4 }, 0.5);

    const steps = document.querySelectorAll('.kamusai-thinking-step');
    gsap.set(steps, { autoAlpha: 0, x: -30 });
    tl.to(steps, { autoAlpha: 1, x: 0, duration: 0.4, ease: 'power2.out', stagger: 0.5 }, 1.0);

    const loadingBar = document.querySelector('.kamusi-loading-bar');
    const fill = document.querySelector('.loading-fill');
    if (fill) gsap.set(fill, { width: '0%' });
    tl.to(fill, { width: '100%', duration: 8, ease: 'power2.inOut' }, 3.0);

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

      <!-- SECTION 5: THINKING -->
      <div class="kamusai-sec kamusai-thinking">
        <div class="kamusi-thinking-container">
          <h1 class="kamusai-think-title">THINKING</h1>
          <p class="kamusai-think-subtitle">AI lagi mikir...</p>
          <div class="kamusai-think-process">
            <div class="kamusai-thinking-step active"><span class="step-icon">🧠</span><br><span class="step-text">MEMAHAMI INPUT</span></div>
            <div class="kamusai-thinking-step"><span class="step-icon">⚙️</span><br><span class="step-text">PROSES DATA</span></div>
            <div class="kamusai-thinking-step"><span class="step-icon">🔍</span><br><span class="step-text">CARI SOLUSI</span></div>
            <div class="kamusai-thinking-step"><span class="step-icon">✅</span><br><span class="step-text">HASIL SIAP!</span></div>
          </div>
          <div class="kamusi-loading-bar">
            <div class="loading-fill"></div>
          </div>
        </div>
      </div>

    </div>
  </div>
</div>

<style>
  .kamusai-page { display: flex; flex-direction: column; align-items: center; min-height: 100vh; background: #05050d; font-family: 'Inter', sans-serif; color: #fff; padding-top: 20px; }
  .kamusai-wrap { position: relative; overflow: visible; flex-shrink: 0; margin-top: 80px; }
  .kamusai-stage { position: relative; width: 1080px; height: 1920px; transform-origin: top left; overflow: hidden; background: #0D0D1A; border-radius: 12px; box-shadow: 0 0 60px rgba(0,191,255,0.15); }
  .kamusai-sec { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; z-index: 10; }
  .kamusai-thinking-container { text-align: center; padding: 40px; width: 100%; }
  .kamusai-think-title { font-size: 130px; font-weight: 900; color: #FF6B6B; text-shadow: 0 0 60px rgba(255,107,107,0.8); margin-bottom: 20px; }
  .kamusai-think-subtitle { font-size: 56px; font-weight: 700; color: #aaa; margin-bottom: 80px; }
  .kamusai-thinking-step { background: rgba(255,107,107,0.1); border: 2px solid rgba(255,107,107,0.4); border-radius: 20px; padding: 20px; margin-bottom: 20px; display: flex; align-items: center; justify-content: center; width: 80%; margin-left: auto; margin-right: auto; }
  .kamusai-thinking-step.active { background: rgba(255,107,107,0.2); border-color: #FF6B6B; }
  .step-icon { font-size: 60px; display: inline-block; margin-right: 20px; }
  .step-text { font-size: 48px; font-weight: 900; color: #fff; }
  .kamusi-loading-bar { width: 70%; height: 16px; background: rgba(255,107,107,0.2); border-radius: 8px; margin-top: 60px; overflow: hidden; }
  .loading-fill { height: 100%; background: linear-gradient(90deg, #FF6B6B, #FFD77A); border-radius: 8px; width: 0%; }
</style>
