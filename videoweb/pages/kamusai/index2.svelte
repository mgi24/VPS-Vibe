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
  let duration = 7.8;
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

    // === LLM SECTION (0s – 7.8s) ===
    tl.set('.kamusai-llm', { display: 'flex', autoAlpha: 1 }, 0);

    tl.fromTo('.kamusai-llm-title', { autoAlpha: 0, y: -30 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 0);
    tl.fromTo('.kamusai-llm-subtitle', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.4 }, 0.3);

    tl.fromTo('.kamusai-llm-input-box', { autoAlpha: 0, x: -60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 0.7);
    tl.fromTo('.kamusai-llm-arrow-right', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.3 }, 1.2);
    tl.fromTo('.kamusai-llm-model-box', { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'back.out(2)' }, 1.5);
    tl.fromTo('.kamusai-llm-arrow-left', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.3 }, 2.0);
    tl.fromTo('.kamusai-llm-output-box', { autoAlpha: 0, x: 60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 2.3);

    tl.fromTo('.kamusai-llm-highlight', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.4, ease: 'elastic.out(1, 0.5)' }, 3.9);

    tl.set('.kamusai-mini-flow', { autoAlpha: 0, display: 'flex' }, 3.2);
    gsap.set('.kamusai-mini-box', { scale: 0 });
    tl.to('.kamusai-mini-text-in', { scale: 1, duration: 0.25, ease: 'back.out(2)' }, 3.2);
    tl.to('.kamusai-mini-arrow', { autoAlpha: 1, duration: 0.15 }, 3.4);
    tl.to('.kamusai-mini-robot', { scale: 1, duration: 0.3, ease: 'back.out(2)' }, 3.55);
    tl.to('.kamusai-mini-arrow2', { autoAlpha: 1, duration: 0.15 }, 3.85);
    tl.to('.kamusai-mini-text-out', { scale: 1, duration: 0.25, ease: 'back.out(2)' }, 4.0);

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

      <!-- SECTION 2: LLM -->
      <div class="kamusai-sec kamusai-llm">
        <div class="kamusai-llm-container">
          <h1 class="kamusai-llm-title">LLM</h1>
          <p class="kamusai-llm-subtitle">Large Language Model</p>

          <div class="kamusai-llm-diagram">
            <div class="kamusai-llm-input-box">
              <span class="icon-emoji">⌨️</span>
              <br>
              <span class="label-text">TEKS</span>
            </div>

            <div class="kamusai-llm-arrow-right">→</div>

            <div class="kamusai-llm-model-box">
              <span class="icon-emoji">🤖</span>
            </div>

            <div class="kamusai-llm-arrow-left">→</div>

            <div class="kamusai-llm-output-box">
              <span class="icon-emoji">📄</span>
              <br>
              <span class="label-text">TEKS</span>
            </div>
          </div>

          <p class="kamusai-llm-highlight">TEKS DOANG YA</p>

          <!-- Mini flow: text → robot → text (smaller scale) -->
          <div class="kamusai-mini-flow" style="position:absolute;bottom:30px;left:50%;transform:translateX(-50%);display:none;align-items:center;gap:4px;">
            <div class="kamusai-mini-box kamusai-mini-text-in">⌨️</div>
            <span class="kamusai-mini-arrow" style="opacity:0;font-size:16px;color:#00BFFF;">→</span>
            <div class="kamusai-mini-box kamusai-mini-robot">🤖</div>
            <span class="kamusai-mini-arrow2" style="opacity:0;font-size:16px;color:#7AE582;">→</span>
            <div class="kamusai-mini-box kamusai-mini-text-out">📄</div>
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

  /* LLM */
  .kamusai-llm-container { text-align: center; padding: 40px; width: 100%; }
  .kamusai-llm-title { font-size: 140px; font-weight: 900; color: #00BFFF; text-shadow: 0 0 60px rgba(0,191,255,0.8); margin-bottom: 20px; }
  .kamusai-llm-subtitle { font-size: 64px; font-weight: 700; color: #aaa; margin-bottom: 120px; }

  .kamusai-llm-diagram { display: flex; align-items: center; justify-content: center; gap: 20px; margin-top: 80px; width: 100%; box-sizing: border-box; }

  .kamusai-llm-input-box, .kamusai-llm-model-box, .kamusai-llm-output-box {
    background: rgba(0,191,255,0.1);
    border: 2px solid rgba(0,191,255,0.4);
    border-radius: 24px;
    padding: 40px 30px;
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
  }

  .kamusai-llm-input-box, .kamusai-llm-output-box { width: 260px; }

  .kamusai-llm-model-box {
    background: rgba(122,229,130,0.1);
    border-color: rgba(122,229,130,0.5);
    width: 220px;
  }

  .icon-emoji { font-size: 80px; display: block; margin-bottom: 20px; }
  .label-text { font-size: 48px; font-weight: 900; color: #fff; }

  .kamusai-llm-arrow-right, .kamusai-llm-arrow-left {
    font-size: 72px;
    color: #00BFFF;
    font-weight: 900;
  }

  .kamusai-llm-highlight {
    margin-top: 100px;
    font-size: 80px;
    font-weight: 900;
    color: #FFD77A;
    text-shadow: 0 0 40px rgba(255,215,122,0.6);
    border-bottom: 4px solid #FFD77A;
  }

  .kamusai-mini-flow { z-index: 15; padding: 12px; background: rgba(0,0,0,0.4); border-radius: 12px; gap: 4px; }
  .kamusai-mini-box { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; font-size: 20px; background: rgba(0,191,255,0.1); border: 2px solid rgba(0,191,255,0.4); border-radius: 8px; }
  .kamusai-mini-robot { background: rgba(122,229,130,0.1); border-color: rgba(122,229,130,0.5); font-size: 24px; }
  .kamusai-mini-text-out { background: rgba(255,215,122,0.1); border-color: rgba(255,215,122,0.4); }
</style>
