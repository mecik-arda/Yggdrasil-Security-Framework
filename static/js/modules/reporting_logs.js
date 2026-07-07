// ==========================================
// Reporting, Logs, History, and Graph Functions
// Extracted from api.js
// ==========================================

// --- History Modal ---
async function openHistoryModal() {
    document.getElementById('historyModal').style.display = 'block';
    const list = document.getElementById('historyList');
    list.innerHTML = '<div style="color:var(--text-dim); text-align:center; padding: 20px;">Loading history...</div>';
    try {
        const res = await fetch('/api/history');
        const data = await res.json();
        if (data.status === 'success') {
            window._historyData = data.history;
            if (data.history.length === 0) { list.innerHTML = '<div style="color:var(--text-dim); text-align:center; padding: 20px;">No scan history found.</div>'; return; }
            let html = '';
            data.history.forEach(function (item, index) {
                const date = new Date(item.timestamp).toLocaleString();
                html += '<div onclick="viewHistoryOutput(' + index + ')" style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer; display: flex; justify-content: space-between;">' +
                    '<div><span style="color:#d08770; font-weight:bold;">' + escapeHtml(item.tool) + '</span> ' + escapeHtml(item.target) + '</div>' +
                    '<div style="color:var(--text-dim); font-size: 11px;">' + date + '</div></div>';
            });
            list.innerHTML = html;
        }
    } catch (err) { list.innerHTML = '<div style="color:var(--danger-color); text-align:center; padding: 20px;">Failed to load history.</div>'; }
}

function closeHistoryModal() {
    document.getElementById('historyModal').style.display = 'none';
}

async function clearScanHistory() {
    if (!confirm('Are you sure you want to clear all scan history? This action cannot be undone.')) return;
    try {
        await fetch('/api/history/clear', { method: 'POST' });
        openHistoryModal();
        updateStats();
    } catch (err) { alert('Failed to clear history.'); }
}

function viewHistoryOutput(index) {
    const item = window._historyData[index];
    if (!item) return;
    closeHistoryModal();
    const content = createTerminalWindow('[ HISTORIC: ' + item.tool + ' - ' + item.target + ' ]', item.tool.toLowerCase(), item.target);
    typeWriter(content, item.output || '[No output logs saved]', 0);
}

// --- Valkyrie Report ---
let valkyrieReportContent = '';

async function generateValkyrieReport() {
    const terminals = [];
    const windows = document.querySelectorAll('.terminal-window');
    windows.forEach(function (win) {
        const content = win.querySelector('.terminal-content');
        const title = win.querySelector('.terminal-title');
        if (content && title) {
            const output = content.innerText.trim();
            if (output) {
                terminals.push({
                    tool: win._scanTool || 'manual_tool',
                    target: win._scanTarget || (document.getElementById('target-input').value || 'unknown'),
                    output: output
                });
            }
        }
    });
    if (agentSessionId && terminals.length === 0) {
        try {
            const res = await fetch('/api/ai/report', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: 'agent_session', session_id: agentSessionId })
            });
            const data = await res.json();
            if (data.status === 'success') { showValkyrieReport(data.report); return; }
        } catch (err) { }
    }
    if (terminals.length === 0) {
        alert('No scan data found. Run at least one tool scan before generating a report.');
        return;
    }
    document.getElementById('valkyrieModal').style.display = 'block';
    document.getElementById('valkyrieLoading').style.display = 'block';
    document.getElementById('valkyriePreview').style.display = 'none';
    try {
        const res = await fetch('/api/ai/report', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: 'terminals', terminals: terminals })
        });
        const data = await res.json();
        if (data.status === 'success') { showValkyrieReport(data.report); }
        else { document.getElementById('valkyrieLoading').innerHTML = '<p style="color: var(--danger-color);">Failed to generate report: ' + escapeHtml(data.message || 'Unknown error') + '</p>'; }
    } catch (err) { document.getElementById('valkyrieLoading').innerHTML = '<p style="color: var(--danger-color);">Error generating report.</p>'; }
}

function showValkyrieReport(report) {
    valkyrieReportContent = report;
    document.getElementById('valkyrieLoading').style.display = 'none';
    const preview = document.getElementById('valkyriePreview');
    preview.style.display = 'block';
    preview.innerText = report;
}

function downloadValkyrieReport() {
    if (!valkyrieReportContent) return;
    const target = document.getElementById('target-input').value || 'unknown';
    const timestamp = new Date().toISOString().slice(0, 10);
    const filename = 'yggdrasil_report_' + target.replace(/[^a-zA-Z0-9]/g, '_') + '_' + timestamp + '.md';
    const blob = new Blob([valkyrieReportContent], { type: 'text/markdown' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
}

function closeValkyrieModal() { document.getElementById('valkyrieModal').style.display = 'none'; }

function printValkyrieReport() {
    if (!valkyrieReportContent) return;
    const win = window.open('', '_blank', 'width=900,height=700');
    fetch('/api/ai/report/html', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'terminals', terminals: [{ tool: 'report', target: document.getElementById('target-input').value || 'unknown', output: valkyrieReportContent }] })
    }).then(function (r) { return r.text(); }).then(function (html) {
        win.document.write(html);
        win.document.close();
        setTimeout(function () { win.print(); }, 500);
    }).catch(function () { alert('Failed to open print view.'); });
}

// --- Attack Graph ---
window.openAttackGraphModal = function() { document.getElementById('attackGraphModal').style.display = 'block'; window.renderAttackGraph(); }
window.closeAttackGraphModal = function() { document.getElementById('attackGraphModal').style.display = 'none'; }

window.renderAttackGraph = async function() {
    try {
        const res = await fetch('/api/graph/data');
        const data = await res.json();
        const canvas = document.getElementById('attackGraphCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const W = canvas.width = canvas.parentElement.clientWidth || 900;
        const H = canvas.height = 500;
        ctx.clearRect(0, 0, W, H);
        ctx.fillStyle = '#05070a';
        ctx.fillRect(0, 0, W, H);
        if (!data.nodes || data.nodes.length === 0) {
            ctx.fillStyle = '#666';
            ctx.font = '16px monospace';
            ctx.textAlign = 'center';
            ctx.fillText('No attack graph data. Run scans to populate.', W / 2, H / 2);
            return;
        }
        const nodes = data.nodes;
        const levels = {};
        nodes.forEach(function (n) {
            const d = n.depth || 0;
            if (!levels[d]) levels[d] = [];
            levels[d].push(n);
        });
        const maxDepth = Math.max.apply(null, Object.keys(levels).map(Number).concat([1]));
        const positions = {};
        nodes.forEach(function (n) {
            const d = n.depth || 0;
            const siblings = levels[d] || [n];
            const idx = siblings.indexOf(n);
            const x = ((idx + 1) / (siblings.length + 1)) * W;
            const y = 60 + (d / Math.max(maxDepth, 1)) * (H - 120);
            positions[n.id] = { x: x, y: y };
        });
        const colors = { target: '#bf616a', ip: '#88c0d0', port: '#a3be8c', vuln: '#ebcb8b', subdomain: '#b48ead', exploit: '#d08770', default: '#81a1c1' };
        nodes.forEach(function (n) {
            if (n.parent_id && positions[n.parent_id]) {
                const p = positions[n.parent_id];
                const c = positions[n.id];
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(c.x, c.y);
                ctx.strokeStyle = 'rgba(136,192,208,0.2)';
                ctx.lineWidth = 1;
                ctx.stroke();
            }
        });
        nodes.forEach(function (n) {
            const p = positions[n.id];
            const color = colors[n.node_type] || colors.default;
            const r = 18;
            ctx.beginPath();
            ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(5,7,10,0.9)';
            ctx.fill();
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.fillStyle = color;
            ctx.font = 'bold 11px monospace';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            const label = n.label.length > 18 ? n.label.substring(0, 16) + '..' : n.label;
            ctx.fillText(label, p.x, p.y);
        });
        ctx.fillStyle = '#666';
        ctx.font = '10px monospace';
        ctx.textAlign = 'right';
        ctx.fillText('Click nodes to expand | Right-click to remove', W - 10, H - 10);
    } catch (e) { }
}

async function addGraphNode() {
    const label = document.getElementById('graphNodeLabel').value.trim();
    const type = document.getElementById('graphNodeType').value;
    const parent = document.getElementById('graphNodeParent').value.trim();
    if (!label) return;
    try {
        await fetch('/api/graph/node/add', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ label: label, node_type: type, parent_id: parent || null })
        });
        document.getElementById('graphNodeLabel').value = '';
        if (typeof window.renderAttackGraph === 'function') window.renderAttackGraph();
    } catch (e) { }
}

// --- Log Dashboard ---
let logEntries = [];
let logOffset = 0;

function openLogDashboard() {
    document.getElementById('logDashboardModal').style.display = 'block';
    logEntries = []; logOffset = 0;
    loadLogs(); loadLogStats();
}
function closeLogDashboard() {
    document.getElementById('logDashboardModal').style.display = 'none';
    document.getElementById('logDetailPanel').style.display = 'none';
}

async function loadLogs(reset) {
    if (reset) { logEntries = []; logOffset = 0; }
    const limit = 50;
    try {
        const res = await fetch('/api/logs?offset=' + logOffset + '&limit=' + limit);
        const data = await res.json();
        if (data.status === 'success') {
            if (data.logs.length > 0) {
                logEntries = logEntries.concat(data.logs);
                logOffset += data.logs.length;
                renderLogTable();
            }
            if (data.logs.length < limit) { document.getElementById('logLoadMoreBtn').style.display = 'none'; }
            else { document.getElementById('logLoadMoreBtn').style.display = 'inline-block'; }
        }
    } catch (e) { console.error('[LogDashboard] Error loading logs:', e); }
}

async function loadMoreLogs() { await loadLogs(false); }
function refreshLogDashboard() { loadLogs(true); }

async function loadLogStats() {
    try {
        const res = await fetch('/api/logs/stats');
        const data = await res.json();
        if (data.status === 'success') { updateLogStatsBadges(data.stats); }
    } catch (e) { }
}

function updateLogStatsBadges(stats) {
    document.getElementById('badgeErrorCount').innerText = stats.error || 0;
    document.getElementById('badgeWarnCount').innerText = stats.warning || 0;
    document.getElementById('badgeInfoCount').innerText = stats.info || 0;
    document.getElementById('badgeDebugCount').innerText = stats.debug || 0;
}

function renderLogTable() {
    const tbody = document.getElementById('logTableBody');
    if (!tbody) return;
    const filterLevel = document.getElementById('logLevelFilter').value;
    const search = (document.getElementById('logSearchFilter').value || '').toLowerCase();
    let html = '';
    logEntries.forEach(function (entry) {
        if (filterLevel && filterLevel !== 'ALL' && entry.level !== filterLevel) return;
        const msg = (entry.message || '').toLowerCase();
        if (search && msg.indexOf(search) === -1) return;
        html += renderLogRowHTML(entry);
    });
    tbody.innerHTML = html;
}

function renderLogRowHTML(entry) {
    const colors = { ERROR: '#bf616a', WARNING: '#ebcb8b', INFO: '#a3be8c', DEBUG: '#4c566a' };
    const color = colors[entry.level] || colors.INFO;
    const time = new Date(entry.timestamp * 1000).toLocaleTimeString([], { hour12: false });
    const id = entry.id || btoa(Math.random().toString()).substring(0, 8);
    const m = (entry.message || '');
    const shortMsg = m.length > 80 ? escapeHtml(m.substring(0, 80)) + '...' : escapeHtml(m);
    return '<tr class="log-row" onclick="expandLogDetail(\'' + id + '\')" data-id="' + id + '" data-full=\'' + escapeHtml(JSON.stringify(entry)) + '\'>' +
        '<td style="color:var(--text-dim);">' + time + '</td>' +
        '<td style="color:' + color + ';">' + escapeHtml(entry.level) + '</td>' +
        '<td style="color:var(--highlight-color);">' + escapeHtml(entry.module) + '</td>' +
        '<td>' + shortMsg + '</td>' +
        '</tr>';
}

function prependLogRow(entry) {
    logEntries.unshift(entry);
    const tbody = document.getElementById('logTableBody');
    if (!tbody || document.getElementById('logDashboardModal').style.display === 'none') return;
    const search = (document.getElementById('logSearchFilter').value || '').toLowerCase();
    const msg = (entry.message || '').toLowerCase();
    if (search && msg.indexOf(search) === -1) return;
    const filterLevel = document.getElementById('logLevelFilter').value;
    if (filterLevel && filterLevel !== 'ALL' && entry.level !== filterLevel) return;
    const rowHTML = renderLogRowHTML(entry);
    tbody.insertAdjacentHTML('afterbegin', rowHTML);
}

function expandLogDetail(id) {
    const row = document.querySelector('.log-row[data-id="' + id + '"]');
    if (!row) return;
    try {
        const entry = JSON.parse(row.getAttribute('data-full'));
        document.getElementById('logDetailTime').innerText = new Date(entry.timestamp * 1000).toLocaleString();
        document.getElementById('logDetailLevel').innerText = entry.level;
        document.getElementById('logDetailModule').innerText = entry.module;
        document.getElementById('logDetailMessage').innerText = entry.message;
        const colors = { ERROR: '#bf616a', WARNING: '#ebcb8b', INFO: '#a3be8c', DEBUG: '#4c566a' };
        document.getElementById('logDetailLevel').style.color = colors[entry.level] || colors.INFO;
        let extraHtml = '';
        if (entry.extra && Object.keys(entry.extra).length > 0) {
            extraHtml = JSON.stringify(entry.extra, null, 2);
        } else { extraHtml = 'No extra metadata.'; }
        document.getElementById('logDetailExtra').innerText = extraHtml;
        document.getElementById('logDetailPanel').style.display = 'block';
    } catch (e) { }
}

function hideLogDetail() { document.getElementById('logDetailPanel').style.display = 'none'; }
function filterLogTable() { renderLogTable(); }

function toggleLogLive() {
    const liveToggle = document.getElementById('logLiveToggle');
    if (liveToggle.checked) { document.getElementById('logLiveIndicator').style.display = 'inline'; }
    else { document.getElementById('logLiveIndicator').style.display = 'none'; }
}

async function clearAllLogs() {
    if (!confirm('Clear all system logs?')) return;
    try {
        await fetch('/api/logs/clear', { method: 'POST' });
        logEntries = []; logOffset = 0;
        renderLogTable(); loadLogStats();
    } catch (e) { console.error('[LogDashboard] Clear failed:', e); }
}



// --- GTFOBins Modal (legacy UI moved here) ---
function openGtfobinsModal() { document.getElementById('gtfobinsModal').style.display = 'block'; }
function closeGtfobinsModal() { document.getElementById('gtfobinsModal').style.display = 'none'; }

async function fetchGtfobins() {
    const query = document.getElementById('gtfobinsSearch').value.toLowerCase().trim();
    const resultsDiv = document.getElementById('gtfobinsResults');
    if (!query) return;
    resultsDiv.innerHTML = '<span style="color:#ebcb8b;">Connecting to GTFOBins Live...</span>';
    try {
        const res = await fetch('/api/rag/fetch', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success' && data.data && data.data[query]) {
            const info = data.data[query];
            let html = '<h3 style="color:#d08770; margin-top:0;">' + query + '</h3>';
            for (const [funcName, funcData] of Object.entries(info)) {
                html += '<div style="margin-bottom: 15px; border-left: 2px solid #d08770; padding-left: 10px;"><h4 style="color:#ebcb8b; margin: 0 0 5px 0;">' + funcName + '</h4>';
                if (Array.isArray(funcData)) {
                    funcData.forEach(function (item) {
                        if (item.description) html += '<p style="font-size:12px; margin: 5px 0;">' + item.description + '</p>';
                        if (item.code) html += '<pre style="background: rgba(0,0,0,0.5); padding: 8px; border-radius: 4px; color: #a3be8c; overflow-x: auto;">' + escapeHtml(item.code) + '</pre>';
                    });
                }
                html += '</div>';
            }
            resultsDiv.innerHTML = html;
        } else { resultsDiv.innerHTML = '<span style="color:#bf616a;">No GTFOBins data found for "' + query + '". Note: Only a subset of live binaries is currently indexed.</span>'; }
    } catch (e) { resultsDiv.innerHTML = '<span style="color:#bf616a;">Connection error.</span>'; }
}

async function fetchGtfobinsLive() {
    const resultsDiv = document.getElementById('kvasirResults');
    resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--accent-color);">🔄 Fetching latest GTFOBins data from GitHub...<br><small>This may take a moment.</small></div>';
    try {
        const res = await fetch('/api/rag/fetch', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') { resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: #a3be8c;">✅ ' + escapeHtml(data.message) + '</div>'; }
        else { resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: #d08770;">⚠️ ' + escapeHtml(data.message) + '</div>'; }
    } catch (err) { resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--danger-color);">⚠️ Fetch failed. Check internet connection.</div>'; }
}
