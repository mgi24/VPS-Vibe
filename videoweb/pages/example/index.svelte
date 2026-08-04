<script>
  import { onMount, onDestroy } from 'svelte';
  import gsap from 'gsap';

  export let controller = null;

  let canvasEl;
  let wrapEl;
  let tl = null;
  let raf = null;
  let manualT = 0;
  let lastTs = 0;
  let duration = 1;
  let isPlaying = false;
  let speed = 1;

  const W = 1080;
  const H = 1920;

  function setupCanvasSize() {
    const scale = Math.min(window.innerWidth / W, window.innerHeight / H);
    if (wrapEl) { wrapEl.style.width = W * scale + 'px'; wrapEl.style.height = H * scale + 'px'; }
    if (canvasEl) { canvasEl.style.transform = `scale(${scale})`; }
  }

  function buildTimeline() {
    tl = gsap.timeline({ paused: true });
    // Hide all sections first, then show the main one at t=0
    document.querySelectorAll('.sec').forEach(el => { el.style.display = 'none'; el.style.opacity = '0'; });
    const mainSec = document.querySelector('.sec-main');
    if (mainSec) { mainSec.style.display = 'flex'; mainSec.style.opacity = '1'; }
    tl.fromTo('.main-text', { autoAlpha: 0, y: 40 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 0);
    tl.to('.sec-main', { autoAlpha: 0, duration: 0.3 }, 0.8);
    tl.duration(duration);
  }

  function tick(ts) {
    if (isPlaying) {
      const dt = (ts - lastTs) / 1000 * speed;
      lastTs = ts;
      manualT = Math.min(duration, manualT + dt);
      tl.seek(manualT);
      if (manualT >= duration) { isPlaying = false; }
    } else { lastTs = ts; }
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

    // Force show first section immediately (before timeline)
    const mainSec = document.querySelector('.sec-main');
    if (mainSec) { mainSec.style.display = 'flex'; mainSec.style.opacity = '1'; }

    tl.seek(0);
    raf = requestAnimationFrame(tick);
    if (controller) {
      controller.update((c) => ({ ...c, stageReady: true, W, H, duration, canvasEl, wrapEl, play, pause, playPause, seekTo, getTime, getDuration, isPlaying: isPlayingFn, setSpeed, stepFrame, reset, exportFrame: null, restoreLayout: null }));
    }
  });

  onDestroy(() => {
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', setupCanvasSize);
    if (tl) tl.kill();
    if (controller) controller.update((c) => ({ ...c, stageReady: false }));
  });
</script>

<div class="page">
  <div class="stage-wrap" bind:this={wrapEl}>
    <div class="stage" bind:this={canvasEl}>
      <div class="sec sec-main">
        <div class="main-text">parameter training LLM</div>
      </div>
    </div>
  </div>
</div>

<style>
  .page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #05050d; font-family: 'Inter', sans-serif; color: #fff; }
  .stage-wrap { position: relative; overflow: hidden; flex-shrink: 0; }
  .stage { position: relative; width: 1080px; height: 1920px; transform-origin: top left; overflow: hidden; background: #0D0D1A; border-radius: 12px; box-shadow: 0 0 60px rgba(0,191,255,0.15); }
  .sec { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; z-index: 10; }
  .main-text { font-size: 80px; font-weight: 900; text-align: center; color: #00BFFF; text-shadow: 0 0 40px rgba(0,191,255,0.6); padding: 40px; }
</style>
