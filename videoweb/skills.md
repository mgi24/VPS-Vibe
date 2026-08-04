## Rules project video web

Tugas anda adalah buat video motion grafis via web browser. Setiap project baru = folder `pages/{nama_project}`.

##PREPARING
1. copy dulu semua file dari `pages/example` ke folder baru itu baru diedit.

2. edit indexer.js bagian '''export function getSegmentFromPath(pathname)''' di parts[0] === 'example' ubah jadi nama folder project

3. baca file pages/output.srt untuk tau timestamp pengucapan kata subtitle

4. generate visual.md didalam folder pages/{nama_project}, isinya berformat table

Total Video Duration: {total_duration}s ({total_frames} frames)

##SEGMENT {number}
**Subtitle:** "{subtitle_text}"
**Timestamp:** HH:MM - HH:MM (frame X to Y)

| # | Visual | Status |
|---|--------|--------|
| 1. | visual pertama yang tampil & animasinya seperti apa | ⬜ |
| 2. | ... dst | ⬜ |

**Rules visual.md:**
- a. buat agar sebanyak mungkin ada animation, swipe, move dan dinamis
- b. buat segment singkat jangan bikin layar jadi crowded, kalau terasa full jadiin beda segmen
- c. bikin segmen SEBANYAK MUNGKIN, lebih banyak, lebih kecil per segmen LEBIH BAIK

##GENERATING
1. WAJIB todowrite sebanyak segment yang telah dibuat visual.md misal: create index1.svelte time 00:00 to 00:05, hal ini karena jika compacting task masih bisa continue
2. Create tool task, jangan lakukan generating di session utama opencode untuk menghemat context! description: index{segment num} generation, prompt: edit index{num}.svelte isi sesuai dengan segment{num} pada pages/visual.md. DILARANG langsung generate 1 pass karena rawan corrupt! Apply 1 visual dulu!, done? edit visual.md bagian statusnya dari X ke OK. jika compacting baca lagi visual.md untuk cek progress! subagent type: general 
  
3. WAJIB coret to do list setelah anda generate index.svelte segement itu, misal done index1.svelte maka langsung coret to do list -index1.svelte time 00:00 to 00:05-
4. lakukan generate per index.svelte secara seri, jangan pararel! 

##TESTS
Jika sudah selesai generate semua index.svelte, lakukan test suite:
1. setiap 100 frame lakukan test dengan camofox, baca /home/mamad/camoskills.md
2. total test = durasi*24/100, bulatkan kebawah, misal 60s = 14 test
3. bikin to do list untuk track progress test, lalu langsung coret setelah test selesai.
4. Test camofox hanya dilakukan ke model yang ada kemampuan multimodal, untuk model non multimodal, hanya gunakan web_fetch untuk akses 127.0.0.1:8017/{nama_project}/{frame} SAVE ke pages/{nama_project}/test_photo/{num frame}
5. untuk model multimodal, perhatikan apakah ada element yang keluar dari frame (top, down, left right), overlap. ignore jika kurang rapi, asal terbaca saja. JANGAN PERFEKSIONIS, user akan beri feedback.
6. jika test tidak passed, tulis di revisi.md, jangan fix dulu sampai test done
7. isi revision.md adalah tabel
frame | segment | comment
100 | 1 | text "Hello" terpotong di kiri 

##DEBUG
Hanya dijalankan jika test tidak passed.
1. Baca revision.md
2. bikin to do list sejumlah revision.md, langsung coret jika sudah fixed! baca kembali to do list jika compacted!
3. Setiap list, edit index{segmen bermasalah}.svelte
4. Lakukan test kembali seperti ##TESTS diatas namun save image ke pages/{nama_project}/test_photo/{num frame}revision{num revision}
5. looping edit file hingga fixed.

Rules:
1. Jangan render subtitle di video! hanya key visualisasi / B roll saja!
2. Jangan edit file diluar pages/{nama_project}! jika ada error akses 127.0.0.1/{nama_project}! langsung end task saja dan laporkan errornya!