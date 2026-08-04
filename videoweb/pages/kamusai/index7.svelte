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
  let duration = 3.4;
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

    // === OUTRO SECTION (0s – 3.4s) ===
    tl.set('.kamusai-outro', { display: 'flex', autoAlpha: 1 }, 0);

    tl.fromTo('.kamusai-outro-text-1', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'back.out(2)' }, 0);
    tl.fromTo('.kamusai-outro-text-2', { autoAlpha: 0, scale: 0.9 }, { autoAlpha: 1, scale: 1, duration: 0.4, ease: 'elastic.out(1, 0.6)' }, 0.8);

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

      <!-- SECTION 7: OUTRO -->
      <div class="kamusai-sec kamusai-outro">
        <div class="kamusai-outro-container">
          <p class="kamusai-outro-text-1" style="font-size:72px;font-weight:900;color:#00BFFF;text-shadow:0 0 40px rgba(0,191,255,0.6);text-align:center;">
            Part Lainnya
          </p>
          <p class="kamusai-outro-text-2" style="font-size:80px;font-weight:900;color:#7AE582;text-shadow:0 0 40px rgba(122,229,130,0.6);text-align:center;margin-top:40px;">
            Cek di Komen! 💬
          </p>
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

  /* OUTRO */
  .kamusai-outro-container { text-align: center; padding: 40px; width: 100%; }
</style>
