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
    tl.set('.kamusai-thinking', { display: 'flex', autoAlpha: 1 }, 0);

    tl.fromTo('.kamusai-think-title', { autoAlpha: 0, y: -30 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 0.2);
    tl.fromTo('.kamusai-think-subtitle', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.4 }, 0.5);

    tl.fromTo('.kamusai-think-ai-box', { autoAlpha: 0, scale: 0.6 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'back.out(2)' }, 1.3);
    tl.fromTo('.kamusai-think-brain-icon', { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.4, ease: 'elastic.out(1, 0.6)' }, 1.9);

    tl.fromTo('.kamusai-think-path-1', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.35 }, 3.4);
    tl.fromTo('.kamusai-think-path-2', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.35 }, 4.4);
    tl.fromTo('.kamusai-think-path-3', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.35 }, 5.4);

    tl.fromTo('.kamusai-think-highlight', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'elastic.out(1, 0.5)' }, 7.2);

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
        <div class="kamusai-think-container">
          <h1 class="kamusai-think-title">THINKING</h1>
          <p class="kamusai-think-subtitle">Mikir Dulu Sebelum Jawab</p>

          <div class="kamusai-think-diagram">
            <div class="kamusai-think-ai-box">
              <span class="icon-emoji kamusai-think-brain-icon" style="font-size:120px;">🧠</span>
            </div>

            <div class="kamusai-think-paths">
              <div class="kamusai-think-path kamusai-think-path-1">✓ Jawaban A (prob. 45%)</div>
              <div class="kamusai-think-path kamusai-think-path-2">✓ Jawaban B (prob. 35%)</div>
              <div class="kamusai-think-path kamusai-think-path-3">✓ Jawaban C (prob. 20%)</div>
            </div>
          </div>

          <p class="kamusai-think-highlight">PROBABILITAS PALING TINGGI</p>
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

  /* THINKING */
  .kamusai-think-container { text-align: center; padding: 40px; width: 100%; }
  .kamusai-think-title { font-size: 130px; font-weight: 900; color: #FF5252; text-shadow: 0 0 60px rgba(255,82,82,0.8); margin-bottom: 20px; }
  .kamusai-think-subtitle { font-size: 56px; font-weight: 700; color: #aaa; margin-bottom: 100px; }

  .kamusai-think-diagram { display: flex; align-items: center; justify-content: center; gap: 40px; margin-top: 80px; width: 100%; box-sizing: border-box; }

  .kamusai-think-ai-box {
    background: rgba(255,215,122,0.1);
    border: 3px solid rgba(255,215,122,0.6);
    border-radius: 50%;
    width: 240px;
    height: 240px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .icon-emoji { font-size: 80px; display: block; margin-bottom: 20px; }

  .kamusai-think-paths { display: flex; flex-direction: column; gap: 20px; text-align: left; min-width: 350px; max-width: 450px; }

  .kamusai-think-path {
    font-size: 52px;
    font-weight: 700;
    color: #fff;
    background: rgba(0,191,255,0.1);
    border: 2px solid rgba(0,191,255,0.3);
    border-radius: 16px;
    padding: 24px 36px;
    opacity: 0;
  }

  .kamusai-think-path-1 { color: #7AE582; border-color: rgba(122,229,130,0.5); }
  .kamusai-think-path-2 { color: #FFD77A; border-color: rgba(255,215,122,0.5); }
  .kamusai-think-path-3 { color: #aaa; border-color: rgba(170,170,170,0.3); }

  .kamusai-think-highlight {
    margin-top: 80px;
    font-size: 72px;
    font-weight: 900;
    color: #FFD77A;
    text-shadow: 0 0 40px rgba(255,215,122,0.6);
    border-bottom: 4px solid #FFD77A;
  }
</style>
