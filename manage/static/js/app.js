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
  parsePath();
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

function getPathFromLocation() {
  let p = window.location.pathname;
  if (p.length > 1) p = p.replace(/\/+$/, '');
  return p || '/';
}

function urlForTab(tab, explorerPath) {
  if (tab === 'explorer') {
    const p = (explorerPath || '/') === '/' ? '' : (explorerPath || '/').replace(/^\/+|\/+$/g, '');
    return '/explorer' + (p ? '/' + p : '/');
  }
  return '/' + tab;
}

function routeFromPath(path) {
  if (path === '/' || path === '') return { tab: 'explorer', explorerPath: '/' };
  let m = path.match(/^\/explorer(\/.*)?$/i);
  if (m) {
    let ep = m[1] ? m[1].replace(/\/+$/, '') : '';
    if (!ep) return { tab: 'explorer', explorerPath: '/' };
    if (!ep.startsWith('/')) ep = '/' + ep;
    return { tab: 'explorer', explorerPath: ep };
  }
  m = path.match(/^\/(docker|services|iptables|wireguard)$/i);
  if (m) return { tab: m[1].toLowerCase(), explorerPath: '/' };
  return { tab: 'explorer', explorerPath: '/' };
}

function showTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.tab === tab));
  document.querySelectorAll('#main-content > div[id^="tab-"]').forEach(el => el.style.display = 'none');
  const tabNames = {explorer:'Explorer', iptables:'iptables', services:'Services', docker:'Docker', wireguard:'WireGuard'};
  document.getElementById('main-header').textContent = tabNames[tab] || tab;
  document.title = (tabNames[tab] || tab) + ' - VPS Manager';
  const tabEl = document.getElementById('tab-' + tab);
  if (tabEl) tabEl.style.display = 'block';
  if (dockerInterval && tab !== 'docker') { clearInterval(dockerInterval); dockerInterval = null; }
  if (svcLogTimer && tab !== 'services') { clearInterval(svcLogTimer); svcLogTimer = null; }
  if (tab !== 'wireguard') stopWgPing();
  svcLogName = null;
}

function loadTabContent(tab, explorerPath) {
  if (tab === 'explorer') {
    currentPath = explorerPath || '/';
    renderExplorer(currentPath);
    clearPreview();
  } else if (tab === 'iptables') {
    loadIptables();
  } else if (tab === 'services') {
    loadService();
  } else if (tab === 'docker') {
    loadDocker();
    dockerInterval = setInterval(loadDocker, 5000);
  } else if (tab === 'wireguard') {
    loadWireguard();
  }
}

function switchTab(tab, explorerPath, pushUrl) {
  showTab(tab);
  const url = urlForTab(tab, explorerPath);
  if (pushUrl && window.location.pathname !== url) {
    history.pushState({tab, explorerPath: explorerPath || '/'}, '', url);
  }
  loadTabContent(tab, explorerPath);
}

function parsePath() {
  const locationPath = getPathFromLocation();
  let { tab, explorerPath } = routeFromPath(locationPath);

  // Legacy hash-based URL support: /#/services, /explorer#/docker, etc.
  const hm = window.location.hash.match(/^#?\/+\/?(explorer|iptables|services|docker|wireguard)(\/.*)?$/i);
  if (hm) {
    const htab = hm[1].toLowerCase();
    let hep = '/';
    if (htab === 'explorer' && hm[2]) {
      hep = hm[2].replace(/\/+$/, '') || '/';
      if (!hep.startsWith('/')) hep = '/' + hep;
    }
    const url = urlForTab(htab, hep);
    history.replaceState({tab: htab, explorerPath: hep}, '', url);
    tab = htab;
    explorerPath = hep;
  } else if (locationPath === '/') {
    history.replaceState({tab: 'explorer', explorerPath: '/'}, '', urlForTab('explorer', '/'));
  }

  switchTab(tab, explorerPath, false);
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
    switchTab(tab, '/', true);
  });
});

document.getElementById('sidebar-logout').addEventListener('click', () => {
  authToken = null;
  localStorage.removeItem('vpsm_token');
  stopSessionRefresh();
  showLogin();
});

// Handle browser back/forward buttons
window.addEventListener('popstate', () => {
  parsePath();
});

checkAuth();
