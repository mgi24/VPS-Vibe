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
    tl.set('.kamusai-input', { display: 'flex', autoAlpha: 1 }, 0);

    tl.fromTo('.kamusai-input-title', { autoAlpha: 0, y: -30 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 0);
    tl.fromTo('.kamusai-input-question', { autoAlpha: 0, scale: 0.9 }, { autoAlpha: 1, scale: 1, duration: 0.4 }, 0.34);

    tl.fromTo('.kamusai-input-img-side', { autoAlpha: 0, x: -60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 1.24);
    tl.fromTo('.kamusai-input-audio-side', { autoAlpha: 0, x: 60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 1.64);

    tl.fromTo('.kamusai-transform-arrow-1', { autoAlpha: 0, scaleX: 0.3 }, { autoAlpha: 1, scaleX: 1, duration: 0.25, ease: 'back.out(3)' }, 2.94);
    tl.fromTo('.kamusai-transform-label', { autoAlpha: 0, y: -10 }, { autoAlpha: 1, y: 0, duration: 0.3 }, 3.14);
    tl.fromTo('.kamusai-transform-arrow-2', { autoAlpha: 0, scaleX: 0.3 }, { autoAlpha: 1, scaleX: 1, duration: 0.25, ease: 'back.out(3)' }, 3.34);

    tl.to('.kamusai-transform-arrow-1', { autoAlpha: 0.3, duration: 0.15 }, 3.94);
    tl.to('.kamusai-transform-arrow-1', { autoAlpha: 1, duration: 0.15 }, 4.09);
    tl.to('.kamusai-transform-arrow-2', { autoAlpha: 0.3, duration: 0.15 }, 4.24);
    tl.to('.kamusai-transform-arrow-2', { autoAlpha: 1, duration: 0.15 }, 4.39);

    tl.fromTo('.kamusai-input-result-box', { autoAlpha: 0, scale: 0.5, y: 30 }, { autoAlpha: 1, scale: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 4.94);
    tl.fromTo('.kamusai-input-highlight', { autoAlpha: 0, scale: 0.85 }, { autoAlpha: 1, scale: 1, duration: 0.45, ease: 'elastic.out(1, 0.6)' }, 5.44);

    tl.fromTo('.kamusai-base64-area', { autoAlpha: 0, y: 30 }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'back.out(2)' }, 5.94);

    tl.fromTo('.kamusai-base64-line-1', { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'none' }, 6.74);
    tl.set('.kamusai-typing-cursor', { display: 'none' }, 7.24);
    tl.set('.kamusai-cursor-2', { display: 'inline', autoAlpha: 1 }, 7.24);
    tl.fromTo('.kamusai-base64-line-2', { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'none' }, 7.74);
    tl.set('.kamusai-cursor-2', { display: 'none' }, 8.24);
    tl.set('.kamusai-cursor-3', { display: 'inline', autoAlpha: 1 }, 8.24);
    tl.fromTo('.kamusai-base64-line-3', { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'none' }, 8.74);
    tl.set('.kamusai-cursor-3', { display: 'none' }, 9.24);
    tl.set('.kamusai-cursor-4', { display: 'inline', autoAlpha: 1 }, 9.24);
    tl.fromTo('.kamusai-base64-line-4', { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'none' }, 9.74);
    tl.set('.kamusai-cursor-4', { display: 'none' }, 10.24);
    tl.set('.kamusai-cursor-5', { display: 'inline', autoAlpha: 1 }, 10.24);
    tl.fromTo('.kamusai-base64-line-5', { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'none' }, 10.74);

    tl.set('.kamusai-cursor-5', { autoAlpha: 0 }, 11.94);
    tl.fromTo('.kamusai-input-base64-highlight', { autoAlpha: 0, scaleX: 0 }, { autoAlpha: 1, scaleX: 1, duration: 0.6, ease: 'steps(8)' }, 11.94);

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
        <div class="kamusai-input-container">
          <h1 class="kamusai-input-title">INPUT</h1>
          <p class="kamusai-input-question">Gimana Cara Inputnya?</p>

          <!-- Diagram: gambar → transformasi → teks / audio → teks -->
          <div class="kamusai-input-diagram">
            <!-- Kiri: Gambar -->
            <div class="kamusai-input-side kamusai-input-img-side">
              <span class="icon-emoji kamusai-input-img-icon" style="font-size:120px;">🖼️</span>
              <p class="kamusai-input-label kamusai-input-img-label" style="margin-top:16px;font-size:48px;color:#00BFFF;">GAMBAR</p>
            </div>

            <!-- Tengah: panah transformasi berkedip -->
            <div class="kamusai-input-transform">
              <span class="kamusai-transform-arrow kamusai-transform-arrow-1" style="font-size:56px;color:#00BFFF;">→</span>
              <p class="kamusai-transform-label" style="font-size:32px;color:#FFD77A;margin-top:8px;text-align:center;">transform</p>
              <span class="kamusai-transform-arrow kamusai-transform-arrow-2" style="font-size:56px;color:#7AE582;">→</span>
            </div>

            <!-- Kanan: Audio -->
            <div class="kamusai-input-side kamusai-input-audio-side">
              <span class="icon-emoji kamusai-input-audio-icon" style="font-size:120px;">🎤</span>
              <p class="kamusai-input-label kamusai-input-audio-label" style="margin-top:16px;font-size:48px;color:#7AE582;">AUDIO</p>
            </div>
          </div>

          <!-- Hasil: teks -->
          <div class="kamusai-input-result-box">
            <span class="icon-emoji kamusai-input-result-icon" style="font-size:100px;">📄</span>
            <p class="kamusai-input-result-label" style="font-size:56px;font-weight:900;color:#fff;margin-top:16px;">TEKS</p>
          </div>

          <!-- Highlight -->
          <p class="kamusai-input-highlight">DIBIKIN TEKS GITU YA!</p>

          <!-- Base 64 code typing area -->
          <div class="kamusai-base64-area kamusai-base64-typing">
            <span class="kamusai-typing-cursor" style="color:#7AE582;">▌</span><span class="kamusai-base64-line kamusai-base64-line-1" style="opacity:0;">data:image/png;base64,iVBORw0KGgoAAAANSU...</span>
            <br>
            <span class="kamusai-typing-cursor kamusai-cursor-2" style="color:#7AE582;display:none;">▌</span><span class="kamusai-base64-line kamusai-base64-line-2" style="opacity:0;">data:audio/mp3;base64,UklGRi9vTWFu...</span>
            <br>
            <span class="kamusai-typing-cursor kamusai-cursor-3" style="color:#7AE582;display:none;">▌</span><span class="kamusai-base64-line kamusai-base64-line-3" style="opacity:0;">base64://eyJ0eXAiOiJKV1QiLCJhbGc...</span>
            <br>
            <span class="kamusai-typing-cursor kamusai-cursor-4" style="color:#7AE582;display:none;">▌</span><span class="kamusai-base64-line kamusai-base64-line-4" style="opacity:0;">// AI encoding pipeline</span>
            <br>
            <span class="kamusai-typing-cursor kamusai-cursor-5" style="color:#7AE582;display:none;">▌</span><span class="kamusai-base64-line kamusai-base64-line-5" style="opacity:0;">→ converting multimodal → text tokens</span>
          </div>

          <!-- Base 64 typing highlight -->
          <p class="kamusai-input-base64-highlight" style="font-size:72px;font-weight:900;color:#FFD77A;text-shadow:0 0 30px rgba(255,215,122,0.6);">BASE 64</p>
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

  /* INPUT */
  .kamusai-input-container { text-align: center; padding: 40px; width: 100%; display: flex; flex-direction: column; align-items: center; }
  .kamusai-input-title { font-size: 130px; font-weight: 900; color: #FFD77A; text-shadow: 0 0 60px rgba(255,215,122,0.8); margin-bottom: 20px; }
  .kamusai-input-question { font-size: 56px; font-weight: 700; color: #aaa; margin-bottom: 60px; }

  .kamusai-input-diagram { display: flex; align-items: center; justify-content: center; gap: 24px; width: 100%; box-sizing: border-box; }

  /* Side boxes (gambar / audio) */
  .kamusai-input-side {
    background: rgba(0,191,255,0.08);
    border: 2px solid rgba(0,191,255,0.35);
    border-radius: 24px;
    padding: 40px 36px;
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
    width: 260px;
  }

  .kamusai-input-audio-side { background: rgba(122,229,130,0.08); border-color: rgba(122,229,130,0.35); }

  /* Transform area (tengah) */
  .kamusai-input-transform {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .kamusai-transform-arrow { font-size: 56px; font-weight: 900; opacity: 0; }

  .kamusai-transform-label {
    font-size: 32px;
    color: #FFD77A;
    margin-top: 8px;
    text-align: center;
    opacity: 0;
    letter-spacing: 2px;
  }

  /* Hasil teks */
  .kamusai-input-result-box {
    background: rgba(122,229,130,0.1);
    border: 3px solid rgba(122,229,130,0.5);
    border-radius: 24px;
    padding: 40px 48px;
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-top: 60px;
    opacity: 0;
    transform: scale(0.7);
  }

  .kamusai-input-result-icon { font-size: 100px; }
  .kamusai-input-result-label { font-size: 56px; font-weight: 900; color: #fff; margin-top: 16px; }

  /* Highlight */
  .kamusai-input-highlight {
    margin-top: 80px;
    font-size: 72px;
    font-weight: 900;
    color: #00BFFF;
    text-shadow: 0 0 40px rgba(0,191,255,0.6);
    border-bottom: 4px solid #00BFFF;
  }

  /* Base 64 typing area */
  .kamusai-base64-area {
    margin-top: 70px;
    width: 85%;
    max-width: 800px;
    min-height: 160px;
    position: relative;
    background: rgba(0,0,0,0.35);
    border: 2px solid rgba(0,191,255,0.2);
    border-radius: 16px;
    padding: 24px 28px;
    opacity: 0;
    font-family: 'Courier New', monospace;
    color: #7AE582;
    line-height: 1.8;
  }

  .kamusai-base64-typing {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 30px;
  }

  .kamusai-typing-cursor {
    animation: kamusai-cursor-blink 0.8s step-end infinite;
  }

  .kamusai-cursor-2, .kamusai-cursor-3, .kamusai-cursor-4, .kamusai-cursor-5 {
    display: none !important;
  }

  @keyframes kamusai-cursor-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }

  .kamusai-base64-line {
    white-space: nowrap;
    font-size: 30px;
    line-height: 1.8;
  }

  /* Base 64 typing highlight */
  .kamusai-input-base64-highlight {
    margin-top: 50px;
    opacity: 0;
    display: inline-block;
  }
</style>
