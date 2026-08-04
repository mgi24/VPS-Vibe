let authToken = localStorage.getItem('vpsm_token');
let currentTab = 'overview';
let openDropdown = null;
let dockerInterval = null;
let svcLogTimer = null;
let svcLogName = null;
let refreshInterval = null;

function startSessionRefresh() {
  if (refreshInterval) clearInterval(refreshInterval);
  refreshInterval = setInterval(() => {
    if (authToken) {
      fetch('/api/refresh?token=' + encodeURIComponent(authToken)).catch(() => {});
    } else {
      clearInterval(refreshInterval);
      refreshInterval = null;
    }
  }, 5 * 60 * 1000); // every 5 minutes
}

function stopSessionRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function escapeAttr(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function unescapeAttr(s) {
  if (!s) return '';
  return s.replace(/&#39;/g,"'").replace(/&quot;/g,'"').replace(/&amp;/g,'&');
}

async function checkAuth() {
  if (!authToken) { showLogin(); stopSessionRefresh(); return false; }
  try {
    const res = await fetch('/api/me?token=' + encodeURIComponent(authToken));
    if (!res.ok) { authToken = null; localStorage.removeItem('vpsm_token'); showLogin(); stopSessionRefresh(); return false; }
    const data = await res.json();
    if (!data.authenticated) { authToken = null; localStorage.removeItem('vpsm_token'); showLogin(); stopSessionRefresh(); return false; }
    document.getElementById('sidebar-user').textContent = data.username;
    startSessionRefresh();
    showApp();
    return true;
  } catch(e) {
    showLogin();
    stopSessionRefresh();
    return false;
  }
}

function showLogin() {
  document.getElementById('login-overlay').classList.add('show');
  document.getElementById('app').classList.remove('show');
  document.getElementById('login-username').focus();
}

function showApp() {
  document.getElementById('login-overlay').classList.remove('show');
  document.getElementById('app').classList.add('show');
  parseHash();
}

async function doLogin(username, password) {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  const statusEl = document.getElementById('login-status');
  const errorEl = document.getElementById('login-error');
  statusEl.style.display = 'block';
  statusEl.innerHTML = '<span class="spinner"></span> Authenticating...';
  errorEl.style.display = 'none';
  try {
    const res = await fetch('/api/login', { method: 'POST', body: formData });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || 'Login failed');
    }
    const data = await res.json();
    authToken = data.token;
    localStorage.setItem('vpsm_token', authToken);
    statusEl.style.display = 'none';
    document.getElementById('sidebar-user').textContent = username;
    startSessionRefresh();
    showApp();
  } catch(err) {
    statusEl.style.display = 'none';
    errorEl.textContent = err.message;
    errorEl.style.display = 'block';
  }
}

function switchTab(tab, explorerPath) {
  currentTab = tab;
  document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.tab === tab));
  document.querySelectorAll('#main-content > div[id^="tab-"]').forEach(el => el.style.display = 'none');
  const tabNames = {explorer:'Explorer', iptables:'iptables', services:'Services', docker:'Docker'};
  document.getElementById('main-header').textContent = tabNames[tab] || tab;
  document.title = (tabNames[tab] || tab) + ' - VPS Manager';
  const tabEl = document.getElementById('tab-' + tab);
  if (tabEl) tabEl.style.display = 'block';
  if (dockerInterval) { clearInterval(dockerInterval); dockerInterval = null; }
  if (typeof svcLogTimer !== 'undefined' && svcLogTimer) { clearInterval(svcLogTimer); svcLogTimer = null; }
  svcLogName = null;

  // Update URL without triggering navigation
  let hashPath = tab === 'explorer' ? '/explorer' + ((explorerPath || '/') === '/' ? '' : (explorerPath || '/').replace(/\/+$/, '')) : '/' + tab;
  if (!hashPath || hashPath === '/explorer') hashPath += '/';
  history.pushState({tab, explorerPath: explorerPath || '/'}, '', '#/' + hashPath.replace(/^\/+/,''));

  if (tab === 'explorer') loadExplorer(explorerPath || '/');
  if (tab === 'iptables') loadIptables();
  if (tab === 'services') loadService();
  if (tab === 'docker') { loadDocker(); dockerInterval = setInterval(loadDocker, 5000); }
}

function parseHash() {
  console.log('[app] parseHash called, hash:', window.location.hash);
  const hash = window.location.hash;
  // Match #/explorer/path/to/dir or #/iptables etc. (supports both #/ and without, and double slashes)
  const match = hash.match(/^#?\/+\/?(explorer|iptables|services|docker)(\/.*)?$/i);
  console.log('[app] parseHash match:', match ? [match[1], match[2]] : 'NO MATCH');
  if (match) {
    const tab = match[1].toLowerCase();
    let explorerPath = '/';
    if (tab === 'explorer' && match[2]) {
      // Remove leading slash from path segment and normalize
      explorerPath = match[2].replace(/\/+$/, '') || '/';
      if (!explorerPath.startsWith('/')) explorerPath = '/' + explorerPath;
    }
    currentTab = tab;
    document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.tab === tab));
    document.querySelectorAll('#main-content > div[id^="tab-"]').forEach(el => el.style.display = 'none');
    const tabNames = {explorer:'Explorer', iptables:'iptables', services:'Services', docker:'Docker'};
    document.getElementById('main-header').textContent = tabNames[tab] || tab;
    document.title = (tabNames[tab] || tab) + ' - VPS Manager';
    const tabEl = document.getElementById('tab-' + tab);
    if (tabEl) tabEl.style.display = 'block';
    if (dockerInterval && tab !== 'docker') { clearInterval(dockerInterval); dockerInterval = null; }
    if (typeof svcLogTimer !== 'undefined' && svcLogTimer && tab !== 'services') { clearInterval(svcLogTimer); svcLogTimer = null; }
    svcLogName = null;
    if (tab === 'explorer') loadExplorer(explorerPath);
    else if (tab === 'iptables') loadIptables();
    else if (tab === 'services') loadService();
    else if (tab === 'docker') { loadDocker(); dockerInterval = setInterval(loadDocker, 5000); }
    return;
  }

  // Default to explorer
  switchTab('explorer', '/');
}

function toggleDropdown(e, safeId) {
  e.stopPropagation();
  const menu = document.getElementById('svc-drop-' + safeId);
  if (openDropdown && openDropdown !== menu) openDropdown.classList.remove('show');
  menu.classList.toggle('show');
  openDropdown = menu.classList.contains('show') ? menu : null;
}

document.addEventListener('click', () => {
  if (openDropdown) { openDropdown.classList.remove('show'); openDropdown = null; }
});

document.getElementById('login-btn').addEventListener('click', () => {
  const u = document.getElementById('login-username').value.trim();
  const p = document.getElementById('login-password').value;
  if (!u || !p) {
    document.getElementById('login-error').textContent = 'Username and password required';
    document.getElementById('login-error').style.display = 'block';
    return;
  }
  document.getElementById('login-error').style.display = 'none';
  doLogin(u, p);
});

document.getElementById('login-password').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.getElementById('login-btn').click();
});

// Nav item click handlers use pushState for URL routing
document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', () => {
    const tab = el.dataset.tab;
    const hashPath = tab === 'explorer' ? '/explorer/' : '/' + tab;
    history.pushState({tab}, '', '#/' + hashPath.replace(/^\/+/,''));
    switchTab(tab, tab === 'explorer' ? '/' : undefined);
  });
});

document.getElementById('sidebar-logout').addEventListener('click', () => {
  authToken = null;
  localStorage.removeItem('vpsm_token');
  stopSessionRefresh();
  showLogin();
});

// Handle browser back/forward buttons
window.addEventListener('popstate', (e) => {
  const state = e.state;
  if (state && state.tab) {
    currentTab = state.tab;
    document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.tab === state.tab));
    document.querySelectorAll('#main-content > div[id^="tab-"]').forEach(el => el.style.display = 'none');
    const tabNames = {explorer:'Explorer', iptables:'iptables', services:'Services', docker:'Docker'};
    document.getElementById('main-header').textContent = tabNames[state.tab] || state.tab;
    document.title = (tabNames[state.tab] || state.tab) + ' - VPS Manager';
    const tabEl = document.getElementById('tab-' + state.tab);
    if (tabEl) tabEl.style.display = 'block';
    if (dockerInterval && state.tab !== 'docker') { clearInterval(dockerInterval); dockerInterval = null; }
    if (typeof svcLogTimer !== 'undefined' && svcLogTimer && state.tab !== 'services') { clearInterval(svcLogTimer); svcLogTimer = null; }
    svcLogName = null;
    if (state.tab === 'explorer') loadExplorer(state.explorerPath || '/');
    else if (state.tab === 'iptables') loadIptables();
    else if (state.tab === 'services') loadService();
    else if (state.tab === 'docker') { loadDocker(); dockerInterval = setInterval(loadDocker, 5000); }
  } else {
    parseHash();
  }
});

// Handle initial hash on load
if (window.location.hash && window.location.hash !== '#/') {
  // Will be handled by checkAuth -> showApp -> parseHash
} else if (!window.location.hash) {
  // No hash, default to explorer
  setTimeout(() => {
    history.replaceState(null, '', '#/explorer');
  }, 0);
}

checkAuth();
