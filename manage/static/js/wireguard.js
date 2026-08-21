var wgPingTimer = null;
var wgData = null;

function stopWgPing() {
  if (wgPingTimer) { clearInterval(wgPingTimer); wgPingTimer = null; }
}

async function loadWireguard() {
  const el = document.getElementById('tab-wireguard');
  if (!el) return;
  el.innerHTML = '<div class="wg-empty"><span class="spinner"></span> Loading...</div>';
  try {
    const res = await fetch('/api/wg?token=' + encodeURIComponent(authToken));
    if (!res.ok) throw new Error('HTTP ' + res.status);
    wgData = await res.json();
    renderWireguard(el, wgData);
  } catch (e) {
    el.innerHTML = '<div class="wg-empty">Failed to load WireGuard status</div>';
  }
}

async function wgSetup() {
  const btn = document.getElementById('wg-setup-btn');
  const endpoint = document.getElementById('wg-endpoint').value.trim();
  if (!endpoint) { alert('Endpoint is required (host:port)'); return; }
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Creating...';
  try {
    const res = await fetch('/api/wg/setup?token=' + encodeURIComponent(authToken), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ endpoint })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Setup failed');
    loadWireguard();
  } catch (e) {
    alert(e.message);
    btn.disabled = false;
    btn.textContent = 'Create Server';
  }
}

async function wgPower(action) {
  try {
    const res = await fetch('/api/wg/power?token=' + encodeURIComponent(authToken), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    loadWireguard();
  } catch (e) { alert(e.message); }
}

async function wgAddPeer() {
  const input = document.getElementById('wg-peer-name');
  const btn = document.getElementById('wg-add-btn');
  const name = input.value.trim();
  if (!name) { alert('Peer name is required'); return; }
  btn.disabled = true;
  try {
    const res = await fetch('/api/wg/peers?token=' + encodeURIComponent(authToken), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to add peer');
    wgShowConfigModal(data.config, 'wg-manage_' + data.peer.name + '.conf');
    loadWireguard();
  } catch (e) { alert(e.message); btn.disabled = false; }
}

async function wgDeletePeer(ip, name) {
  if (!confirm('Delete peer "' + name + '" (' + ip + ')?')) return;
  try {
    const res = await fetch('/api/wg/peers?token=' + encodeURIComponent(authToken) + '&ip=' + encodeURIComponent(ip), { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to delete');
    loadWireguard();
  } catch (e) { alert(e.message); }
}

async function wgDownloadConfig(ip) {
  try {
    const res = await fetch('/api/wg/peer-config?token=' + encodeURIComponent(authToken) + '&ip=' + encodeURIComponent(ip));
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    const blob = new Blob([data.content], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = data.filename;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) { alert(e.message); }
}

async function wgUpdateStatus() {
  if (!wgData || !wgData.initialized || !wgData.peers.length) return;
  try {
    const res = await fetch('/api/wg/ping?token=' + encodeURIComponent(authToken));
    if (!res.ok) return;
    const data = await res.json();
    for (const [ip, online] of Object.entries(data.status)) {
      const cell = document.getElementById('wg-status-' + ip.replaceAll('.', '_'));
      if (cell) {
        cell.className = 'wg-badge ' + (online ? 'online' : 'offline');
        cell.textContent = online ? 'Online' : 'Offline';
      }
    }
  } catch (e) { /* ignore transient errors */ }
}

function startWgPing() {
  stopWgPing();
  wgUpdateStatus();
  wgPingTimer = setInterval(wgUpdateStatus, 2000);
}

function wgShowConfigModal(content, filename) {
  let overlay = document.getElementById('wg-config-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'wg-config-overlay';
    overlay.className = 'rule-form-overlay';
    overlay.innerHTML = `
      <div class="rule-form">
        <h4 id="wg-config-title"></h4>
        <textarea id="wg-config-text" readonly rows="14"></textarea>
        <div class="form-row" style="margin-top:12px">
          <button id="wg-config-download">Download .conf</button>
          <button class="cancel" id="wg-config-close">Close</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.querySelector('#wg-config-close').addEventListener('click', () => overlay.classList.remove('show'));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.classList.remove('show'); });
  }
  overlay.querySelector('#wg-config-title').textContent = filename;
  overlay.querySelector('#wg-config-text').value = content;
  overlay.querySelector('#wg-config-download').onclick = () => {
    const blob = new Blob([content], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  overlay.classList.add('show');
}

function renderWireguard(el, data) {
  if (!data.initialized) {
    el.innerHTML = `
      <div class="wg-card">
        <h3>WireGuard Manage Server</h3>
        <p class="wg-note">Config <code>/etc/wireguard/wg-manage.conf</code> belum ada. Buat server untuk jaringan manage <code>10.8.0.0/24</code> (server: <code>10.8.0.1</code>, port UDP <code>${data.port}</code>).</p>
        <p class="wg-note">Pastikan gateway publik sudah forward UDP ${data.port} ke VPS ini.</p>
        <div class="wg-setup-row">
          <input type="text" id="wg-endpoint" placeholder="Endpoint (host:port)" value="wg.misbahwork.my.id:${data.port}">
          <button id="wg-setup-btn">Create Server</button>
        </div>
      </div>`;
    document.getElementById('wg-setup-btn').addEventListener('click', wgSetup);
    stopWgPing();
    return;
  }

  const peerRows = data.peers.map(p => `
    <tr>
      <td class="wg-name">${escapeHtml(p.name)}</td>
      <td class="wg-ip">${p.ip}</td>
      <td><span class="wg-badge checking" id="wg-status-${p.ip.replaceAll('.', '_')}">&mdash;</span></td>
      <td class="wg-created">${escapeHtml(p.created)}</td>
      <td class="wg-actions">
        <button class="wg-btn" onclick="wgDownloadConfig('${p.ip}')">Config</button>
        <button class="wg-btn danger" onclick="wgDeletePeer('${p.ip}', '${escapeAttr(p.name)}')">Delete</button>
      </td>
    </tr>`).join('');

  el.innerHTML = `
    <div class="wg-card">
      <div class="wg-server">
        <div class="wg-server-info">
          <h3>wg-manage <span class="wg-badge ${data.up ? 'online' : 'offline'}">${data.up ? 'UP' : 'DOWN'}</span></h3>
          <div class="wg-server-meta">10.8.0.1/24 &middot; port ${data.port}/udp &middot; endpoint ${escapeHtml(data.endpoint)}</div>
        </div>
        <div class="wg-server-actions">
          <button class="wg-btn" onclick="wgPower('restart')">Restart</button>
          <button class="wg-btn danger" onclick="wgPower('${data.up ? 'stop' : 'start'}')">${data.up ? 'Stop' : 'Start'}</button>
        </div>
      </div>
      <div class="wg-controls">
        <input type="text" id="wg-peer-name" placeholder="Nama peer (contoh: laptop, hp)" maxlength="32">
        <button id="wg-add-btn">+ Add Peer</button>
      </div>
      ${data.peers.length ? `
      <table class="wg-table">
        <thead><tr><th>Nama</th><th>IP</th><th>Status</th><th>Dibuat</th><th></th></tr></thead>
        <tbody>${peerRows}</tbody>
      </table>` : '<div class="wg-empty">Belum ada peer. Tambahkan dengan form di atas.</div>'}
    </div>`;

  document.getElementById('wg-add-btn').addEventListener('click', wgAddPeer);
  document.getElementById('wg-peer-name').addEventListener('keydown', (e) => { if (e.key === 'Enter') wgAddPeer(); });
  startWgPing();
}
