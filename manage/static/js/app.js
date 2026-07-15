let authToken = localStorage.getItem('vpsm_token');
let currentTab = 'overview';
let openDropdown = null;
let dockerInterval = null;

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
  if (!authToken) { showLogin(); return false; }
  try {
    const res = await fetch('/api/me?token=' + encodeURIComponent(authToken));
    if (!res.ok) { authToken = null; localStorage.removeItem('vpsm_token'); showLogin(); return false; }
    const data = await res.json();
    if (!data.authenticated) { authToken = null; localStorage.removeItem('vpsm_token'); showLogin(); return false; }
    document.getElementById('sidebar-user').textContent = data.username;
    showApp();
    return true;
  } catch(e) {
    showLogin();
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
  switchTab('overview');
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
    showApp();
  } catch(err) {
    statusEl.style.display = 'none';
    errorEl.textContent = err.message;
    errorEl.style.display = 'block';
  }
}

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.tab === tab));
  document.querySelectorAll('#main-content > div[id^="tab-"]').forEach(el => el.style.display = 'none');
  const tabNames = {overview:'Overview', iptables:'iptables', services:'Services', docker:'Docker'};
  document.getElementById('main-header').textContent = tabNames[tab] || tab;
  const tabEl = document.getElementById('tab-' + tab);
  if (tabEl) tabEl.style.display = 'block';
  if (dockerInterval) { clearInterval(dockerInterval); dockerInterval = null; }
  if (tab === 'overview') loadOverview();
  if (tab === 'iptables') loadIptables();
  if (tab === 'services') loadService();
  if (tab === 'docker') { loadDocker(); dockerInterval = setInterval(loadDocker, 5000); }
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

document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', () => switchTab(el.dataset.tab));
});

document.getElementById('sidebar-logout').addEventListener('click', () => {
  authToken = null;
  localStorage.removeItem('vpsm_token');
  showLogin();
});

checkAuth();
