import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

function ffmpegHeaders() {
  return {
    name: 'ffmpeg-wasm-headers',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
        res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [svelte(), ffmpegHeaders()],
  server: {
    port: 8017,
    allowedHosts: ['video.misbahwork.my.id'],
  },
});
