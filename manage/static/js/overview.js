async function loadOverview() {
  const el = document.getElementById('tab-overview');
  el.innerHTML = '<div style="text-align:center;padding:40px"><span class="spinner"></span> Loading...</div>';
  try {
    const res = await fetch('/api/overview?token=' + encodeURIComponent(authToken));
    if (!res.ok) throw new Error('Failed to load');
    const data = await res.json();
    el.innerHTML = '<div class="overview-grid">' +
      card('Hostname', data.hostname) +
      card('Kernel', data.kernel) +
      card('Uptime', data.uptime) +
      card('Memory', data.memory) +
      card('Disk Usage', data.disk) +
      card('Top Processes (by mem)', data.top_processes) +
    '</div>';
  } catch(e) {
    el.innerHTML = '<div style="color:var(--accent);padding:20px">Failed to load overview: ' + e.message + '</div>';
  }
  function card(title, content) {
    return '<div class="overview-card"><h3>' + title + '</h3><pre>' + escapeHtml(content) + '</pre></div>';
  }
}
