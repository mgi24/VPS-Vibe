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
  let duration = 61.8;
  let isPlaying = false;
  let speed = 1;

  const W = 1080;
  const H = 1920;

  function setupCanvasSize() {
    const isPreview = showFrame >= 0 && isFinite(showFrame);
    const availableW = window.innerWidth;
    const availableH = isPreview ? window.innerHeight : window.innerHeight - 160;
    
    // Fit canvas to viewport while maintaining aspect ratio, with small margin
    const scale = Math.min(availableW / W, availableH / H) * (isPreview ? 0.95 : 0.92);
    
    if (!isPreview) {
      document.querySelector('.page')?.style.removeProperty('padding-top');
      wrapEl?.style.removeProperty('margin-top');
    } else {
      const page = document.querySelector('.page');
      if (page) { page.style.paddingTop = '0'; page.style.marginTop = '0'; }
      if (wrapEl) wrapEl.style.marginTop = '0';
      // Remove overflow hidden on stage for preview mode so content isn't clipped
      if (canvasEl) canvasEl.style.overflow = '';
    }
    
    if (wrapEl) { wrapEl.style.width = W * scale + 'px'; wrapEl.style.height = H * scale + 'px'; }
    if (canvasEl) canvasEl.style.transform = `scale(${scale})`;
  }

  function buildTimeline() {
    tl = gsap.timeline({ paused: true });

    // Make all sections hidden first (CSS default is visible)
    document.querySelectorAll('.sec').forEach(el => { el.style.display = 'none'; el.style.opacity = '0'; });

    // === SECTION 1: INTRO (0s – 3.6s) ===
    tl.set('.sec-intro', { display: 'flex', autoAlpha: 1 }, 0);
    
    // Kata per kata muncul dengan stagger
    const introWords = document.querySelectorAll('.intro-word');
    gsap.set(introWords, { autoAlpha: 0, y: 40 });
    tl.to(introWords, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)', stagger: 0.3 }, 0);

    // Intro fade out sebelum LLM
    tl.to('.sec-intro', { autoAlpha: 0, duration: 0.3 }, 3.2);

    // === SECTION 2: LLM (3.6s – 11.3s) ===
    tl.set('.sec-llm', { autoAlpha: 1, display: 'flex' }, 3.6);
    
    // Judul LLM muncul
    tl.fromTo('.llm-title', { autoAlpha: 0, y: -30 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 3.6);
    
    // Subtitle "Large Language Model"
    tl.fromTo('.llm-subtitle', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.4 }, 3.9);

    // Diagram input → model → output muncul bertahap
    tl.fromTo('.llm-input-box', { autoAlpha: 0, x: -60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 4.3);
    tl.fromTo('.llm-arrow-right', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.3 }, 4.8);
    tl.fromTo('.llm-model-box', { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'back.out(2)' }, 5.1);
    tl.fromTo('.llm-arrow-left', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.3 }, 5.6);
    tl.fromTo('.llm-output-box', { autoAlpha: 0, x: 60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 5.9);

    // Highlight "TEKS DOANG YA"
    tl.fromTo('.llm-highlight', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.4, ease: 'elastic.out(1, 0.5)' }, 7.5);

    // === t=6.8s: text → robot → text (smaller scale) ===
    tl.set('.mini-flow', { autoAlpha: 0, display: 'flex' }, 6.8);
    gsap.set('.mini-box', { scale: 0 });
    tl.to('.mini-text-in', { scale: 1, duration: 0.25, ease: 'back.out(2)' }, 6.8);
    tl.to('.mini-arrow', { autoAlpha: 1, duration: 0.15 }, 7.0);
    tl.to('.mini-robot', { scale: 1, duration: 0.3, ease: 'back.out(2)' }, 7.15);
    tl.to('.mini-arrow2', { autoAlpha: 1, duration: 0.15 }, 7.45);
    tl.to('.mini-text-out', { scale: 1, duration: 0.25, ease: 'back.out(2)' }, 7.6);

    // LLM fade out
    tl.to('.sec-llm', { autoAlpha: 0, duration: 0.3 }, 10.8);

    // === SECTION 3: MULTIMODAL (11.4s – 27.06s) ===
    tl.set('.sec-multimodal', { autoAlpha: 1, display: 'flex' }, 11.4);
    
    tl.fromTo('.mm-title', { autoAlpha: 0, y: -30 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 11.4);
    tl.fromTo('.mm-subtitle', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.4 }, 11.7);
    
    // Diagram: teks biasa vs multimodal (gambar + audio)
    tl.fromTo('.mm-text-only', { autoAlpha: 0, x: -60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 12.3);
    tl.fromTo('.mm-x-icon', { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.3, ease: 'back.out(2)' }, 12.8);
    tl.fromTo('.mm-image-box', { autoAlpha: 0, x: -60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 13.3);
    tl.fromTo('.mm-plus-icon', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.3 }, 13.7);
    tl.fromTo('.mm-audio-box', { autoAlpha: 0, x: 60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 14.1);
    
    // Highlight "BISA GAMBAR + AUDIO"
    tl.fromTo('.mm-highlight', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'elastic.out(1, 0.5)' }, 16.5);
    
    // "Base 64" muncul
    tl.fromTo('.mm-base64', { autoAlpha: 0, y: 30 }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'back.out(2)' }, 20.5);
    
    // Multimodal fade out
    tl.to('.sec-multimodal', { autoAlpha: 0, duration: 0.3 }, 26.5);

    // === SECTION 4: INPUT (27.06s – 36.14s) ===
    tl.set('.sec-input', { autoAlpha: 1, display: 'flex' }, 27.06);
    
    tl.fromTo('.input-title', { autoAlpha: 0, y: -30 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 27.06);
    tl.fromTo('.input-question', { autoAlpha: 0, scale: 0.9 }, { autoAlpha: 1, scale: 1, duration: 0.4 }, 27.4);
    
    // Gambar muncul dari kiri
    tl.fromTo('.input-img-side', { autoAlpha: 0, x: -60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 28.3);
    
    // Audio muncul dari kanan
    tl.fromTo('.input-audio-side', { autoAlpha: 0, x: 60 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, 28.7);
    
    // Panah transformasi berkedip (pulse) — efek proses encoding
    tl.fromTo('.transform-arrow-1', { autoAlpha: 0, scaleX: 0.3 }, { autoAlpha: 1, scaleX: 1, duration: 0.25, ease: 'back.out(3)' }, 30);
    
    // Label "transform" muncul
    tl.fromTo('.transform-label', { autoAlpha: 0, y: -10 }, { autoAlpha: 1, y: 0, duration: 0.3 }, 30.2);
    
    // Panah kedua muncul
    tl.fromTo('.transform-arrow-2', { autoAlpha: 0, scaleX: 0.3 }, { autoAlpha: 1, scaleX: 1, duration: 0.25, ease: 'back.out(3)' }, 30.4);
    
    // Panah berkedip (pulse) — efek proses berjalan
    tl.to('.transform-arrow-1', { autoAlpha: 0.3, duration: 0.15 }, 31);
    tl.to('.transform-arrow-1', { autoAlpha: 1, duration: 0.15 }, 31.15);
    tl.to('.transform-arrow-2', { autoAlpha: 0.3, duration: 0.15 }, 31.3);
    tl.to('.transform-arrow-2', { autoAlpha: 1, duration: 0.15 }, 31.45);
    
    // Hasil teks muncul — scale up + glow
    tl.fromTo('.input-result-box', { autoAlpha: 0, scale: 0.5, y: 30 }, { autoAlpha: 1, scale: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 32);
    
    // Highlight "DIBIKIN TEKS GITU YA!"
    tl.fromTo('.input-highlight', { autoAlpha: 0, scale: 0.85 }, { autoAlpha: 1, scale: 1, duration: 0.45, ease: 'elastic.out(1, 0.6)' }, 32.5);
    
    // Base 64 area muncul
    tl.fromTo('.base64-area', { autoAlpha: 0, y: 30 }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'back.out(2)' }, 33);
    
    // Typing effect — baris muncul satu per satu dengan cursor
    tl.fromTo('.base64-line-1', { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'none' }, 33.8);
    
    // Cursor pindah ke baris 2
    tl.set('.typing-cursor', { display: 'none' }, 34.3);
    tl.set('.cursor-2', { display: 'inline', autoAlpha: 1 }, 34.3);
    tl.fromTo('.base64-line-2', { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'none' }, 34.8);
    
    // Cursor pindah ke baris 3
    tl.set('.cursor-2', { display: 'none' }, 35.3);
    tl.set('.cursor-3', { display: 'inline', autoAlpha: 1 }, 35.3);
    tl.fromTo('.base64-line-3', { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'none' }, 35.8);
    
    // Cursor pindah ke baris 4
    tl.set('.cursor-3', { display: 'none' }, 36.3);
    tl.set('.cursor-4', { display: 'inline', autoAlpha: 1 }, 36.3);
    tl.fromTo('.base64-line-4', { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'none' }, 36.8);
    
    // Cursor pindah ke baris 5
    tl.set('.cursor-4', { display: 'none' }, 37.3);
    tl.set('.cursor-5', { display: 'inline', autoAlpha: 1 }, 37.3);
    tl.fromTo('.base64-line-5', { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'none' }, 37.8);
    
    // Cursor hilang setelah semua baris muncul
    tl.set('.cursor-5', { autoAlpha: 0 }, 39);
    
    // Highlight "BASE 64" dengan efek typing (muncul huruf per huruf via scale + opacity)
    tl.fromTo('.input-base64-highlight', { autoAlpha: 0, scaleX: 0 }, { autoAlpha: 1, scaleX: 1, duration: 0.6, ease: 'steps(8)' }, 39);
    
    // Input fade out
    tl.to('.sec-input', { autoAlpha: 0, duration: 0.3 }, 40);

    // === SECTION 5: THINKING (40.4s – 52.7s) ===
    tl.set('.sec-thinking', { autoAlpha: 1, display: 'flex' }, 40.4);
    
    tl.fromTo('.think-title', { autoAlpha: 0, y: -30 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 40.6);
    tl.fromTo('.think-subtitle', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.4 }, 40.9);
    
    // Diagram: AI berpikir dengan alternatif jawaban
    tl.fromTo('.think-ai-box', { autoAlpha: 0, scale: 0.6 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'back.out(2)' }, 41.7);
    tl.fromTo('.think-brain-icon', { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.4, ease: 'elastic.out(1, 0.6)' }, 42.3);
    
    // Multiple answer paths muncul bertahap
    tl.fromTo('.think-path-1', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.35 }, 43.8);
    tl.fromTo('.think-path-2', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.35 }, 44.8);
    tl.fromTo('.think-path-3', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.35 }, 45.8);
    
    // Highlight "PROBABILITAS PALING TINGGI"
    tl.fromTo('.think-highlight', { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'elastic.out(1, 0.5)' }, 47.6);

    // Thinking fade out
    tl.to('.sec-thinking', { autoAlpha: 0, duration: 0.3 }, 52.4);

    // === SECTION 6: THINKING OFF (52.7s – 59.8s) ===
    tl.set('.sec-thinking-off', { autoAlpha: 1, display: 'flex' }, 52.7);
    
    // Split reveal: garis tengah muncul dari tengah ke samping
    tl.fromTo('.split-line', { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: 'power2.inOut' }, 52.7);
    
    // Labels muncul dulu
    tl.fromTo('.side-label-on', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.3, ease: 'back.out(2)' }, 53);
    tl.fromTo('.side-label-off', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.3, ease: 'back.out(2)' }, 53.3);
    
    // === KIRI: Thinking ON chain-of-thought ===
    // Question box muncul
    tl.fromTo('.think-cot-q', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'back.out(2)' }, 54);
    
    // Thinking block muncul dengan tag <thinking>
    tl.fromTo('.think-cot-thinking', { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'back.out(2)' }, 54.8);
    
    // Answer muncul
    tl.fromTo('.think-cot-ans', { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'back.out(2)' }, 55.8);
    
    // Checkmark muncul
    tl.fromTo('.think-check', { scale: 0 }, { scale: 1, duration: 0.3, ease: 'back.out(3)' }, 56.4);
    
    // === KANAN: Thinking OFF langsung jawab ===
    // Question box muncul (sama)
    tl.fromTo('.think-raw-q', { autoAlpha: 0, x: 20 }, { autoAlpha: 1, x: 0, duration: 0.4, ease: 'power2.out' }, 55);
    
    // Langsung jawab — tanpa thinking
    tl.fromTo('.think-raw-ans', { autoAlpha: 0, scale: 0.7 }, { autoAlpha: 1, scale: 1, duration: 0.45, ease: 'back.out(2)' }, 56);
    
    // Warning muncul
    tl.fromTo('.think-warn', { autoAlpha: 0, y: -10 }, { autoAlpha: 1, y: 0, duration: 0.3, ease: 'back.out(2)' }, 56.8);
    
    // Thinking OFF fade out
    tl.to('.sec-thinking-off', { autoAlpha: 0, duration: 0.3 }, 59.4);

    // === SECTION 7: OUTRO (59.7s – 63.2s) ===
    tl.set('.sec-outro', { autoAlpha: 1, display: 'flex' }, 59.7);
    
    tl.fromTo('.outro-text-1', { autoAlpha: 0, y: -20 }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'back.out(2)' }, 59.7);
    tl.fromTo('.outro-text-2', { autoAlpha: 0, scale: 0.9 }, { autoAlpha: 1, scale: 1, duration: 0.4, ease: 'elastic.out(1, 0.6)' }, 60.5);
    
    // Outro fade out
    tl.to('.sec-outro', { autoAlpha: 0, duration: 0.3 }, 62.8);

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
      // In preview mode (showFrame), just render once and stop
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

    // Force show intro section immediately (GSAP timeline sets may not apply yet)
    const intro = document.querySelector('.sec-intro');
    if (intro) { 
      intro.style.display = 'flex'; 
      intro.style.opacity = '1'; 
      gsap.set('.intro-word', { opacity: 1, visibility: 'visible' });
    }

    setupCanvasSize();
    window.addEventListener('resize', setupCanvasSize);

    // Preview mode: show a single frame, no controls needed
    if (showFrame >= 0 && isFinite(showFrame)) {
      const previewTime = Math.min(showFrame / 24, duration - 0.01);
      console.log('Preview mode, frame:', showFrame, 'time:', previewTime.toFixed(3), 's');
      
      // Force GSAP to flush renders at this time
      requestAnimationFrame(() => {
        tl.render(previewTime, true);
        gsap.ticker.pause();
        raf = null;
        
        if (controller) {
          controller.update((c) => ({ ...c, stageReady: true, W, H, duration, canvasEl, wrapEl, play, pause, playPause, seekTo, getTime, getDuration, isPlaying: isPlayingFn, setSpeed, stepFrame, reset, exportFrame: null, restoreLayout: null }));
        }
      });
    } else {
      tl.seek(0);
      raf = requestAnimationFrame(tick);
      if (controller) {
        controller.update((c) => ({ ...c, stageReady: true, W, H, duration, canvasEl, wrapEl, play, pause, playPause, seekTo, getTime, getDuration, isPlaying: isPlayingFn, setSpeed, stepFrame, reset, exportFrame: null, restoreLayout: null }));
      }
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
      
      <!-- SECTION 1: INTRO -->
      <div class="sec sec-intro">
        <div class="intro-container">
          <span class="intro-word word-1">TIGA</span>
          <br><br>
          <span class="intro-word word-2">KAMUS AI</span>
          <br><br>
          <span class="intro-word word-3">PER HARI.</span>
        </div>
      </div>

      <!-- SECTION 2: LLM -->
      <div class="sec sec-llm">
        <div class="llm-container">
          <h1 class="llm-title">LLM</h1>
          <p class="llm-subtitle">Large Language Model</p>
          
          <div class="llm-diagram">
            <div class="llm-input-box">
              <span class="icon-emoji">⌨️</span>
              <br>
              <span class="label-text">TEKS</span>
            </div>
            
            <div class="llm-arrow-right">→</div>
            
            <div class="llm-model-box">
              <span class="icon-emoji">🤖</span>
            </div>
            
            <div class="llm-arrow-left">→</div>
            
            <div class="llm-output-box">
              <span class="icon-emoji">📄</span>
              <br>
              <span class="label-text">TEKS</span>
            </div>
          </div>
          
          <p class="llm-highlight">TEKS DOANG YA</p>

          <!-- Mini flow: text → robot → text (smaller scale) -->
          <div class="mini-flow" style="position:absolute;bottom:30px;left:50%;transform:translateX(-50%);display:none;align-items:center;gap:4px;">
            <div class="mini-box mini-text-in">⌨️</div>
            <span class="mini-arrow" style="opacity:0;font-size:16px;color:#00BFFF;">→</span>
            <div class="mini-box mini-robot">🤖</div>
            <span class="mini-arrow2" style="opacity:0;font-size:16px;color:#7AE582;">→</span>
            <div class="mini-box mini-text-out">📄</div>
          </div>
        </div>
      </div>

      <!-- SECTION 3: MULTIMODAL -->
      <div class="sec sec-multimodal">
        <div class="mm-container">
          <h1 class="mm-title">MULTIMODAL</h1>
          <p class="mm-subtitle">Lebih dari Sekedar Teks</p>
          
          <div class="mm-diagram">
            <div class="mm-box mm-text-only">
              <span class="icon-emoji">⌨️</span>
              <span class="label-text">TEKS DOANG</span>
            </div>
            
            <span class="mm-x-icon" style="font-size:64px;color:#ff5252;">✖</span>
            
            <div class="mm-diagram-right">
              <div class="mm-box mm-image-box">
                <span class="icon-emoji">🖼️</span>
                <span class="label-text">GAMBAR</span>
              </div>
              
              <span class="mm-plus-icon" style="font-size:48px;color:#7AE582;margin:16px 0;display:block;text-align:center;">+</span>
              
              <div class="mm-box mm-audio-box">
                <span class="icon-emoji">🎤</span>
                <span class="label-text">AUDIO</span>
              </div>
            </div>
          </div>
          
          <p class="mm-highlight">BISA GAMBAR + AUDIO!</p>
          <p class="mm-base64" style="color:#aaa;font-size:52px;margin-top:60px;">Dikonversi jadi Base 64</p>
        </div>
      </div>

      <!-- SECTION 4: INPUT (27.06s – 36.14s) -->
      <div class="sec sec-input">
        <div class="input-container">
          <h1 class="input-title">INPUT</h1>
          <p class="input-question">Gimana Cara Inputnya?</p>
          
          <!-- Diagram: gambar → transformasi → teks / audio → teks -->
          <div class="input-diagram">
            <!-- Kiri: Gambar -->
            <div class="input-side input-img-side">
              <span class="icon-emoji input-img-icon" style="font-size:120px;">🖼️</span>
              <p class="input-label input-img-label" style="margin-top:16px;font-size:48px;color:#00BFFF;">GAMBAR</p>
            </div>
            
            <!-- Tengah: panah transformasi berkedip -->
            <div class="input-transform">
              <span class="transform-arrow transform-arrow-1" style="font-size:56px;color:#00BFFF;">→</span>
              <p class="transform-label" style="font-size:32px;color:#FFD77A;margin-top:8px;text-align:center;">transform</p>
              <span class="transform-arrow transform-arrow-2" style="font-size:56px;color:#7AE582;">→</span>
            </div>
            
            <!-- Kanan: Audio -->
            <div class="input-side input-audio-side">
              <span class="icon-emoji input-audio-icon" style="font-size:120px;">🎤</span>
              <p class="input-label input-audio-label" style="margin-top:16px;font-size:48px;color:#7AE582;">AUDIO</p>
            </div>
          </div>
          
          <!-- Hasil: teks -->
          <div class="input-result-box">
            <span class="icon-emoji input-result-icon" style="font-size:100px;">📄</span>
            <p class="input-result-label" style="font-size:56px;font-weight:900;color:#fff;margin-top:16px;">TEKS</p>
          </div>
          
          <!-- Highlight -->
          <p class="input-highlight">DIBIKIN TEKS GITU YA!</p>
          
          <!-- Base 64 code typing area -->
          <div class="base64-area base64-typing">
            <span class="typing-cursor" style="color:#7AE582;">▌</span><span class="base64-line base64-line-1" style="opacity:0;">data:image/png;base64,iVBORw0KGgoAAAANSU...</span>
            <br>
            <span class="typing-cursor cursor-2" style="color:#7AE582;display:none;">▌</span><span class="base64-line base64-line-2" style="opacity:0;">data:audio/mp3;base64,UklGRi9vTWFu...</span>
            <br>
            <span class="typing-cursor cursor-3" style="color:#7AE582;display:none;">▌</span><span class="base64-line base64-line-3" style="opacity:0;">base64://eyJ0eXAiOiJKV1QiLCJhbGc...</span>
            <br>
            <span class="typing-cursor cursor-4" style="color:#7AE582;display:none;">▌</span><span class="base64-line base64-line-4" style="opacity:0;">// AI encoding pipeline</span>
            <br>
            <span class="typing-cursor cursor-5" style="color:#7AE582;display:none;">▌</span><span class="base64-line base64-line-5" style="opacity:0;">→ converting multimodal → text tokens</span>
          </div>
          
          <!-- Base 64 typing highlight -->
          <p class="input-base64-highlight" style="font-size:72px;font-weight:900;color:#FFD77A;text-shadow:0 0 30px rgba(255,215,122,0.6);">BASE 64</p>
        </div>
      </div>

      <!-- SECTION 5: THINKING -->
      <div class="sec sec-thinking">
        <div class="think-container">
          <h1 class="think-title">THINKING</h1>
          <p class="think-subtitle">Mikir Dulu Sebelum Jawab</p>
          
          <div class="think-diagram">
            <div class="think-ai-box">
              <span class="icon-emoji think-brain-icon" style="font-size:120px;">🧠</span>
            </div>
            
            <div class="think-paths">
              <div class="think-path think-path-1">✓ Jawaban A (prob. 45%)</div>
              <div class="think-path think-path-2">✓ Jawaban B (prob. 35%)</div>
              <div class="think-path think-path-3">✓ Jawaban C (prob. 20%)</div>
            </div>
          </div>
          
          <p class="think-highlight">PROBABILITAS PALING TINGGI</p>
        </div>
      </div>

      <!-- SECTION 6: THINKING OFF (52.7s – 59.8s) -->
      <div class="sec sec-thinking-off">
        <div class="thinking-off-container">
          
          <!-- Garis pembagi tengah -->
          <div class="split-line"></div>
          
          <!-- Labels di atas masing-masing sisi -->
          <p class="side-label side-label-on" style="left: 4%; top: 80px;">THINKING ON</p>
          <p class="side-label side-label-off" style="right: 4%; top: 80px;">THINKING OFF</p>
          
          <!-- Kiri: Thinking ON — contoh chain-of-thought -->
          <div class="think-on-side">
            <!-- Question box -->
            <div class="cot-question-box think-cot-q">
              <span style="font-size:48px;">❓</span>
              <p style="font-size:52px;color:#fff;margin-top:16px;font-weight:700;">Tapi hari ini...</p>
            </div>
            
            <!-- Thinking block -->
            <div class="think-block think-cot-thinking">
              <span class="think-tag">&lt;thinking&gt;</span>
              <p class="cot-thought" style="font-size:40px;">Wah si pria solo ini mah...</p>
              <span class="think-tag">&lt;/thinking&gt;</span>
            </div>
            
            <!-- Answer -->
            <div class="think-answer think-cot-ans">
              <span style="font-size:40px;color:#7AE582;">→</span>
              <p style="font-size:48px;color:#7AE582;font-weight:900;margin-top:16px;">SAYA AKAN LAWAN!!!</p>
            </div>
            
            <span class="check-icon think-check" style="font-size:56px;color:#7AE582;margin-top:30px;">✅</span>
          </div>
          
          <!-- Kanan: Thinking OFF — langsung jawab -->
          <div class="think-off-side">
            <!-- Question box (sama) -->
            <div class="cot-question-box think-raw-q" style="border-color: rgba(255,82,82,0.4); background: rgba(255,82,82,0.06);">
              <span style="font-size:48px;">❓</span>
              <p style="font-size:52px;color:#fff;margin-top:16px;font-weight:700;">Tapi hari ini...</p>
            </div>
            
            <!-- Langsung jawab, tanpa thinking -->
            <div class="raw-answer think-raw-ans">
              <span style="font-size:36px;color:#aaa;margin-bottom:12px;display:block;text-align:center;">(langsung jawab)</span>
              <p style="font-size:56px;color:#fff;font-weight:900;line-height:1.4;">Kenapa hari ini?</p>
            </div>
            
            <span class="warning-icon think-warn" style="font-size:56px;color:#FFD77A;margin-top:30px;">⚠️</span>
          </div>
          
        </div>
      </div>

      <!-- SECTION 7: OUTRO -->
      <div class="sec sec-outro">
        <div class="outro-container">
          <p class="outro-text-1" style="font-size:72px;font-weight:900;color:#00BFFF;text-shadow:0 0 40px rgba(0,191,255,0.6);text-align:center;">
            Part Lainnya
          </p>
          <p class="outro-text-2" style="font-size:80px;font-weight:900;color:#7AE582;text-shadow:0 0 40px rgba(122,229,130,0.6);text-align:center;margin-top:40px;">
            Cek di Komen! 💬
          </p>
        </div>
      </div>

    </div>
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; align-items: center; min-height: 100vh; background: #05050d; font-family: 'Inter', sans-serif; color: #fff; padding-top: 20px; }
  .stage-wrap { position: relative; overflow: visible; flex-shrink: 0; margin-top: 80px; }
  .stage { position: relative; width: 1080px; height: 1920px; transform-origin: top left; overflow: hidden; background: #0D0D1A; border-radius: 12px; box-shadow: 0 0 60px rgba(0,191,255,0.15); }
  .sec { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; z-index: 10; }

  /* INTRO */
  .intro-container { text-align: center; padding: 40px; }
  .intro-word { font-size: 96px; font-weight: 900; color: #00BFFF; text-shadow: 0 0 40px rgba(0,191,255,0.6); display: inline-block; }
  .word-2 { color: #fff; }
  .word-3 { color: #7AE582; font-size: 72px; }

  /* LLM */
  .llm-container { text-align: center; padding: 40px; width: 100%; }
  .llm-title { font-size: 140px; font-weight: 900; color: #00BFFF; text-shadow: 0 0 60px rgba(0,191,255,0.8); margin-bottom: 20px; }
  .llm-subtitle { font-size: 64px; font-weight: 700; color: #aaa; margin-bottom: 120px; }

  .llm-diagram { display: flex; align-items: center; justify-content: center; gap: 20px; margin-top: 80px; width: 100%; box-sizing: border-box; }
  
  .llm-input-box, .llm-model-box, .llm-output-box {
    background: rgba(0,191,255,0.1);
    border: 2px solid rgba(0,191,255,0.4);
    border-radius: 24px;
    padding: 40px 30px;
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
  }

  .llm-input-box, .llm-output-box { width: 260px; }
  
  .llm-model-box {
    background: rgba(122,229,130,0.1);
    border-color: rgba(122,229,130,0.5);
    width: 220px;
  }

  .icon-emoji { font-size: 80px; display: block; margin-bottom: 20px; }
  .label-text { font-size: 48px; font-weight: 900; color: #fff; }

  .llm-arrow-right, .llm-arrow-left {
    font-size: 72px;
    color: #00BFFF;
    font-weight: 900;
  }

  .llm-highlight {
    margin-top: 100px;
    font-size: 80px;
    font-weight: 900;
    color: #FFD77A;
    text-shadow: 0 0 40px rgba(255,215,122,0.6);
    border-bottom: 4px solid #FFD77A;
  }

  .mini-flow { z-index: 15; padding: 12px; background: rgba(0,0,0,0.4); border-radius: 12px; gap: 4px; }
  .mini-box { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; font-size: 20px; background: rgba(0,191,255,0.1); border: 2px solid rgba(0,191,255,0.4); border-radius: 8px; }
  .mini-robot { background: rgba(122,229,130,0.1); border-color: rgba(122,229,130,0.5); font-size: 24px; }
  .mini-text-out { background: rgba(255,215,122,0.1); border-color: rgba(255,215,122,0.4); }

  /* MULTIMODAL */
  .mm-container { text-align: center; padding: 40px; width: 100%; }
  .mm-title { font-size: 130px; font-weight: 900; color: #7AE582; text-shadow: 0 0 60px rgba(122,229,130,0.8); margin-bottom: 20px; }
  .mm-subtitle { font-size: 56px; font-weight: 700; color: #aaa; margin-bottom: 100px; }

  .mm-diagram { display: flex; align-items: center; justify-content: center; gap: 20px; margin-top: 80px; width: 100%; box-sizing: border-box; }
  
  .mm-box {
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

  .mm-image-box { background: rgba(0,191,255,0.1); border-color: rgba(0,191,255,0.4); }
  .mm-audio-box { background: rgba(255,215,122,0.1); border-color: rgba(255,215,122,0.4); }

  .mm-diagram-right { display: flex; flex-direction: column; align-items: center; gap: 0; }

  .mm-highlight {
    margin-top: 80px;
    font-size: 76px;
    font-weight: 900;
    color: #FFD77A;
    text-shadow: 0 0 40px rgba(255,215,122,0.6);
    border-bottom: 4px solid #FFD77A;
  }

  .mm-base64 { font-size: 52px; color: #aaa; margin-top: 60px; }

  /* INPUT */
  .input-container { text-align: center; padding: 40px; width: 100%; display: flex; flex-direction: column; align-items: center; }
  .input-title { font-size: 130px; font-weight: 900; color: #FFD77A; text-shadow: 0 0 60px rgba(255,215,122,0.8); margin-bottom: 20px; }
  .input-question { font-size: 56px; font-weight: 700; color: #aaa; margin-bottom: 60px; }

  .input-diagram { display: flex; align-items: center; justify-content: center; gap: 24px; width: 100%; box-sizing: border-box; }
  
  /* Side boxes (gambar / audio) */
  .input-side {
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

  .input-audio-side { background: rgba(122,229,130,0.08); border-color: rgba(122,229,130,0.35); }
  
  /* Transform area (tengah) */
  .input-transform {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .transform-arrow { font-size: 56px; font-weight: 900; opacity: 0; }
  
  .transform-label {
    font-size: 32px;
    color: #FFD77A;
    margin-top: 8px;
    text-align: center;
    opacity: 0;
    letter-spacing: 2px;
  }

  /* Hasil teks */
  .input-result-box {
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

  .input-result-icon { font-size: 100px; }
  .input-result-label { font-size: 56px; font-weight: 900; color: #fff; margin-top: 16px; }

  /* Highlight */
  .input-highlight {
    margin-top: 80px;
    font-size: 72px;
    font-weight: 900;
    color: #00BFFF;
    text-shadow: 0 0 40px rgba(0,191,255,0.6);
    border-bottom: 4px solid #00BFFF;
  }

  /* Base 64 typing area */
  .base64-area {
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

  .base64-typing {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 30px;
  }

  .typing-cursor {
    animation: cursor-blink 0.8s step-end infinite;
  }

  .cursor-2, .cursor-3, .cursor-4, .cursor-5 {
    display: none !important;
  }

  @keyframes cursor-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }

  .base64-line {
    white-space: nowrap;
    font-size: 30px;
    line-height: 1.8;
  }

  /* Base 64 typing highlight */
  .input-base64-highlight {
    margin-top: 50px;
    opacity: 0;
    display: inline-block;
  }

  /* THINKING */
  .think-container { text-align: center; padding: 40px; width: 100%; }
  .think-title { font-size: 130px; font-weight: 900; color: #FF5252; text-shadow: 0 0 60px rgba(255,82,82,0.8); margin-bottom: 20px; }
  .think-subtitle { font-size: 56px; font-weight: 700; color: #aaa; margin-bottom: 100px; }

  .think-diagram { display: flex; align-items: center; justify-content: center; gap: 40px; margin-top: 80px; width: 100%; box-sizing: border-box; }
  
  .think-ai-box {
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

  .think-paths { display: flex; flex-direction: column; gap: 20px; text-align: left; min-width: 350px; max-width: 450px; }
  
  .think-path {
    font-size: 52px;
    font-weight: 700;
    color: #fff;
    background: rgba(0,191,255,0.1);
    border: 2px solid rgba(0,191,255,0.3);
    border-radius: 16px;
    padding: 24px 36px;
    opacity: 0;
  }

  .think-path-1 { color: #7AE582; border-color: rgba(122,229,130,0.5); }
  .think-path-2 { color: #FFD77A; border-color: rgba(255,215,122,0.5); }
  .think-path-3 { color: #aaa; border-color: rgba(170,170,170,0.3); }

  .think-highlight {
    margin-top: 80px;
    font-size: 72px;
    font-weight: 900;
    color: #FFD77A;
    text-shadow: 0 0 40px rgba(255,215,122,0.6);
    border-bottom: 4px solid #FFD77A;
  }

  .think-off-label { font-size: 64px; font-weight: 900; color: #ff5252; margin-top: 30px; }
  
  .think-off-highlight {
    margin-top: 60px;
    font-size: 72px;
    font-weight: 900;
    color: #FF5252;
    text-shadow: 0 0 40px rgba(255,82,82,0.6);
    border-bottom: 4px solid #FF5252;
  }

  /* THINKING OFF — SECTION 6 (split-screen) */
  .thinking-off-container {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .split-line {
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

  .think-on-side, .think-off-side {
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

  .think-on-side { left: 2%; }
  .think-off-side { right: 2%; }

  /* Labels */
  .side-label {
    font-size: 56px;
    font-weight: 900;
    letter-spacing: 4px;
    position: absolute;
    z-index: 25;
  }

  .side-label-on { color: #7AE582; text-shadow: 0 0 30px rgba(122,229,130,0.6); }
  .side-label-off { color: #FF5252; text-shadow: 0 0 30px rgba(255,82,82,0.6); }

  /* Question box (sama untuk ON/OFF) */
  .cot-question-box {
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
  .think-block {
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

  .think-tag {
    font-family: 'Courier New', monospace;
    font-size: 48px;
    font-weight: 900;
    color: #FFD77A;
    text-shadow: 0 0 20px rgba(255,215,122,0.5);
  }

  .cot-thought {
    color: #aaa;
    font-size: 40px;
    text-align: center;
  }

  /* Answer box */
  .think-answer {
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
  .raw-answer {
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

  .think-check, .think-warn { margin-top: 30px !important; }

  /* OUTRO */
  .outro-container { text-align: center; padding: 40px; width: 100%; }

  .sec { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; z-index: 10; }
</style>
