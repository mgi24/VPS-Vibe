<script>
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';
  import VideoUI from './src/components/VideoUI.svelte';

  let currentPage = null;
  let currentPath = '';
  let pageProps = {};

  const controller = writable({
    stageReady: false,
    W: 1080, H: 1920, fps: 24, duration: 1,
    canvasEl: null, wrapEl: null,
    seekTo: null, play: null, pause: null, playPause: null,
    getTime: null, getDuration: null, isPlaying: null,
    setSpeed: null, stepFrame: null, reset: null, exportFrame: null, restoreLayout: null,
    _previewPath: 'kamusai',
  });

  // Dynamic page loader using Vite's glob imports
  const pageModules = import.meta.glob('./pages/*/index.svelte', { eager: false });
  const segmentModules = import.meta.glob('./pages/kamusai2/index{1..7}.svelte', { eager: false });

  console.log('Available pages:', Object.keys(pageModules));
  console.log('Available segments:', Object.keys(segmentModules));

  // Extract valid page slugs from glob keys
  const validPages = new Set();
  for (const key of Object.keys(pageModules)) {
    const match = key.match(/\.\/pages\/([^/]+)\/index\.svelte$/);
    if (match) {
      validPages.add(match[1]);
    }
  }

  // Extract valid segment slugs from glob keys
  const validSegments = new Map();
  for (const key of Object.keys(segmentModules)) {
    const match = key.match(/\.\/pages\/kamusai2\/index(\d+)\.svelte$/);
    if (match) {
      validSegments.set(match[1], key);
    }
  }

  console.log('Valid page slugs:', Array.from(validPages));
  console.log('Valid segments:', Array.from(validSegments.keys()));

  async function loadPage(pathname) {
    currentPath = pathname;
    const cleanPath = pathname.replace(/^\/+|\/+$/g, '');
    
    // Root path: redirect to example
    if (!cleanPath || cleanPath === '/') {
      pageProps = {};
      $controller._previewPath = 'example';
      return './pages/example/index.svelte';
    }

    const parts = cleanPath.split('/');
    
    // Check for /kamusai2 (full combined timeline) or /kamusai2/{segment} pattern (1-7)
    if (parts[0] === 'kamusai2') {
      let segmentStr;
      if (parts.length >= 2 && parts[1]) {
        segmentStr = parts[1];
      } else {
        // No segment number - load full combined timeline
        pageProps = {};
        $controller._previewPath = 'kamusai2';
        return './pages/kamusai2/index.svelte';
      }
      if (validSegments.has(segmentStr)) {
        const key = validSegments.get(segmentStr);
        console.log('Loading segment:', key);
        pageProps = {};
        $controller._previewPath = 'kamusai2';
        return key;
      }
    }

    // Check for /{slug}/{frameNumber} pattern
    if (parts.length >= 2) {
      const slug = parts[0];
      const frameStr = parts[1];
      
      if (validPages.has(slug)) {
        const frameNum = parseInt(frameStr, 10);
        if (!isNaN(frameNum) && frameNum >= 0) {
          // Frame preview mode: /kamusai/345
          pageProps = { showFrame: frameNum };
          $controller._previewPath = slug;
          return `./pages/${slug}/index.svelte`;
        }
      }
    }

    // Normal page route
    if (!validPages.has(cleanPath)) {
      console.warn('Page not found:', cleanPath, 'Available pages:', Array.from(validPages));
      pageProps = {};
      return null;
    }

    const key = `./pages/${cleanPath}/index.svelte`;
    console.log('Loading page:', key);
    pageProps = {};
    $controller._previewPath = cleanPath.split('/')[0];
    
    if (pageModules[key]) {
      return key;
    }
    return null;
  }

  async function renderPage(pathname) {
    const key = await loadPage(pathname);
    
    if (key === null) {
      currentPage = null;
      console.log('No page to render, showing 404');
      return;
    }

    try {
      const loader = segmentModules[key] ?? pageModules[key];
      if (!loader) {
        console.error('Module not found for key:', key);
        currentPage = null;
        return;
      }
      const module = await loader();
      currentPage = module.default;
      console.log('Page loaded successfully:', key);
    } catch (e) {
      console.error('Failed to load page:', key, e);
      currentPage = null;
    }
  }

  onMount(async () => {
    await renderPage(window.location.pathname);
  });

  // Listen for popstate (browser back/forward)
  window.addEventListener('popstate', async () => {
    console.log('Popstate event, path:', window.location.pathname);
    await renderPage(window.location.pathname);
  });
</script>

{#if currentPage}
  <svelte:component this={currentPage} controller={controller} {...pageProps} />
{:else}
  <div class="not-found">
    <h1>404</h1>
    <p>Halaman tidak ditemukan.</p>
    <p><a href="/">Kembali ke beranda</a></p>
  </div>
{/if}

{#if $controller.stageReady && !pageProps.showFrame}
  <VideoUI {controller} />
{/if}

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    background: #0D0D1A;
    overflow-x: hidden;
  }

  .not-found {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    color: #fff;
    font-family: 'Inter', sans-serif;
    text-align: center;
  }

  .not-found h1 {
    font-size: 96px;
    font-weight: 900;
    color: #FF4444;
    margin-bottom: 20px;
  }

  .not-found p {
    font-size: 32px;
    color: #aaa;
    margin-bottom: 40px;
  }

  .not-found a {
    font-size: 28px;
    color: #00BFFF;
    text-decoration: none;
  }

  .not-found a:hover {
    text-decoration: underline;
  }
</style>
