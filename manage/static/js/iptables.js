let iptablesEditContext = null;
let iptablesInterfaces = [];
const chainFormConfig = {
  'nat/PREROUTING':  { showIn:1, showOut:0, showPorts:0, showTo:1, toLbl:'DNAT target (--to-destination)', defTarget:'DNAT' },
  'nat/INPUT':       { showIn:1, showOut:0, showPorts:1, showTo:0, defTarget:'' },
  'nat/OUTPUT':      { showIn:0, showOut:1, showPorts:1, showTo:1, toLbl:'SNAT target (--to-source)', defTarget:'SNAT' },
  'nat/POSTROUTING': { showIn:0, showOut:1, showPorts:0, showTo:1, toLbl:'SNAT/MASQ target (--to-source)', defTarget:'MASQUERADE' },
  'filter/INPUT':    { showIn:1, showOut:0, showPorts:1, showTo:0, defTarget:'' },
  'filter/FORWARD':  { showIn:1, showOut:1, showPorts:1, showTo:0, defTarget:'' },
  'filter/OUTPUT':   { showIn:0, showOut:1, showPorts:1, showTo:0, defTarget:'' },
};

function setFormFields(table, chain) {
  const c = chainFormConfig[table+'/'+chain] || { showIn:1, showOut:1, showPorts:1, showTo:0, defTarget:'' };
  document.getElementById('ipt-form-in-row').style.display = c.showIn ? 'flex' : 'none';
  document.getElementById('ipt-form-out-row').style.display = c.showOut ? 'flex' : 'none';
  document.getElementById('ipt-form-port-row').style.display = c.showPorts ? 'flex' : 'none';
  const toRow = document.getElementById('ipt-form-to-row');
  toRow.style.display = c.showTo ? 'flex' : 'none';
  if (c.showTo) document.getElementById('ipt-form-to-label').textContent = c.toLbl;
  if (c.defTarget && !document.getElementById('ipt-form-target').value) {
    document.getElementById('ipt-form-target').value = c.defTarget;
  }
}

function populateInterfaces() {
  ['ipt-form-in','ipt-form-out'].forEach(id => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const v = sel.value;
    sel.innerHTML = '<option value="">any</option>';
    iptablesInterfaces.forEach(iface => {
      const o = document.createElement('option');
      o.value = iface;
      o.textContent = iface;
      if (iface === v) o.selected = true;
      sel.appendChild(o);
    });
  });
}

async function loadIptables() {
  const el = document.getElementById('tab-iptables');
  el.innerHTML = `
    <div class="iptables-controls">
      <button id="ipt-refresh">&#8635; Refresh</button>
    </div>
    <div id="iptables-sections">
      <div class="iptables-section" id="ipt-nat-section">
        <div class="section-header">NAT <span class="badge">nat</span></div>
        <div id="ipt-nat-chains"></div>
      </div>
      <div class="iptables-section" id="ipt-filter-section">
        <div class="section-header">FILTER <span class="badge">filter</span></div>
        <div id="ipt-filter-chains"></div>
      </div>
    </div>
    <div class="rule-form-overlay" id="ipt-form-overlay">
      <div class="rule-form">
        <h4 id="ipt-form-title">Add Rule</h4>
        <div class="form-row">
          <select id="ipt-form-target" style="max-width:130px">
            <option value="">Target</option>
            <option value="ACCEPT">ACCEPT</option>
            <option value="DROP">DROP</option>
            <option value="REJECT">REJECT</option>
            <option value="LOG">LOG</option>
            <option value="MASQUERADE">MASQUERADE</option>
            <option value="DNAT">DNAT</option>
            <option value="SNAT">SNAT</option>
            <option value="RETURN">RETURN</option>
          </select>
          <select id="ipt-form-proto" style="max-width:100px">
            <option value="">Proto</option>
            <option value="tcp">tcp</option>
            <option value="udp">udp</option>
            <option value="icmp">icmp</option>
            <option value="all">all</option>
          </select>
        </div>
        <div class="form-row" id="ipt-form-in-row">
          <span class="field-label">In interface</span>
          <select id="ipt-form-in"><option value="">any</option></select>
        </div>
        <div class="form-row" id="ipt-form-out-row">
          <span class="field-label">Out interface</span>
          <select id="ipt-form-out"><option value="">any</option></select>
        </div>
        <div class="form-row">
          <input type="text" id="ipt-form-src" placeholder="Source (e.g. 10.0.0.0/24)">
          <input type="text" id="ipt-form-dst" placeholder="Destination (e.g. 10.0.0.1)">
        </div>
        <div class="form-row" id="ipt-form-port-row">
          <input type="text" id="ipt-form-dport" placeholder="dport (e.g. 80,443)">
          <input type="text" id="ipt-form-sport" placeholder="sport">
        </div>
        <div class="form-row" id="ipt-form-to-row">
          <span class="field-label" id="ipt-form-to-label">DNAT target</span>
          <input type="text" id="ipt-form-to" placeholder="e.g. 10.90.204.143 or 10.90.204.143:80">
        </div>
        <div class="form-row">
          <input type="text" id="ipt-form-extra" placeholder="Extra flags">
        </div>
        <div class="form-row" style="justify-content:flex-end">
          <button class="cancel" id="ipt-form-cancel">Cancel</button>
          <button id="ipt-form-submit">Apply</button>
          <button class="danger" id="ipt-form-delete" style="display:none">Delete</button>
        </div>
        <div class="form-note" id="ipt-form-note"></div>
      </div>
    </div>
  `;
  document.getElementById('ipt-refresh').addEventListener('click', refreshIptables);
  document.getElementById('ipt-form-cancel').addEventListener('click', closeIptablesForm);
  document.getElementById('ipt-form-submit').addEventListener('click', submitIptablesForm);
  document.getElementById('ipt-form-delete').addEventListener('click', deleteFromForm);
  await fetchInterfaces();
  refreshIptables();
}

async function fetchInterfaces() {
  try {
    const res = await fetch('/api/interfaces?token=' + encodeURIComponent(authToken));
    if (res.ok) {
      const data = await res.json();
      if (data.interfaces) iptablesInterfaces = data.interfaces;
    }
  } catch(e) {}
}

async function refreshIptables() {
  document.querySelectorAll('#ipt-nat-chains, #ipt-filter-chains').forEach(e => {
    e.innerHTML = '<div class="iptables-empty"><span class="spinner"></span> Loading...</div>';
  });
  await fetchInterfaces();
  try {
    const res = await fetch('/api/iptables/all?token=' + encodeURIComponent(authToken));
    if (!res.ok) throw new Error('Failed to load rules');
    const data = await res.json();
    renderChainGroup('ipt-nat-chains', 'nat', data.nat, ['PREROUTING', 'INPUT', 'OUTPUT', 'POSTROUTING']);
    renderChainGroup('ipt-filter-chains', 'filter', data.filter, ['INPUT', 'FORWARD', 'OUTPUT']);
  } catch(e) {
    document.querySelectorAll('#ipt-nat-chains, #ipt-filter-chains').forEach(el => {
      el.innerHTML = '<div class="iptables-empty" style="color:var(--accent)">Error: ' + escapeHtml(e.message) + '</div>';
    });
  }
}

function renderChainGroup(containerId, table, chains, chainOrder) {
  const container = document.getElementById(containerId);
  let html = '';
  for (const name of chainOrder) {
    const rules = chains[name] || [];
    html += '<div class="chain-card">';
    html += '<div class="chain-header"><span>' + name + '</span>';
    html += '<div class="chain-actions">';
    html += '<button class="add-btn" onclick="openAddForm(\'' + table + '\',\'' + name + '\')">+ Add</button>';
    html += '</div></div>';
    if (rules.length === 0) {
      html += '<div class="iptables-empty">No rules</div>';
    } else {
      html += '<table class="rule-table"><thead><tr>';
      html += '<th>#</th><th>pkts</th><th>bytes</th><th>target</th><th>prot</th><th>in</th><th>out</th><th>source</th><th>destination</th><th>extra</th><th class="col-edit"></th>';
      html += '</tr></thead><tbody>';
      for (const r of rules) {
        const cls = 'rule-target-' + r.target;
        html += '<tr>';
        html += '<td>' + r.num + '</td>';
        html += '<td>' + r.pkts + '</td>';
        html += '<td>' + r.bytes + '</td>';
        html += '<td class="col-target ' + cls + '">' + r.target + '</td>';
        html += '<td>' + r.prot + '</td>';
        html += '<td>' + r.in + '</td>';
        html += '<td>' + r.out + '</td>';
        html += '<td>' + r.source + '</td>';
        html += '<td>' + r.destination + '</td>';
        html += '<td style="color:var(--text2)">' + escapeHtml(r.extra) + '</td>';
        html += '<td class="col-edit"><button class="edit-btn" onclick="openEditForm(\'' + table + '\',\'' + name + '\',' + r.num + ',\'' + escapeAttr(r.target) + '\',\'' + escapeAttr(r.prot) + '\',\'' + escapeAttr(r.in) + '\',\'' + escapeAttr(r.out) + '\',\'' + escapeAttr(r.source) + '\',\'' + escapeAttr(r.destination) + '\',\'' + escapeAttr(r.extra) + '\')">Edit</button></td>';
        html += '</tr>';
      }
      html += '</tbody></table>';
    }
    html += '</div>';
  }
  container.innerHTML = html;
}

function openAddForm(table, chain) {
  iptablesEditContext = { mode:'add', table, chain, line:0 };
  document.getElementById('ipt-form-title').textContent = 'Add Rule \u2014 ' + table + '/' + chain;
  ['src','dst','dport','sport','to','extra'].forEach(id => document.getElementById('ipt-form-'+id).value = '');
  document.getElementById('ipt-form-target').value = '';
  document.getElementById('ipt-form-proto').value = '';
  setFormFields(table, chain);
  populateInterfaces();
  document.getElementById('ipt-form-delete').style.display = 'none';
  document.getElementById('ipt-form-note').textContent = '';
  showIptablesForm();
}

function openEditForm(table, chain, line, target, prot, inIf, outIf, src, dst, extra) {
  iptablesEditContext = { mode:'edit', table, chain, line };
  document.getElementById('ipt-form-title').textContent = 'Edit Rule #' + line + ' \u2014 ' + table + '/' + chain;
  setFormFields(table, chain);
  populateInterfaces();
  const u = s => s === '*' ? '' : unescapeAttr(s);
  document.getElementById('ipt-form-src').value = u(src);
  document.getElementById('ipt-form-dst').value = u(dst);
  document.getElementById('ipt-form-in').value = u(inIf);
  document.getElementById('ipt-form-out').value = u(outIf);
  document.getElementById('ipt-form-target').value = unescapeAttr(target);
  document.getElementById('ipt-form-proto').value = unescapeAttr(prot) === 'all' ? 'all' : unescapeAttr(prot);
  document.getElementById('ipt-form-to').value = '';
  document.getElementById('ipt-form-sport').value = '';
  document.getElementById('ipt-form-dport').value = '';
  let extraStr = unescapeAttr(extra);
  const dpm = extraStr.match(/(?:^|\s)(tcp|udp) dpt:(\S+)/);
  if (dpm) { document.getElementById('ipt-form-dport').value = dpm[2]; extraStr = extraStr.replace(dpm[0], ''); }
  const spm = extraStr.match(/(?:^|\s)(tcp|udp) spt:(\S+)/);
  if (spm) { document.getElementById('ipt-form-sport').value = spm[2]; extraStr = extraStr.replace(spm[0], ''); }
  const tom = extraStr.match(/to:\S+/);
  if (tom) { document.getElementById('ipt-form-to').value = tom[0]; extraStr = extraStr.replace(tom[0], ''); }
  document.getElementById('ipt-form-extra').value = extraStr.trim();
  document.getElementById('ipt-form-delete').style.display = 'inline-block';
  document.getElementById('ipt-form-note').textContent = '';
  showIptablesForm();
}

function showIptablesForm() {
  document.getElementById('ipt-form-overlay').classList.add('show');
}

function closeIptablesForm() {
  document.getElementById('ipt-form-overlay').classList.remove('show');
  iptablesEditContext = null;
}

function getRuleFromForm() {
  const f = id => document.getElementById('ipt-form-'+id);
  const target = f('target').value;
  const proto = f('proto').value;
  const src = f('src').value.trim();
  const dst = f('dst').value.trim();
  const inIf = f('in').value;
  const outIf = f('out').value;
  const dport = f('dport').value.trim();
  const sport = f('sport').value.trim();
  const toVal = f('to').value.trim();
  const extra = f('extra').value.trim();
  let rule = '';
  if (proto && proto !== 'all') rule += '-p ' + proto + ' ';
  if (src) rule += '-s ' + src + ' ';
  if (dst) rule += '-d ' + dst + ' ';
  if (inIf) rule += '-i ' + inIf + ' ';
  if (outIf) rule += '-o ' + outIf + ' ';
  if (dport) rule += '--dport ' + dport + ' ';
  if (sport) rule += '--sport ' + sport + ' ';
  if (extra) rule += extra + ' ';
  if (target) rule += '-j ' + target + ' ';
  if (toVal) {
    const dest = toVal.replace(/^to:\s*/i, '');
    const isSnat = target === 'SNAT' || target === 'MASQUERADE';
    rule += (isSnat ? '--to-source ' : '--to-destination ') + dest + ' ';
  }
  return rule.trim();
}

async function submitIptablesForm() {
  const ctx = iptablesEditContext;
  if (!ctx) return;
  const noteEl = document.getElementById('ipt-form-note');
  const rule = getRuleFromForm();
  if (!rule) { noteEl.textContent = 'Rule cannot be empty'; return; }
  try {
    if (ctx.mode === 'add') {
      const fd = new FormData();
      fd.append('token', authToken);
      fd.append('table', ctx.table);
      fd.append('chain', ctx.chain);
      fd.append('position', '0');
      fd.append('rule', rule);
      const res = await fetch('/api/iptables', { method:'POST', body:fd });
      const d = await res.json();
      if (!d.success) { noteEl.textContent = 'Error: ' + d.error; return; }
    } else {
      const fd = new FormData();
      fd.append('token', authToken);
      fd.append('table', ctx.table);
      fd.append('chain', ctx.chain);
      fd.append('line', ctx.line.toString());
      fd.append('rule', rule);
      const res = await fetch('/api/iptables', { method:'PUT', body:fd });
      const d = await res.json();
      if (!d.success) { noteEl.textContent = 'Error: ' + d.error; return; }
    }
    closeIptablesForm();
    refreshIptables();
  } catch(e) { noteEl.textContent = 'Error: ' + e.message; }
}

async function deleteFromForm() {
  const ctx = iptablesEditContext;
  if (!ctx || ctx.mode !== 'edit') return;
  if (!confirm('Delete rule #' + ctx.line + ' from ' + ctx.table + '/' + ctx.chain + '?')) return;
  try {
    const res = await fetch('/api/iptables?token=' + encodeURIComponent(authToken) +
      '&table=' + ctx.table + '&chain=' + ctx.chain + '&line=' + ctx.line, { method:'DELETE' });
    const d = await res.json();
    if (!d.success) { document.getElementById('ipt-form-note').textContent = 'Error: ' + d.error; return; }
    closeIptablesForm();
    refreshIptables();
  } catch(e) { document.getElementById('ipt-form-note').textContent = 'Error: ' + e.message; }
}

document.addEventListener('click', e => {
  if (e.target.id === 'ipt-form-overlay') closeIptablesForm();
});
