// ==========================================
// AI and Autonomous Agent Functions
// Extracted from api.js
// ==========================================

// --- Agent Functions ---
let agentSessionId = null;
let agentPollTimer = null;

function openAgentPanel() {
    const targetInput = document.getElementById('target-input').value;
    document.getElementById('agentTargetInput').value = targetInput || '';
    document.getElementById('agentIdleView').style.display = 'block';
    document.getElementById('agentActiveView').style.display = 'none';
    document.getElementById('agentFinalSummary').style.display = 'none';
    document.getElementById('agentModal').style.display = 'block';
}

function closeAgentPanel() {
    if (agentPollTimer) { clearInterval(agentPollTimer); agentPollTimer = null; }
    document.getElementById('agentModal').style.display = 'none';
}

async function startAgentScan() {
    const target = document.getElementById('agentTargetInput').value.trim();
    if (!target) { alert('Please enter a target IP or domain.'); return; }
    document.getElementById('btnStartAgent').disabled = true;
    document.getElementById('btnStartAgent').innerText = 'Starting...';
    try {
        const res = await fetch('/api/agent/start', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: target })
        });
        const data = await res.json();
        if (data.status === 'success') {
            agentSessionId = data.session_id;
            document.getElementById('agentIdleView').style.display = 'none';
            document.getElementById('agentActiveView').style.display = 'block';
            document.getElementById('agentTargetDisplay').innerText = target;
            document.getElementById('agentStepLog').innerHTML = '';
            document.getElementById('agentFinalSummary').style.display = 'none';
            agentPollTimer = setInterval(pollAgentStatus, 1000);
            pollAgentStatus();
            window._lastScanRequest = { tool: 'autonomous_agent', target: target };
        } else { alert(data.message || 'Failed to start agent.'); }
    } catch (err) { alert('Error starting agent. Check server connection.'); }
    document.getElementById('btnStartAgent').disabled = false;
    document.getElementById('btnStartAgent').innerHTML = 'ᛏ START MISSION';
}

async function pollAgentStatus() {
    if (!agentSessionId) return;
    try {
        const res = await fetch('/api/agent/status?session_id=' + agentSessionId);
        const data = await res.json();
        if (data.status !== 'success') return;
        const s = data.session;
        document.getElementById('agentPhaseBadge').innerText = s.current_phase || '';
        document.getElementById('agentStepCounter').innerText = 'Step ' + s.total_steps + '/' + s.max_steps;
        const logDiv = document.getElementById('agentStepLog');
        let html = '';
        s.steps.forEach(function (step) {
            const icon = step.status === 'completed' ? '✅' : step.status === 'running' ? '🔄' : step.status === 'blocked' ? '🚫' : '❌';
            const bgColor = step.status === 'completed' ? 'rgba(163, 190, 140, 0.04)' : step.status === 'running' ? 'rgba(235, 203, 139, 0.06)' : step.status === 'blocked' ? 'rgba(191, 97, 106, 0.06)' : 'rgba(191, 97, 106, 0.04)';
            html += '<div style="padding: 10px 14px; margin-bottom: 8px; background: ' + bgColor + '; border-left: 3px solid ' +
                (step.status === 'completed' ? '#a3be8c' : step.status === 'running' ? '#ebcb8b' : '#bf616a') + '; border-radius: 2px;">';
            html += '<div style="display: flex; justify-content: space-between; align-items: center;">';
            html += '<span>' + icon + ' <strong style="color: #ebcb8b;">Step ' + step.step + '</strong>: ' + escapeHtml(step.tool) + '</span>';
            html += '<span style="font-size: 10px; color: var(--accent-color);">' + escapeHtml(step.status.toUpperCase()) + '</span></div>';
            if (step.reasoning) html += '<div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">💭 ' + escapeHtml(step.reasoning) + '</div>';
            if (step.summary) html += '<div style="font-size: 11px; color: var(--accent-color); margin-top: 3px;">📊 ' + escapeHtml(step.summary) + '</div>';
            html += '</div>';
        });
        if (s.status === 'running' && s.current_tool) {
            html += '<div style="text-align: center; padding: 10px; color: #ebcb8b; font-style: italic;">🔄 Executing ' + escapeHtml(s.current_tool) + '...</div>';
        }
        logDiv.innerHTML = html;
        logDiv.scrollTop = logDiv.scrollHeight;
        if (s.status === 'completed' || s.status === 'stopped' || s.status === 'error') {
            clearInterval(agentPollTimer); agentPollTimer = null;
            const summaryDiv = document.getElementById('agentFinalSummary');
            summaryDiv.style.display = 'block';
            document.getElementById('agentSummaryText').innerText = s.final_summary || 'Mission complete.';
            document.getElementById('agentPhaseBadge').innerText = s.status.toUpperCase();
            document.getElementById('btnStopAgent').style.display = 'none';
            if (s.status === 'completed' && document.body.classList.contains('odin-mode')) {
                const allOutput = s.steps.map(function (st) { return st.output || ''; }).join('\n---\n');
                if (allOutput.trim()) { autoAnalyzeScan(allOutput, 'autonomous_agent', s.target); }
            }
        }
        if (s.scope_warning) {
            logDiv.innerHTML += '<div style="color: #d08770; font-size: 11px; margin-top: 8px; font-style: italic;">⚠️ ' + escapeHtml(s.scope_warning) + '</div>';
        }
    } catch (err) { }
}

async function stopAgentScan() {
    if (!agentSessionId) return;
    try {
        await fetch('/api/agent/stop', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: agentSessionId })
        });
        if (agentPollTimer) { clearInterval(agentPollTimer); agentPollTimer = null; }
        document.getElementById('btnStopAgent').style.display = 'none';
        document.getElementById('agentPhaseBadge').innerText = 'STOPPED';
    } catch (err) { }
}

// --- Auto-Exploit Panel ---
function openAutoExploitPanel() { document.getElementById('autoExploitModal').style.display = 'block'; }
function closeAutoExploitPanel() { document.getElementById('autoExploitModal').style.display = 'none'; }

async function startAutoExploit() {
    const target = document.getElementById('autoExploitTarget').value.trim();
    if (!target) { setStatus('Enter a target IP or domain', 'error'); return; }
    const logDiv = document.getElementById('autoExploitLog');
    logDiv.innerHTML = '<div style="color:#ebcb8b;">Odin starting autonomous red team operation...</div>';
    try {
        const res = await fetch('/api/agent/start', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: target, mode: 'redteam' })
        });
        const data = await res.json();
        if (data.status === 'success') {
            logDiv.innerHTML += '<div style="color:#4CAF50;">Session ' + data.session_id + ' started. Monitoring...</div>';
            window._autoExploitSession = data.session_id;
            pollAutoExploit();
        } else { logDiv.innerHTML += '<div style="color:#bf616a;">' + data.message + '</div>'; }
    } catch (e) { logDiv.innerHTML += '<div style="color:#bf616a;">Failed to start autonomous operation.</div>'; }
}

async function pollAutoExploit() {
    if (!window._autoExploitSession) return;
    try {
        const res = await fetch('/api/agent/status?session_id=' + window._autoExploitSession);
        const data = await res.json();
        if (data.status === 'success' && data.session) {
            const s = data.session;
            const logDiv = document.getElementById('autoExploitLog');
            if (s.steps) {
                s.steps.forEach(function (step) {
                    if (!window._seenAutoSteps) window._seenAutoSteps = new Set();
                    if (!window._seenAutoSteps.has(step.step)) {
                        window._seenAutoSteps.add(step.step);
                        logDiv.innerHTML += '<div style="margin:3px 0;padding:4px;border-left:2px solid ' + (step.status === 'completed' ? '#4CAF50' : '#bf616a') + ';">' +
                            '<b>Step ' + step.step + ':</b> ' + escapeHtml(step.tool) + ' — ' + escapeHtml(step.reasoning || '') +
                            '<span style="font-size:9px;color:var(--text-dim);">[' + step.status + ']</span></div>';
                    }
                });
            }
            if (s.status !== 'running') {
                logDiv.innerHTML += '<div style="color:#ebcb8b;margin-top:10px;"><b>' + escapeHtml(s.final_summary || 'Operation complete.') + '</b></div>';
                window._autoExploitSession = null;
                window._seenAutoSteps = null;
            } else { setTimeout(pollAutoExploit, 3000); }
        }
    } catch (e) { }
}

async function stopAutoExploit() {
    if (window._autoExploitSession) {
        try {
            await fetch('/api/agent/stop', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: window._autoExploitSession })
            });
        } catch (e) { }
        window._autoExploitSession = null;
        document.getElementById('autoExploitLog').innerHTML += '<div style="color:#bf616a;">Operation stopped by user.</div>';
    }
}

// --- Kvasir (RAG) ---
function openKvasirPanel() {
    document.getElementById('kvasirModal').style.display = 'block';
    document.getElementById('kvasirSearchInput').focus();
    checkKvasirStatus();
}
function closeKvasirPanel() { document.getElementById('kvasirModal').style.display = 'none'; }

async function checkKvasirStatus() {
    try {
        const res = await fetch('/api/rag/status');
        const data = await res.json();
        const statusEl = document.getElementById('kvasirStatus');
        if (data.chromadb_available && data.ollama_available) {
            statusEl.innerText = '● Online (Vector)'; statusEl.style.color = '#a3be8c';
        } else if (data.ollama_available) {
            statusEl.innerText = '● Online (Keyword)'; statusEl.style.color = '#ebcb8b';
        } else { statusEl.innerText = '● Offline KB'; statusEl.style.color = 'var(--accent-color)'; }
    } catch (e) { document.getElementById('kvasirStatus').innerText = '● Offline KB'; }
}

async function searchKvasir() {
    const query = document.getElementById('kvasirSearchInput').value.trim();
    if (!query) return;
    const resultsDiv = document.getElementById('kvasirResults');
    const searchBtn = document.getElementById('kvasirSearchBtn');
    resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--accent-color);">ᚱ Searching the roots of knowledge...</div>';
    searchBtn.disabled = true; searchBtn.innerText = '...';
    const collections = [];
    if (document.getElementById('kvasirColGTFOBins').checked) collections.push('gtfobins');
    if (document.getElementById('kvasirColExploitDB').checked) collections.push('exploitdb');
    if (document.getElementById('kvasirColPayloads').checked) collections.push('payloads');
    try {
        const res = await fetch('/api/rag/query', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, collections: collections, top_k: 5 })
        });
        const data = await res.json();
        if (data.status === 'success' && data.total_hits > 0) { renderKvasirResults(resultsDiv, data); }
        else { resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: #d08770;">ᚱ No knowledge found. Try different keywords or broader terms.</div>'; }
    } catch (err) { resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--danger-color);">⚠️ Search failed. Is the server running?</div>'; }
    searchBtn.disabled = false; searchBtn.innerText = '🔍 SEARCH';
}

function renderKvasirResults(container, data) {
    let html = '';
    const methodLabel = data.method === 'vector' ? '🧠 Vector Search' : '📖 Keyword Search';
    html += '<div style="font-size: 10px; color: var(--accent-color); margin-bottom: 15px;">' + methodLabel + ' · ' + data.total_hits + ' results · Query: "' + escapeHtml(data.query) + '"</div>';
    const collectionColors = {
        'gtfobins': { color: '#d08770', icon: '💻', label: 'GTFOBins' },
        'exploitdb': { color: '#88c0d0', icon: '⚠️', label: 'Exploit-DB' },
        'payloads': { color: '#ebcb8b', icon: '⚡', label: 'Payloads' }
    };
    for (const [colName, hits] of Object.entries(data.results)) {
        const cc = collectionColors[colName] || { color: '#a3be8c', icon: 'ᛒ', label: colName };
        html += '<div style="margin-bottom: 15px; border: 1px solid ' + cc.color + '33; border-radius: 4px; overflow: hidden;">';
        html += '<div style="background: ' + cc.color + '15; padding: 8px 12px; color: ' + cc.color + '; font-weight: bold; font-size: 12px;">' + escapeHtml(cc.icon) + ' ' + escapeHtml(cc.label) + ' (' + hits.length + ')</div>';
        hits.forEach(function (hit) {
            html += '<div style="padding: 10px 14px; border-top: 1px solid rgba(255,255,255,0.03); font-size: 12px;">';
            html += '<pre style="margin: 0; white-space: pre-wrap; color: #d8dee9; line-height: 1.5;">' + escapeHtml(hit.content) + '</pre>';
            if (hit.score !== undefined) { html += '<div style="margin-top: 4px; font-size: 10px; color: var(--accent-color);">Relevance: ' + (hit.score * 100).toFixed(0) + '%</div>'; }
            html += '</div>';
        });
        html += '</div>';
    }
    container.innerHTML = html;
}

async function indexKvasirDB() {
    const resultsDiv = document.getElementById('kvasirResults');
    resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--accent-color);">📥 Indexing knowledge base into ChromaDB...<br><small>This may take a moment.</small></div>';
    try {
        const res = await fetch('/api/rag/index', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') { resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: #a3be8c;">✅ ' + escapeHtml(data.message) + '</div>'; }
        else { resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: #d08770;">⚠️ ' + escapeHtml(data.message) + '</div>'; }
        checkKvasirStatus();
    } catch (err) { resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--danger-color);">⚠️ Indexing failed. Is the server running?</div>'; }
}

// --- Loki WAF ---
function openLokiPanel() { document.getElementById('lokiModal').style.display = 'block'; loadLokiTechniques(); }
function closeLokiPanel() { document.getElementById('lokiModal').style.display = 'none'; }

async function loadLokiTechniques() {
    try {
        const res = await fetch('/api/loki/techniques');
        const data = await res.json();
        const list = document.getElementById('lokiTechniquesList');
        if (data.status === 'success') {
            let html = '<label style="display:block; margin-bottom:3px; cursor:pointer;"><input type="checkbox" id="lokiSelectAll" checked onchange="toggleAllLokiTechniques()"> <strong>Select All</strong></label>';
            data.techniques.forEach(function (t) {
                html += '<label style="display:block; margin-bottom:3px; cursor:pointer; font-size:12px;" title="' + escapeHtml(t.description) + '">' +
                    '<input type="checkbox" class="loki-tech-cb" value="' + t.key + '" checked> ' +
                    '<span style="color:#d08770;">[' + t.category + ']</span> ' + escapeHtml(t.name) + '</label>';
            });
            list.innerHTML = html;
        }
    } catch (e) { document.getElementById('lokiTechniquesList').innerHTML = '<span style="color:var(--danger-color);">Failed to load techniques.</span>'; }
}

function toggleAllLokiTechniques() {
    const all = document.getElementById('lokiSelectAll').checked;
    document.querySelectorAll('.loki-tech-cb').forEach(function (cb) { cb.checked = all; });
}

async function mutateLokiPayload() {
    const payload = document.getElementById('lokiPayload').value.trim();
    if (!payload) return;
    const selected = [];
    document.querySelectorAll('.loki-tech-cb:checked').forEach(function (cb) { selected.push(cb.value); });
    const btn = document.getElementById('lokiMutateBtn');
    btn.disabled = true; btn.innerText = '...';
    const resultsDiv = document.getElementById('lokiResults');
    resultsDiv.innerHTML = '<div style="text-align:center;padding:30px;color:var(--accent-color);">ᚲ Shapeshifting payloads...</div>';
    try {
        const res = await fetch('/api/loki/mutate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ payload: payload, techniques: selected, count: 8 })
        });
        const data = await res.json();
        if (data.status === 'success') {
            let html = '<div style="margin-bottom:10px;font-size:11px;color:var(--accent-color);">Original: <code style="color:#d8dee9;">' + escapeHtml(data.original) + '</code> — ' + data.total_generated + ' variants</div>';
            data.mutations.forEach(function (m, i) {
                html += '<div style="margin-bottom:8px;padding:8px;background:rgba(208,135,112,0.05);border-left:3px solid #d08770;border-radius:2px;">' +
                    '<div style="font-size:10px;color:#d08770;margin-bottom:4px;">#' + (i + 1) + ' ' + escapeHtml(m.name) + ' [' + m.category + ']</div>' +
                    '<code style="color:#d8dee9;word-break:break-all;font-size:12px;">' + escapeHtml(m.payload) + '</code>' +
                    '<button onclick="navigator.clipboard.writeText(\'' + m.payload.replace(/'/g, "\\'") + '\')" style="float:right;background:none;border:1px solid rgba(208,135,112,0.4);color:#d08770;padding:1px 6px;font-size:10px;cursor:pointer;width:auto;margin:0;">COPY</button></div>';
            });
            resultsDiv.innerHTML = html;
        } else { resultsDiv.innerHTML = '<div style="color:var(--danger-color);text-align:center;padding:20px;">' + escapeHtml(data.message) + '</div>'; }
    } catch (err) { resultsDiv.innerHTML = '<div style="color:var(--danger-color);text-align:center;padding:20px;">Mutation failed.</div>'; }
    btn.disabled = false; btn.innerText = 'ᚲ MUTATE';
}

async function analyzeLokiWaf() {
    const code = document.getElementById('lokiWafCode').value;
    const body = document.getElementById('lokiWafBody').value;
    const analysisDiv = document.getElementById('lokiWafAnalysis');
    analysisDiv.innerHTML = '<span style="color:var(--accent-color);">Analyzing WAF response...</span>';
    try {
        const res = await fetch('/api/loki/analyze', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status_code: parseInt(code), response_body: body })
        });
        const data = await res.json();
        if (data.status === 'success' && data.analysis) {
            const a = data.analysis;
            let html = '<div style="padding:10px;background:rgba(208,135,112,0.06);border:1px solid rgba(208,135,112,0.3);border-radius:4px;">' +
                '<strong style="color:#d08770;">🛡️ ' + escapeHtml(a.likely_waf) + '</strong> (' + a.block_type + ')<br>' +
                '<span style="font-size:11px;">Suggested techniques: ';
            a.suggestions.forEach(function (s) {
                html += '<span style="background:rgba(208,135,112,0.15);padding:2px 6px;border-radius:2px;margin:2px;">' + escapeHtml(s.technique) + '</span> ';
            });
            html += '</span></div>';
            analysisDiv.innerHTML = html;
        }
    } catch (err) { analysisDiv.innerHTML = '<span style="color:var(--danger-color);">Analysis failed.</span>'; }
}
