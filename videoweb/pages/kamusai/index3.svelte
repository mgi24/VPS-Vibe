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
  let duration = 15.66;
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

    // === MULTIMODAL SECTION (0s – 15.66s) ===
    tl.set('.kamusai-multimodal', { display: 'flex', autoAlpha: 1 }, 0);

    tl.fromTo('.kamusai-mm-title', { autoAlpha: 0, y: -30 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 0);
    tl.fromTo('.kamusai-mm-subtitle', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.4 }, 0.3);

    tl.fromTo('.kamusai-mm-text-only', { autoAlpha: 0, x: -60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 0.9);
    tl.fromTo('.kamusai-mm-x-icon', { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.3, ease: 'back.out(2)' }, 1.4);
    tl.fromTo('.kamusai-mm-image-box', { autoAlpha: 0, x: -60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 1.9);
    tl.fromTo('.kamusai-mm-plus-icon', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.3 }, 2.3);
    tl.fromTo('.kamusai-mm-audio-box', { autoAlpha: 0, x: 60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 2.7);

    tl.fromTo('.kamusai-mm-highlight', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'elastic.out(1, 0.5)' }, 5.1);
    tl.fromTo('.kamusai-mm-base64', { autoAlpha: 0, y: 30 }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'back.out(2)' }, 9.1);

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

      <!-- SECTION 3: MULTIMODAL -->
      <div class="kamusai-sec kamusai-multimodal">
        <div class="kamusai-mm-container">
          <h1 class="kamusai-mm-title">MULTIMODAL</h1>
          <p class="kamusai-mm-subtitle">Lebih dari Sekedar Teks</p>

          <div class="kamusai-mm-diagram">
            <div class="kamusai-mm-box kamusai-mm-text-only">
              <span class="icon-emoji">⌨️</span>
              <span class="label-text">TEKS DOANG</span>
            </div>

            <span class="kamusai-mm-x-icon" style="font-size:64px;color:#ff5252;">✖</span>

            <div class="kamusai-mm-diagram-right">
              <div class="kamusai-mm-box kamusai-mm-image-box">
                <span class="icon-emoji">🖼️</span>
                <span class="label-text">GAMBAR</span>
              </div>

              <span class="kamusai-mm-plus-icon" style="font-size:48px;color:#7AE582;margin:16px 0;display:block;text-align:center;">+</span>

              <div class="kamusai-mm-box kamusai-mm-audio-box">
                <span class="icon-emoji">🎤</span>
                <span class="label-text">AUDIO</span>
              </div>
            </div>
          </div>

          <p class="kamusai-mm-highlight">BISA GAMBAR + AUDIO!</p>
          <p class="kamusai-mm-base64" style="color:#aaa;font-size:52px;margin-top:60px;">Dikonversi jadi Base 64</p>
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

  /* MULTIMODAL */
  .kamusai-mm-container { text-align: center; padding: 40px; width: 100%; }
  .kamusai-mm-title { font-size: 130px; font-weight: 900; color: #7AE582; text-shadow: 0 0 60px rgba(122,229,130,0.8); margin-bottom: 20px; }
  .kamusai-mm-subtitle { font-size: 56px; font-weight: 700; color: #aaa; margin-bottom: 100px; }

  .kamusai-mm-diagram { display: flex; align-items: center; justify-content: center; gap: 20px; margin-top: 80px; width: 100%; box-sizing: border-box; }

  .kamusai-mm-box {
    background: rgba(0,191,255,0.1);
    border: 2px solid rgba(0,191,255,0.4);
    border-radius: 24px;
    padding: 40px 30px;
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
    width: 260px;
  }

  .kamusai-mm-image-box { background: rgba(0,191,255,0.1); border-color: rgba(0,191,255,0.4); }
  .kamusai-mm-audio-box { background: rgba(255,215,122,0.1); border-color: rgba(255,215,122,0.4); }

  .kamusai-mm-diagram-right { display: flex; flex-direction: column; align-items: center; gap: 0; }

  .icon-emoji { font-size: 80px; display: block; margin-bottom: 20px; }
  .label-text { font-size: 48px; font-weight: 900; color: #fff; }

  .kamusai-mm-highlight {
    margin-top: 80px;
    font-size: 76px;
    font-weight: 900;
    color: #FFD77A;
    text-shadow: 0 0 40px rgba(255,215,122,0.6);
    border-bottom: 4px solid #FFD77A;
  }

  .kamusai-mm-base64 { font-size: 52px; color: #aaa; margin-top: 60px; }
</style>
