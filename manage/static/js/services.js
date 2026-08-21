let svcAvailable = [];

// These are already declared in app.js, just reassign here
svcLogTimer = null;
svcLogName = null;

async function loadService() {
  const el = document.getElementById('tab-services');
  if (!el) return;
  el.innerHTML = `
    <div class="svc-controls">
      <button class="svc-add-btn" id="svc-add-btn">+ Add Service</button>
      <button id="svc-refresh">&#8635; Refresh</button>
    </div>
    <div id="svc-table-wrap"></div>
    <div id="svc-config-area"></div>
    <div id="svc-log-area"></div>
  `;
  document.getElementById('svc-add-btn').addEventListener('click', openAddServiceModal);
  document.getElementById('svc-refresh').addEventListener('click', refreshServices);
  refreshServices();
}

async function refreshServices() {
  const el = document.getElementById('svc-table-wrap');
  if (!el) return;
  el.innerHTML = '<div class="svc-empty"><span class="spinner"></span> Loading...</div>';
  try {
    const res = await fetch('/api/services/monitored?token=' + encodeURIComponent(authToken));
    if (!res.ok) throw new Error('Failed to load');
    const data = await res.json();
    if (!data.services.length) {
      el.innerHTML = '<div class="svc-empty">No services monitored. Click "+ Add Service" to begin.</div>';
      return;
    }
    let html = '<table class="svc-table"><thead><tr>';
    html += '<th>Service</th><th>Status</th><th>Enabled</th><th>Memory</th><th></th>';
    html += '</tr></thead><tbody>';
    for (const svc of data.services) {
      const isActive = svc.active_state === 'active';
      const isFailed = svc.active_state === 'failed';
      const isEnabled = svc.enabled_state === 'enabled';
      const safeId = svc.name.replace(/[^a-zA-Z0-9]/g, '_');
      const memStr = svc.pids > 0 ? svc.rss_mb + ' MB \u00b7 ' + svc.pids + ' PID' + (svc.pids > 1 ? 's' : '') : '\u2014';
      html += '<tr>';
      html += '<td><div class="svc-td-name">' + escapeHtml(svc.name) + '</div><div class="svc-td-desc">' + escapeHtml(svc.description) + '</div></td>';
      html += '<td><span class="svc-check ' + (isActive || isFailed ? (isFailed ? 'no' : 'yes') : 'no') + '">' + (isActive ? '\u2713' : '[X]') + '</span></td>';
      html += '<td><span class="svc-check ' + (isEnabled ? 'yes' : 'no') + '">' + (isEnabled ? '\u2713' : '[X]') + '</span></td>';
      html += '<td style="color:var(--text2);font-size:12px">' + memStr + '</td>';
      html += '<td style="text-align:right"><div class="svc-drop-wrap">';
      html += '<button class="svc-drop-btn" onclick="toggleDropdown(event,\'' + safeId + '\')">Actions <span class="arrow">\u25be</span></button>';
      html += '<div class="svc-drop-menu" id="svc-drop-' + safeId + '">';
      html += '<div class="svc-drop-item" onclick="svcAction(\'' + svc.name + '\',\'restart\')">Restart</div>';
      if (isActive) {
        html += '<div class="svc-drop-item" onclick="svcAction(\'' + svc.name + '\',\'stop\')">Stop</div>';
      } else {
        html += '<div class="svc-drop-item" onclick="svcAction(\'' + svc.name + '\',\'start\')">Start</div>';
      }
      html += '<div class="svc-drop-sep"></div>';
      if (isEnabled) {
        html += '<div class="svc-drop-item" onclick="svcAction(\'' + svc.name + '\',\'disable\')">Disable</div>';
      } else {
        html += '<div class="svc-drop-item" onclick="svcAction(\'' + svc.name + '\',\'enable\')">Enable</div>';
      }
      html += '<div class="svc-drop-sep"></div>';
      html += '<div class="svc-drop-item" onclick="toggleServiceConfig(\'' + svc.name + '\')">Show Config</div>';
      html += '<div class="svc-drop-item" onclick="toggleServiceLogs(\'' + svc.name + '\')">Show Logs</div>';
      html += '<div class="svc-drop-item danger" onclick="removeService(\'' + svc.name + '\')">Remove</div>';
      html += '</div></div></td>';
      html += '</tr>';
    }
    html += '</tbody></table>';
    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = '<div class="svc-empty" style="color:var(--accent)">Error: ' + escapeHtml(e.message) + '</div>';
  }
}

async function svcAction(name, action) {
  try {
    const res = await fetch('/api/services/' + name + '/' + action + '?token=' + encodeURIComponent(authToken), { method: 'POST' });
    const d = await res.json();
    if (!d.success && d.error) alert('Error: ' + d.error);
    refreshServices();
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

async function removeService(name) {
  if (!confirm('Remove "' + name + '" from monitored services?')) return;
  try {
    await fetch('/api/services/monitored?token=' + encodeURIComponent(authToken) + '&name=' + encodeURIComponent(name), { method: 'DELETE' });
    refreshServices();
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

async function toggleServiceConfig(name) {
  const el = document.getElementById('svc-config-area');
  if (el.dataset.current === name) {
    el.innerHTML = '';
    el.dataset.current = '';
    return;
  }
  el.dataset.current = name;
  el.innerHTML = '<div class="svc-config show"><div class="svc-config-src"><span class="spinner"></span> Loading config for ' + escapeHtml(name) + '...</div></div>';
  try {
    const res = await fetch('/api/services/' + encodeURIComponent(name) + '/config?token=' + encodeURIComponent(authToken));
    if (!res.ok) throw new Error('Failed to load config');
    const data = await res.json();
    if (data.error) {
      el.innerHTML = '<div class="svc-config show"><div class="svc-config-src">' + escapeHtml(data.source || '') + '</div><pre style="color:var(--accent)">' + escapeHtml(data.error) + '</pre></div>';
    } else {
      const srcLabel = data.source ? '<div class="svc-config-src">' + escapeHtml(data.source) + '</div>' : '';
      el.innerHTML = '<div class="svc-config show">' + srcLabel + '<pre>' + escapeHtml(data.config) + '</pre></div>';
    }
  } catch(e) {
    el.innerHTML = '<div class="svc-config show"><pre style="color:var(--accent)">Error: ' + escapeHtml(e.message) + '</pre></div>';
  }
}

svcLogTimer = null;
svcLogName = null;

async function toggleServiceLogs(name) {
  const el = document.getElementById('svc-log-area');
  if (svcLogName === name) {
    svcLogName = null;
    if (svcLogTimer) { clearInterval(svcLogTimer); svcLogTimer = null; }
    el.innerHTML = '';
    return;
  }
  svcLogName = name;
  el.innerHTML = '<div class="svc-config show"><div class="svc-config-src">Realtime logs \u00b7 ' + escapeHtml(name) + '</div><pre class="svc-log-body"><span class="spinner"></span> Loading logs...</pre></div>';
  await loadServiceLogs(name);
  if (svcLogTimer) clearInterval(svcLogTimer);
  svcLogTimer = setInterval(() => loadServiceLogs(name), 3000);
}

async function loadServiceLogs(name) {
  const el = document.getElementById('svc-log-area');
  if (svcLogName !== name || !el) return;
  const pre = el.querySelector('.svc-log-body');
  if (!pre) return;
  try {
    const res = await fetch('/api/services/' + encodeURIComponent(name) + '/logs?token=' + encodeURIComponent(authToken));
    if (!res.ok) throw new Error('Failed to load logs');
    const data = await res.json();
    if (data.error) {
      pre.textContent = data.error;
    } else {
      pre.textContent = data.logs.length ? data.logs.join('\n') : '(no logs)';
      pre.scrollTop = pre.scrollHeight;
    }
  } catch(e) {
    pre.textContent = 'Error: ' + e.message;
  }
}

async function openAddServiceModal() {
  const overlay = document.getElementById('svc-modal-overlay');
  const listEl = document.getElementById('svc-modal-list');
  const searchEl = document.getElementById('svc-modal-search');
  overlay.classList.add('show');
  searchEl.value = '';
  listEl.innerHTML = '<div class="svc-empty"><span class="spinner"></span> Loading services...</div>';

  try {
    const [availRes, monRes] = await Promise.all([
      fetch('/api/services/available?token=' + encodeURIComponent(authToken)),
      fetch('/api/services/monitored?token=' + encodeURIComponent(authToken))
    ]);
    if (!availRes.ok || !monRes.ok) throw new Error('Failed to load');
    const availData = await availRes.json();
    const monData = await monRes.json();
    const monitoredNames = new Set(monData.services.map(s => s.name));
    svcAvailable = availData.services.map(s => ({ ...s, monitored: monitoredNames.has(s.name) }));
    renderServiceModalList('');
  } catch(e) {
    listEl.innerHTML = '<div class="svc-empty" style="color:var(--accent)">Error: ' + escapeHtml(e.message) + '</div>';
  }
}

function renderServiceModalList(filter) {
  const listEl = document.getElementById('svc-modal-list');
  const filtered = svcAvailable.filter(s => s.name.toLowerCase().includes(filter.toLowerCase()));
  if (!filtered.length) {
    listEl.innerHTML = '<div class="svc-empty">No services found.</div>';
    return;
  }
  let html = '';
  for (const s of filtered) {
    html += '<div class="svc-modal-item' + (s.monitored ? ' svc-already' : '') + '">';
    html += '<div><span class="svc-modal-name">' + escapeHtml(s.name) + '</span> <span class="svc-modal-state">' + s.unit_file_state + '</span></div>';
    if (s.monitored) {
      html += '<button class="svc-modal-add" disabled>Added</button>';
    } else {
      html += '<button class="svc-modal-add" onclick="addServiceFromModal(\'' + escapeAttr(s.name) + '\', this)">Add</button>';
    }
    html += '</div>';
  }
  listEl.innerHTML = html;
}

async function addServiceFromModal(name, btn) {
  try {
    await fetch('/api/services/monitored', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: authToken, name: name })
    });
    btn.textContent = 'Added';
    btn.disabled = true;
    btn.parentElement.classList.add('svc-already');
    refreshServices();
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

document.getElementById('svc-modal-close').addEventListener('click', () => {
  document.getElementById('svc-modal-overlay').classList.remove('show');
});
document.getElementById('svc-modal-search').addEventListener('input', (e) => {
  renderServiceModalList(e.target.value);
});
document.addEventListener('click', e => {
  if (e.target.id === 'svc-modal-overlay') document.getElementById('svc-modal-overlay').classList.remove('show');
});
