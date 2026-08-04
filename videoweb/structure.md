# Jargon Video Web - Tech Stack & Flow

## Packages

### Core
| Package | Version | Purpose |
|---------|---------|---------|
| `vite` | ^8.2.0 | Build tool + dev server |
| `svelte` | latest | UI framework (component-based, AI-friendly) |
| `@sveltejs/vite-plugin-svelte` | latest | Vite plugin for Svelte |

### Animation & Audio
| Package | Version | Purpose |
|---------|---------|---------|
| `gsap` | latest | Timeline-based animation engine |
| `howler` | latest | Audio player (play/pause/seek) |

### Legacy (kept but unused)
| Package | Purpose |
|---------|---------|
| `three` | 3D rendering (legacy page only) |
| `three-stdlib` | Three.js addons (legacy page only) |

---

## Flow Diagram

```
User opens browser → http://localhost:8017/example
    │
    ▼
main.js → router.js resolves path "/example" → loads pages/example/index.svelte
    │
    ▼
Svelte component mounts → creates #app container (9:16, 1080x1920)
    │
    ├── Howler.js loads voice.mp3
    │       │
    │       └── audio.currentTime = master clock
    │
    ├── GSAP timeline builds all animations mapped to seconds
    │       │
    │       └── tl.seek(audio.currentTime) → syncs animation to audio
    │
    ├── Subtitle checker runs every frame
    │       │
    │       └── if currentTime >= word.start && <= word.end → show word
    │
    └── Controls (play/pause/scrub/frame-step)
            │
            ├── Play/Pause → howler.play() / howler.pause() + tl.paused(!tl.paused())
            ├── Scrub → audio.seek(time) + tl.seek(time)
            └── Frame Step → ±0.0417s (1/24fps)
```

## Page Structure: pages/example/index.svelte

```svelte
<script>
  import gsap from 'gsap'
  import { Howl } from 'howler'
  
  let audio, timeline, canvas
  
  // Word-level subtitle data (to be generated later)
  const words = [/* ... */]
  
  onMount(() => {
    // Build GSAP timeline synced to script data
    timeline = gsap.timeline()
    
    // Load audio
    audio = new Howl({ src: ['/voice.mp3'] })
    
    // Animation loop - sync timeline to audio position
    function syncLoop() {
      if (audio.playing()) {
        timeline.seek(audio.duration() * progress)
      }
      requestAnimationFrame(syncLoop)
    }
  })
</script>

<canvas class="canvas-9x16" bind:this={canvas}>
  <!-- GSAP renders here -->
</canvas>

<div class="controls">
  <button on:click="{play}">▶</button>
  <input type="range" bind:value={progress} />
  <span>{currentTime.toFixed(2)}s / {duration.toFixed(2)}s</span>
  <button on:click="{prevFrame}">⏮</button>
  <button on:click="{nextFrame}">⏭</button>
</div>
```

## Animation Timeline

| Time | Section | GSAP Action |
|------|---------|-------------|
| 0-0.8s | Main | Text "parameter training LLM" fades in |
| 0.8-1s | Fade out | Section fades out |

## File Structure

```
videoweb/
├── pages/
│   └── example/
│       └── index.svelte      # Example page (minimal)
├── public/
│   └── ffmpeg/               # ffmpeg.wasm core (core-mt) + st/ (single-thread fallback)
├── main.js                   # Svelte app entry point
├── vite.config.js            # Vite config: svelte + COOP/COEP headers (utk ffmpeg.wasm MT)
├── svelte.config.js          # Svelte compiler options
└── package.json
```

## Render Flow (Lokal, 100% di browser)

```
User klik "🎬 Render Video"
    │
    ├── Capture: loop N× (N = duration × 24fps) seekTo(i/24) → html2canvas → JPEG(0.9)
    │            → simpan tiap frame ke IndexedDB (store 'frames', key f_{i}) → progress "Frame X/N"
    │
    ├── Encode: baca semua frame dari IndexedDB → ff.writeFile('frame_%05d.jpg') ke MEMFS
    │           → ffmpeg.wasm exec (libx264 h264, yuv420p, faststart) → progress % (event 'progress')
    │
    └── Selesai: ff.readFile('out.mp4') → Blob → auto-download + simpan ke IndexedDB (store 'videos')
                → sidebar "Hasil Render (local)" klik = download lagi
```

- **Tidak ada upload ke server.** Backend `server/render-api.js` sudah dihapus (vite.config hanya svelte + header COOP/COEP).
- `GET /ffmpeg/ffmpeg-core.*` di-serve dari `public/ffmpeg/` (32MB wasm MT; `st/` untuk fallback single-thread kalau `crossOriginIsolated` false).
- Header COOP/COEP (`same-origin` + `require-corp`) WAJIB untuk core multithread (SharedArrayBuffer).
- **Cek FFmpeg** (`checkFfmpeg()`): muat wasm sekali (lazy), simpan instance → tombol jadi "✓ FFmpeg siap".
- **Lanjutkan render**: frame disimpan ke IndexedDB incremental → kalau interrupted, reload → `checkPendingJob()` baca job meta + jumlah frame → tombol "▶ Lanjutkan render (dari frame N)".
- Video hasil disimpan di IndexedDB (store 'videos').

## Key Technical Decisions

1. **GSAP `.seek()`** — single method to jump animation to any second, synced to audio.currentTime
2. **Howler.js** — simple API: `play()`, `pause()`, `seek(time)`, `duration()`
3. **Svelte components** — each visual section (hook/llm/param/training/outro) is a separate `.svelte` component mounted conditionally based on timeline progress
4. **9:16 canvas** — CSS container with aspect-ratio: 9/16, max-height 100vh
5. **Render = html2canvas + ffmpeg.wasm lokal** — semua proses di browser user; server tidak terlibat
