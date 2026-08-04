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
  let duration = 7.1;
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

    // === THINKING OFF SECTION (0s – 7.1s) ===
    tl.set('.kamusai-thinking-off', { display: 'flex', autoAlpha: 1 }, 0);

    tl.fromTo('.kamusai-split-line', { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: 'power2.inOut' }, 0);

    tl.fromTo('.kamusai-side-label-on', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.3, ease: 'back.out(2)' }, 0.3);
    tl.fromTo('.kamusai-side-label-off', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.3, ease: 'back.out(2)' }, 0.6);

    // === KIRI: Thinking ON chain-of-thought ===
    tl.fromTo('.kamusai-think-cot-q', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'back.out(2)' }, 1.3);

    tl.fromTo('.kamusai-think-cot-thinking', { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 2.1);

    tl.fromTo('.kamusai-think-cot-ans', { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'back.out(2)' }, 3.1);

    tl.fromTo('.kamusai-think-check', { scale: 0 }, { scale: 1, duration: 0.3, ease: 'back.out(3)' }, 3.7);

    // === KANAN: Thinking OFF langsung jawab ===
    tl.fromTo('.kamusai-think-raw-q', { autoAlpha: 0, x: 20 }, { autoAlpha: 1, x: 0, duration: 0.4, ease: 'power2.out' }, 2.3);

    tl.fromTo('.kamusai-think-raw-ans', { autoAlpha: 0, scale: 0.7 }, { autoAlpha: 1, scale: 1, duration: 0.45, ease: 'back.out(2)' }, 3.3);

    tl.fromTo('.kamusai-think-warn', { autoAlpha: 0, y: -10 }, { autoAlpha: 1, y: 0, duration: 0.3, ease: 'back.out(2)' }, 4.1);

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

      <!-- SECTION 6: THINKING OFF -->
      <div class="kamusai-sec kamusai-thinking-off">
        <div class="kamusai-thinking-off-container">

          <!-- Garis pembagi tengah -->
          <div class="kamusai-split-line"></div>

          <!-- Labels di atas masing-masing sisi -->
          <p class="kamusai-side-label kamusai-side-label-on" style="left: 4%; top: 80px;">THINKING ON</p>
          <p class="kamusai-side-label kamusai-side-label-off" style="right: 4%; top: 80px;">THINKING OFF</p>

          <!-- Kiri: Thinking ON — contoh chain-of-thought -->
          <div class="kamusai-think-on-side">
            <!-- Question box -->
            <div class="kamusai-cot-question-box kamusai-think-cot-q">
              <span style="font-size:48px;">❓</span>
              <p style="font-size:52px;color:#fff;margin-top:16px;font-weight:700;">Tapi hari ini...</p>
            </div>

            <!-- Thinking block -->
            <div class="kamusai-think-block kamusai-think-cot-thinking">
              <span class="kamusai-think-tag">&lt;thinking&gt;</span>
              <p style="font-size:40px;color:#aaa;text-align:center;">Wah si pria solo ini mah...</p>
              <span class="kamusai-think-tag">&lt;/thinking&gt;</span>
            </div>

            <!-- Answer -->
            <div class="kamusai-think-answer kamusai-think-cot-ans">
              <span style="font-size:40px;color:#7AE582;">→</span>
              <p style="font-size:48px;color:#7AE582;font-weight:900;margin-top:16px;">SAYA AKAN LAWAN!!!</p>
            </div>

            <span class="kamusai-think-check" style="font-size:56px;color:#7AE582;margin-top:30px;">✅</span>
          </div>

          <!-- Kanan: Thinking OFF — langsung jawab -->
          <div class="kamusai-think-off-side">
            <!-- Question box (sama) -->
            <div class="kamusai-cot-question-box kamusai-think-raw-q" style="border-color: rgba(255,82,82,0.4); background: rgba(255,82,82,0.06);">
              <span style="font-size:48px;">❓</span>
              <p style="font-size:52px;color:#fff;margin-top:16px;font-weight:700;">Tapi hari ini...</p>
            </div>

            <!-- Langsung jawab, tanpa thinking -->
            <div class="kamusai-raw-answer kamusai-think-raw-ans">
              <span style="font-size:36px;color:#aaa;margin-bottom:12px;display:block;text-align:center;">(langsung jawab)</span>
              <p style="font-size:56px;color:#fff;font-weight:900;line-height:1.4;">Kenapa hari ini?</p>
            </div>

            <span class="kamusai-think-warn" style="font-size:56px;color:#FFD77A;margin-top:30px;">⚠️</span>
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

  /* THINKING OFF — SECTION 6 (split-screen) */
  .kamusai-thinking-off-container {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .kamusai-split-line {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 50%;
    width: 4px;
    background: linear-gradient(to bottom, #FFD77A, #FF5252);
    transform: translateX(-50%) scaleX(0);
    z-index: 20;
    box-shadow: 0 0 30px rgba(255,215,122,0.6), 0 0 30px rgba(255,82,82,0.6);
  }

  .kamusai-think-on-side, .kamusai-think-off-side {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 46%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    padding-top: 280px;
    gap: 30px;
  }

  .kamusai-think-on-side { left: 2%; }
  .kamusai-think-off-side { right: 2%; }

  /* Labels */
  .kamusai-side-label {
    font-size: 56px;
    font-weight: 900;
    letter-spacing: 4px;
    position: absolute;
    z-index: 25;
  }

  .kamusai-side-label-on { color: #7AE582; text-shadow: 0 0 30px rgba(122,229,130,0.6); }
  .kamusai-side-label-off { color: #FF5252; text-shadow: 0 0 30px rgba(255,82,82,0.6); }

  /* Question box (sama untuk ON/OFF) */
  .kamusai-cot-question-box {
    background: rgba(0,191,255,0.08);
    border: 2px solid rgba(0,191,255,0.35);
    border-radius: 24px;
    padding: 36px 40px;
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 88%;
  }

  /* Thinking block (chain-of-thought) */
  .kamusai-think-block {
    background: rgba(122,229,130,0.06);
    border: 2px solid rgba(122,229,130,0.35);
    border-radius: 24px;
    padding: 36px 40px;
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 88%;
    opacity: 0;
    transform: translateY(20px);
  }

  .kamusai-think-tag {
    font-family: 'Courier New', monospace;
    font-size: 48px;
    font-weight: 900;
    color: #FFD77A;
    text-shadow: 0 0 20px rgba(255,215,122,0.5);
  }

  /* Answer box */
  .kamusai-think-answer {
    background: rgba(122,229,130,0.1);
    border: 3px solid rgba(122,229,130,0.5);
    border-radius: 24px;
    padding: 36px 40px;
    display: flex;
    align-items: center;
    gap: 20px;
    width: 88%;
    opacity: 0;
    transform: translateY(20px);
  }

  /* Raw answer (thinking off) */
  .kamusai-raw-answer {
    background: rgba(255,215,122,0.06);
    border: 2px solid rgba(255,215,122,0.35);
    border-radius: 24px;
    padding: 40px 36px;
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 88%;
    opacity: 0;
    transform: translateY(20px);
  }

  .kamusai-think-check, .kamusai-think-warn { margin-top: 30px !important; }
</style>
