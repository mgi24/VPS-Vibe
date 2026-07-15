let dockerFirstLoad = true;

async function loadDocker() {
  const el = document.getElementById('tab-docker');
  if (currentTab !== 'docker') return;
  if (!el.querySelector('#docker-table-wrap')) {
    el.innerHTML = `
      <div class="svc-controls">
        <button id="docker-refresh">&#8635; Refresh</button>
      </div>
      <div id="docker-table-wrap"></div>
      <div id="docker-config-area"></div>
    `;
    document.getElementById('docker-refresh').addEventListener('click', () => { dockerFirstLoad = true; loadDocker(); });
    dockerFirstLoad = true;
  }
  const wrap = document.getElementById('docker-table-wrap');
  if (!wrap) return;
  try {
    const res = await fetch('/api/docker/containers?token=' + encodeURIComponent(authToken));
    if (!res.ok) throw new Error('Failed to load');
    const data = await res.json();
    if (!data.containers.length) {
      wrap.innerHTML = '<div class="docker-empty">No Docker containers found.</div>';
      dockerFirstLoad = true;
      return;
    }
    if (dockerFirstLoad || !wrap.querySelector('.svc-table')) {
      renderDockerTable(wrap, data.containers);
      dockerFirstLoad = false;
      return;
    }
    const existingRows = wrap.querySelectorAll('tbody tr[data-name]');
    const existingNames = new Set();
    for (const row of existingRows) existingNames.add(row.dataset.name);
    const newNames = new Set(data.containers.map(c => c.name));
    for (const row of existingRows) {
      if (!newNames.has(row.dataset.name)) { row.remove(); continue; }
      const c = data.containers.find(x => x.name === row.dataset.name);
      if (!c) continue;
      const isRunning = c.state === 'running';
      const stateClass = c.state === 'running' ? 'running' : c.state === 'exited' ? 'exited' : c.state === 'paused' ? 'paused' : 'created';
      const memStr = c.mem_usage ? c.mem_usage + ' (' + c.mem_perc + ')' : '\u2014';
      const cpuStr = c.cpu_perc || '\u2014';
      row.querySelector('.dk-state').className = 'docker-state ' + stateClass;
      row.querySelector('.dk-state').textContent = c.state;
      row.querySelector('.dk-status').textContent = c.status;
      row.querySelector('.dk-mem').textContent = memStr;
      row.querySelector('.dk-cpu').textContent = cpuStr;
      const dropItems = row.querySelector('.svc-drop-menu');
      if (isRunning) {
        dropItems.innerHTML = '<div class="svc-drop-item" onclick="dockerAction(\'' + c.name + '\',\'stop\')">Stop</div><div class="svc-drop-sep"></div><div class="svc-drop-item" onclick="toggleDockerConfig(\'' + escapeAttr(c.name) + '\')">View Config</div>';
      } else {
        dropItems.innerHTML = '<div class="svc-drop-item" onclick="dockerAction(\'' + c.name + '\',\'start\')">Start</div><div class="svc-drop-sep"></div><div class="svc-drop-item" onclick="toggleDockerConfig(\'' + escapeAttr(c.name) + '\')">View Config</div>';
      }
    }
    for (const c of data.containers) {
      if (!existingNames.has(c.name)) {
        const tbody = wrap.querySelector('tbody');
        tbody.insertAdjacentHTML('beforeend', buildDockerRow(c));
      }
    }
  } catch(e) {
    if (dockerFirstLoad) wrap.innerHTML = '<div class="docker-empty" style="color:var(--accent)">Error: ' + escapeHtml(e.message) + '</div>';
  }
}

function buildDockerRow(c) {
  const isRunning = c.state === 'running';
  const stateClass = c.state === 'running' ? 'running' : c.state === 'exited' ? 'exited' : c.state === 'paused' ? 'paused' : 'created';
  const memStr = c.mem_usage ? c.mem_usage + ' (' + c.mem_perc + ')' : '\u2014';
  const cpuStr = c.cpu_perc || '\u2014';
  const safeId = 'dk_' + c.name.replace(/[^a-zA-Z0-9]/g, '_');
  let html = '<tr data-name="' + escapeAttr(c.name) + '">';
  html += '<td><div class="svc-td-name">' + escapeHtml(c.name) + '</div>';
  if (c.ports) html += '<div class="svc-td-desc">' + escapeHtml(c.ports) + '</div>';
  html += '</td>';
  html += '<td style="font-size:12px;color:var(--text2)">' + escapeHtml(c.image) + '</td>';
  html += '<td><span class="docker-state dk-state ' + stateClass + '">' + escapeHtml(c.state) + '</span>';
  html += '<div class="dk-status" style="font-size:10px;color:var(--text2);margin-top:2px">' + escapeHtml(c.status) + '</div></td>';
  html += '<td class="dk-mem" style="font-size:12px;color:var(--text2)">' + memStr + '</td>';
  html += '<td class="dk-cpu" style="font-size:12px;color:var(--text2)">' + cpuStr + '</td>';
  html += '<td style="text-align:right"><div class="svc-drop-wrap">';
  html += '<button class="svc-drop-btn" onclick="toggleDropdown(event,\'' + safeId + '\')">Actions <span class="arrow">\u25be</span></button>';
  html += '<div class="svc-drop-menu" id="svc-drop-' + safeId + '">';
  if (isRunning) {
    html += '<div class="svc-drop-item" onclick="dockerAction(\'' + c.name + '\',\'stop\')">Stop</div>';
  } else {
    html += '<div class="svc-drop-item" onclick="dockerAction(\'' + c.name + '\',\'start\')">Start</div>';
  }
  html += '<div class="svc-drop-sep"></div>';
  html += '<div class="svc-drop-item" onclick="toggleDockerConfig(\'' + escapeAttr(c.name) + '\')">View Config</div>';
  html += '</div></div></td>';
  html += '</tr>';
  return html;
}

function renderDockerTable(wrap, containers) {
  let html = '<table class="svc-table"><thead><tr>';
  html += '<th>Container</th><th>Image</th><th>State</th><th>RAM</th><th>CPU</th><th></th>';
  html += '</tr></thead><tbody>';
  for (const c of containers) html += buildDockerRow(c);
  html += '</tbody></table>';
  wrap.innerHTML = html;
}

async function dockerAction(name, action) {
  try {
    const res = await fetch('/api/docker/containers/' + encodeURIComponent(name) + '/' + action + '?token=' + encodeURIComponent(authToken), { method: 'POST' });
    const d = await res.json();
    if (!d.success && d.error) alert('Error: ' + d.error);
    dockerFirstLoad = true;
    loadDocker();
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

async function toggleDockerConfig(name) {
  const el = document.getElementById('docker-config-area');
  if (el.dataset.current === name) {
    el.innerHTML = '';
    el.dataset.current = '';
    return;
  }
  el.dataset.current = name;
  el.innerHTML = '<div class="docker-config show"><pre style="color:var(--text2)"><span class="spinner"></span> Loading config for ' + escapeHtml(name) + '...</pre></div>';
  try {
    const res = await fetch('/api/docker/containers/' + encodeURIComponent(name) + '/inspect?token=' + encodeURIComponent(authToken));
    if (!res.ok) throw new Error('Failed to load config');
    const data = await res.json();
    if (data.error) {
      el.innerHTML = '<div class="docker-config show"><pre style="color:var(--accent)">' + escapeHtml(data.error) + '</pre></div>';
    } else {
      el.innerHTML = '<div class="docker-config show"><pre>' + escapeHtml(data.config) + '</pre></div>';
    }
  } catch(e) {
    el.innerHTML = '<div class="docker-config show"><pre style="color:var(--accent)">Error: ' + escapeHtml(e.message) + '</pre></div>';
  }
}
