## Rules project video web

Buat video motion grafis via web browser. Setiap project baru = folder `pages/{nama}/index.svelte`.
copy dulu dari `pages/example/index.svelte` ke folder baru itu baru diedit.

## Arsitektur

- `App.svelte` membuat `controller` (Svelte `writable` store) berisi API stage → di-pass ke page + `src/components/VideoUI.svelte` (UI: player controls + render sidebar).
- `pages/{nama}/index.svelte` HANYA grafik: stage + timeline GSAP + playback. Di `onMount` daftarkan API ke controller: `controller.update((c) => ({ ...c, stageReady:true, W, H, fps, duration, canvasEl, wrapEl, seekTo, play, pause, playPause, getTime:()=>manualT, getDuration:()=>duration, isPlaying:()=>isPlaying, setSpeed, stepFrame, exportFrame, restoreLayout }))`. `onDestroy` set `stageReady:false`.
- JANGAN buat UI (tombol, sidebar, input) di page — taruh di `VideoUI` dan akses stage via `$controller`.

## Stack

Svelte 5 + GSAP + Howler (bukan Three.js untuk 2D). `vite.config.js` pakai `import { svelte } from '@sveltejs/vite-plugin-svelte'`. `package.json` `"type": "module"`.

## Clock (WAJIB manual, JANGAN pakai tl API untuk playback)

- Tween `repeat:-1` (infinite) korup duration timeline → `tl.time()`/`tl.progress()` meledak jadi ratusan juta → section stuck hidden.
- Manual clock: `manualT` di-increment rAF (`dt = (ts-lastTs)/1000 * speed`), lalu `tl.seek(manualT)` tiap rAF. `play()` hanya `isPlaying=true; lastTs=performance.now()`. `pause()` hanya `isPlaying=false`.
- `seekTo(t)`: `manualT=t; tl.seek(t); if (audio?.playing()) audio.seek(t)`.
- Frame step: `seekTo(manualT + dir*FRAME)`, `FRAME=1/24`.
- Speed via `dt*speed`, bukan `tl.timeScale()`.
- Jangan `tl.play()`/`tl.pause()`/`tl.progress()` untuk playback.

## GSAP onUpdate

Jangan `onUpdate: (e) => e.target...` (e undefined → crash, timeline tidak jadi). Pakai `onUpdate: function () { this.targets()[0].innerHTML = ... }`.

## Layout stage 9:16

- Stage TETAP `width:1080px; height:1920px`, `transform-origin: top left`, `overflow:hidden`. Bungkus `.stage-wrap` (overflow:hidden) yang di-resize `wrap.style.width = W*scale; height = H*scale`, stage di-scale `canvasEl.style.transform = scale(${scale})`.
- JANGAN resize width/height stage (font di dalam tidak ikut scale). JANGAN `line-height:0` di wrap (waris ke stage → teks collapse). JANGAN `max-height`/`aspect-ratio` di stage.
- JANGAN `style={obj}` object di Svelte 5 untuk top/left — pakai string CSS (`style="top:18%;left:8%"` dari array per-index di `{#each}`).
- JANGAN `:nth-of-type()` untuk posisi — hitung per jenis tag, bukan class. Posisi per-element via style string index.

## Section switching

`gsap.set('.sec', { autoAlpha: 0, display:'none' })` + `.set('.sec-x', { autoAlpha: 1, display:'flex' }, t)` + fade out. autoAlpha pakai visibility:hidden.

## Build & verifikasi

- Build: `npx vite build` harus exit 0.
- Verifikasi di browser: play → `getTime()` ≈ wall clock; seek tiap section → elemen tampil sesuai naskah.
