# Kamus AI per Hari — Visual Design

## Overview
- **Durasi total**: ~62 detik (SRT 00:00–01:01)
- **Format**: 9:16 vertical (1080×1920), motion graphics modern tech style
- **Tema visual**: dark background dengan aksen neon biru/cyan, teks besar bold center, ikon sederhana animasi smooth
- **Font**: Inter / Poppins Bold untuk judul, Medium untuk body
- **Warna utama**: `#0D0D1A` (bg gelap), `#00BFFF` (cyan/primary), `#7AE582` (hijau accent), `#FFD77A` (kuning accent)

---

## Section 1 — Intro (0s – 3.6s)
**Audio**: "Tiga kamus AI per hari."

- **Visual**: Judul besar di tengah layar, muncul kata per kata dengan animasi bounce/fade:
  - `TIGA` → muncul scale up + glow cyan
  - `KAMUS` → fade in dari bawah
  - `AI` → teks neon berkedip singkat (neon flicker)
  - `PER HARI.` → slide in dari kanan
- **Background**: gelap dengan grid halus animasi subtle (garis grid bergerak perlahan)
- **Elemen GSAP**: `.fromTo('.intro-word', { autoAlpha:0, y:40 }, { autoAlpha:1, y:0, duration:0.5, ease:'back.out(2)' })` per kata dengan stagger 0.3s

---

## Section 2 — LLM (3.6s – 11.3s)
**Audio**: "Yang pertama, LLM, Large Language Model. Ini AI itu mau apapun inputnya, outputnya itu cuma teks doang ya."

- **Visual**: Slide konsep LLM dengan diagram sederhana:
  - Ikon kotak input → panah ke tengah (logo/model) → panah ke kotak output
  - Input: ikon keyboard `⌨️` atau simbol teks `[TEXT]`
  - Output: ikon dokumen `📄` atau simbol teks `[TEXT]`
  - Teks label besar: **LLM** di atas, subtitle "Large Language Model" di bawahnya (font lebih kecil)
- **Animasi**: 
  - Kotak input muncul dari kiri → panah mengalir ke model → kotak output muncul dari kanan
  - Semua elemen fade in bertahap
  - Highlight pada kata "TEKS DOANG YA" dengan efek underline animasi + warna kuning

---

## Section 3 — Multimodal (11.3s – 26.6s)
**Audio**: "Kedua, multimodal. Umumnya LLM cuma bisa inputnya itu teks doang ya. Nah, kalau yang support multimodal ini, dia bisa dikasih input gambar atau bahkan beberapa model bisa input audio sekalian."

- **Visual**: Slide evolusi dari LLM → Multimodal:
  - Teks "MULTIMODAL" besar di tengah (font bold, warna hijau neon)
  - Di bawahnya muncul 3 ikon secara bertahap:
    - `🖼️ GAMBAR` — muncul dengan scale up effect
    - `🎤 AUDIO` — muncul dengan pulse animation
    - `⌨️ TEKS` — muncul lebih kecil (karena LLM sudah support)
  - Diagram menunjukkan satu model menerima multiple input types
- **Animasi**: 
  - Ikon-ikon muncul dari bawah ke atas dengan stagger
  - Background sedikit berubah: grid glow berwarna hijau tipis
  - Efek "glow ring" di tengah yang memancar saat semua ikon muncul

---

## Section 4 — Cara Input (26.6s – 36s)
**Audio**: "Nah, cara inputnya itu gimana? Gimana? Ya, gambar atau audionya itu dibikin teks gitu ya. Kalau yang biasanya itu dibikin base 64 gitu sih."

- **Visual**: Ilustrasi proses encoding:
  - Ikon gambar → panah transformasi → ikon teks
  - Teks kode kecil bergulir: `base64://...` atau `data:image/png;base64,...`
  - Animasi "transform": ikon gambar berubah bentuk menjadi ikon teks (morph effect)
- **Animasi**: 
  - Gambar di kiri, panah di tengah berkedip (seperti proses), teks muncul di kanan
  - Teks base64 bergulir seperti matrix rain (tapi lebih halus dan lambat)
  - Highlight kata "BASE 64" dengan efek typing animation

---

## Section 5 — Thinking (36s – 51.2s)
**Audio**: "Ketiga, thinking, mikir. Ini sebenarnya cuma ngasih kesempatan AI-nya buat kasih alternatif jawaban, nggak cuma satu ya. Jadi sebelum ngasih jawaban final, dia itu bisa milih kira-kira sih yang probabilitas paling tinggi buat bener."

- **Visual**: Konsep "thinking process" dengan visual branch/pohon keputusan:
  - Di tengah: ikon otak/robot sederhana 🤖 atau logo AI
  - Dari pusat muncul beberapa cabang (garis tipis) menuju kotak-kotak jawaban alternatif
  - Setiap kotak berisi teks placeholder "Jawaban A", "Jawaban B", "Jawaban C"
  - Satu kotak yang paling benar di-highlight dengan border hijau + glow
  - Teks besar: **THINKING** di atas, subtitle "Mikir" di bawahnya
- **Animasi**: 
  - Cabang-cabang muncul dari pusat seperti radar/spider web
  - Kotak jawaban fade in satu per satu
  - Kotak terpilih (probabilitas tertinggi) mendapat pulse effect + border glow
  - Efek "probability meter": bar kecil menunjukkan persentase di setiap kotak

---

## Section 6 — Thinking Off (51.2s – 58.3s)
**Audio**: "Kalau dimatikan gimana? Ya, tetap dijawab sih, tapi kemungkinan gagalnya lebih tinggi. Soalnya cuma dikasih kesempatan satu. Satu kali buat ngasih jawaban."

- **Visual**: Kontras thinking ON vs OFF — layar terbelah dua:
  - **Garis pembagi** vertikal di tengah, gradient kuning→merah dengan glow
  - **Kiri (Thinking ON)**:
    - Label "THINKING ON" di atas (hijau neon)
    - Ikon 🧠 otak besar di tengah
    - 3 path jawaban muncul bertahap:
      - `✓ Jawaban A (45%)` — hijau, border glow hijau
      - `✓ Jawaban B (35%)` — kuning, border glow kuning
      - `✓ Jawaban C (20%)` — abu-abu, border tipis
    - Centang ✅ besar di bawah (hijau neon)
  - **Kanan (Thinking OFF)**:
    - Label "THINKING OFF" di atas (merah neon)
    - Satu kotak jawaban muncul langsung 📄 + teks "Satu Jawaban Langsung"
    - Kotak sedikit redup/desaturated (opacity 0.75, border merah tipis)
    - Tanda seru ⚠️ besar (merah)
    - Teks "GAGAL LEBIH TINGGI" di bawah — merah/oranye, bold, underline animasi
- **Animasi**: 
  - `split-line`: scaleX dari 0 ke 1, muncul dari tengah ke samping (duration 0.6s)
  - `.think-on-side`: fade in + slide dari kiri (autoAlpha: 0→1, x: -40→0)
  - `.think-on-ai`: scale dari 0.7 ke 1 (back.out ease)
  - `.think-on-paths`: stagger muncul satu per satu (y: 20→0, gap 0.2s)
  - `.think-off-side`: fade in + slide dari kanan (autoAlpha: 0→1, x: 40→0)
  - `.single-answer-box`: scale dari 0.5 ke 1, muncul langsung tanpa proses berpikir
  - `.warning-icon`: fade in + slide dari atas (y: -20→0)
  - `.fail-text`: scale + fade in dengan elastic ease (seperti highlight lainnya)
  - `.side-label-on` / `.side-label-off`: fade in bertahap (y: -20→0, stagger 0.3s)

---

## Section 7 — Outro (58.3s – 61.6s)
**Audio**: "Part lainnya cek di komen ya."

- **Visual**: Closing screen sederhana:
  - Teks besar: **"KAMUS AI PER HARI"** (judul seri)
  - Subtitle: "Part lainnya cek di komen 👇" dengan panah menunjuk ke bawah
  - Icon komentar 💬 muncul dengan bounce effect
  - Background kembali gelap dengan grid halus seperti intro
- **Animasi**: 
  - Teks judul fade in dari atas
  - Panah 👇 bounce turun naik 2x
  - Fade out perlahan untuk transition

---

## Technical Notes untuk Implementasi

### Struktur Section (Svelte)
```svelte
<!-- Di index.svelte -->
<div class="sec sec-intro">...</div>
<div class="sec sec-llm">...</div>
<div class="sec sec-multimodal">...</div>
<div class="sec sec-input">...</div>
<div class="sec sec-thinking">...</div>
<div class="sec sec-thinking-off">...</div>
<div class="sec sec-outro">...</div>
```

### Timeline GSAP (pseudocode)
```javascript
tl.set('.sec', { autoAlpha: 0, display:'none' })
  .set('.sec-intro', { autoAlpha:1, display:'flex' }, 0)
  // intro kata per kata stagger
  
  .to('.sec-intro', { autoAlpha:0, duration:0.3 }, 3.2)
  
  .set('.sec-llm', { autoAlpha:1, display:'flex' }, 3.6)
  // animasi diagram LLM input→output
  
  .to('.sec-llm', { autoAlpha:0, duration:0.3 }, 11)
  
  .set('.sec-multimodal', { autoAlpha:1, display:'flex' }, 11.3)
  // ikon gambar/audio/teks muncul bertahap
  
  // ... dst untuk setiap section
```

### Audio (Howler.js)
- Load SRT audio file: `new Howl({ src: ['./kamusai.mp3'], volume: 0.8 })`
- Sync dengan manual clock: `audio.seek(t)` saat seekTo
- Play/pause sync dengan isPlaying flag

---

## File yang Dibutuhkan
1. `pages/kamusai/index.svelte` — stage + timeline GSAP (setelah visual.md disetujui)
2. Audio file: `pages/kamusai/audio.mp3` (voiceover dari SRT)
3. Tidak perlu aset gambar eksternal — semua ikon pakai emoji/unicode atau CSS shapes
