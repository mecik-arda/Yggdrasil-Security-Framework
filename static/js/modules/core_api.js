// ==========================================
// Core API — SocketIO, Fetch Handlers & API Communication
// Extracted from api.js
// ==========================================

// --- Fetch override for CSRF & task_id injection ---
const originalFetch = window.fetch;
window._lastScanRequest = { tool: '', target: '' };
window.fetch = async function () {
    let [resource, config] = arguments;
    let isAction = (resource === '/api/action' || (resource && resource.indexOf('/api/action') === 0));
    if (config && config.method && config.method.toUpperCase() === 'POST') {
        config.headers = config.headers || {};
        config.headers['X-CSRFToken'] = window.csrfToken;
        if (isAction && config.body && config.body instanceof FormData) {
            if (!config.body.has('task_id')) {
                const newTaskId = crypto.randomUUID();
                config.body.append('task_id', newTaskId);
                window.pendingTasks[newTaskId] = {
                    contentDiv: null,
                    statusDiv: null,
                    win: null,
                    lines: [],
                    output_buffer: []
                };
            }
        }
    }
    const res = await originalFetch(resource, config);
    return res;
};

// --- SocketIO & Global State ---
window.socket = null;
window.socketConnected = false;
window.pendingTasks = {};
window.odinMessages = [];
window.odinCurrentModel = '';

function initSocketIO() {
    try {
        window.socket = io({ transports: ['websocket', 'polling'] });
        window.socket.on('connect', function () {
            window.socketConnected = true;
            console.log('[WS] Connected to Yggdrasil');
        });
        window.socket.on('disconnect', function () {
            window.socketConnected = false;
            console.log('[WS] Disconnected – polling fallback active');
        });

        // -- Scan events --
        window.socket.on('scan_start', function (data) {
            console.log('[WS] Scan started:', data.tool);
        });

        window.socket.on('scan_output', function (data) {
            let pt = window.pendingTasks[data.task_id];
            if (!pt) {
                pt = { lines: [], output_buffer: [], contentDiv: null, statusDiv: null };
                window.pendingTasks[data.task_id] = pt;
            }
            if (!pt.lines) pt.lines = [];
            pt.lines.push(data.line);

            if (pt.contentDiv) {
                if (pt.contentDiv.innerHTML.includes('CONNECTING TO THE WORLD TREE')) {
                    pt.contentDiv.innerHTML = '';
                }
                const lineSpan = document.createElement('span');
                lineSpan.textContent = data.line + '\n';
                pt.contentDiv.appendChild(lineSpan);
                pt.contentDiv.scrollTop = pt.contentDiv.scrollHeight;
            } else {
                if (!pt.output_buffer) pt.output_buffer = [];
                pt.output_buffer.push(data.line);
            }
        });

        window.socket.on('scan_complete', function (data) {
            const pt = window.pendingTasks[data.task_id];
            if (pt) {
                if (pt.contentDiv && (!pt.lines || pt.lines.length === 0)) {
                    pt.contentDiv.innerHTML = '';
                    if (data.type === 'html' && data.trusted_source) {
                        pt.contentDiv.innerHTML = data.output || '';
                    } else if (data.output) {
                        typeWriter(pt.contentDiv, data.output, 0);
                    }
                }
                if (pt.statusDiv) {
                    pt.statusDiv.innerText = window.t('operation_complete');
                    pt.statusDiv.style.color = 'var(--highlight-color)';
                    pt.statusDiv.style.borderColor = 'var(--highlight-color)';
                }
                if (pt.win && data.output) {
                    parseScanOutput(pt.win._scanTool, pt.win._scanTarget, data.output);
                }
                updateStats();
                pt.isComplete = true;
                pt.finalData = data;
                if (pt.contentDiv) {
                    delete window.pendingTasks[data.task_id];
                }
            } else {
                window.pendingTasks[data.task_id] = { isComplete: true, finalData: data };
            }
        });

        window.socket.on('scan_error', function (data) {
            const pt = window.pendingTasks[data.task_id];
            if (pt) {
                if (pt.statusDiv) {
                    pt.statusDiv.innerText = 'ERROR: ' + (data.error || '');
                    pt.statusDiv.style.color = 'var(--danger-color)';
                    pt.statusDiv.style.borderColor = 'var(--danger-color)';
                }
                delete window.pendingTasks[data.task_id];
            }
        });

        // -- Heartbeat --
        window.socket.on('heartbeat', function (data) {
            document.getElementById('heartbeat-cpu-val').innerText = (data.cpu || 0).toFixed(0) + '%';
            document.getElementById('heartbeat-cpu-bar').style.width = (data.cpu || 0) + '%';
            document.getElementById('heartbeat-ram-val').innerText = (data.ram || 0).toFixed(0) + '%';
            document.getElementById('heartbeat-ram-bar').style.width = (data.ram || 0) + '%';
            const pingEl = document.getElementById('heartbeat-ping-val');
            if (data.ping != null) {
                pingEl.innerText = 'ONLINE (' + data.ping + 'ms)';
                pingEl.style.color = '#a3be8c';
            } else {
                pingEl.innerText = 'OFFLINE';
                pingEl.style.color = '#bf616a';
            }
            const aiEl = document.getElementById('heartbeat-ai-val');
            if (data.ollama) {
                aiEl.innerText = 'ONLINE';
                aiEl.style.color = '#a3be8c';
            } else {
                aiEl.innerText = 'OFFLINE';
                aiEl.style.color = '#bf616a';
            }
        });

        // -- Stats --
        window.socket.on('stats_update', function (data) {
            document.getElementById('stat-scans').innerText = data.total_scans || 0;
            document.getElementById('stat-target').innerText = data.last_target || 'NONE';
        });

        // -- Log Dashboard --
        window.socket.on('log_entry', function (data) {
            const liveToggle = document.getElementById('logLiveToggle');
            if (liveToggle && liveToggle.checked) {
                if (typeof prependLogRow === 'function') prependLogRow(data);
            }
        });

        window.socket.on('log_stats_update', function (data) {
            if (typeof updateLogStatsBadges === 'function') updateLogStatsBadges(data);
        });

    } catch (e) {
        console.log('[WS] Init failed – using polling fallback:', e.message);
        window.socketConnected = false;
    }
}

async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        document.getElementById('stat-scans').innerText = stats.total_scans;
        document.getElementById('stat-target').innerText = stats.last_target;
    } catch (e) { }
}

function handleTaskResponse(data, contentDiv, statusDiv, win) {
    if (data.status === 'pending') {
        if (win) win._taskId = data.task_id;

        if (window.socketConnected) {
            let pt = window.pendingTasks[data.task_id];
            if (!pt) {
                pt = { lines: [], output_buffer: [] };
                window.pendingTasks[data.task_id] = pt;
            }
            pt.contentDiv = contentDiv;
            pt.statusDiv = statusDiv;
            pt.win = win;

            if (pt.isComplete) {
                if (contentDiv) {
                    contentDiv.innerHTML = '';
                    if (pt.finalData && pt.finalData.type === 'html' && pt.finalData.trusted_source) {
                        contentDiv.innerHTML = pt.finalData.output || '';
                    } else {
                        const finalOutput = (pt.finalData && pt.finalData.output) ? pt.finalData.output : '';
                        if (finalOutput) {
                            typeWriter(contentDiv, finalOutput, 0);
                        } else {
                            contentDiv.innerHTML = '<span style="color:var(--highlight-color)">[Process completed with no output]</span>';
                        }
                    }
                }
                if (statusDiv) {
                    statusDiv.innerText = window.t('operation_complete');
                    statusDiv.style.color = 'var(--highlight-color)';
                    statusDiv.style.borderColor = 'var(--highlight-color)';
                }
                delete window.pendingTasks[data.task_id];
            } else {
                if (pt.output_buffer && pt.output_buffer.length > 0) {
                    if (contentDiv.innerHTML.includes('CONNECTING TO THE WORLD TREE')) {
                        contentDiv.innerHTML = '';
                    }
                    pt.output_buffer.forEach(function (line) {
                        const lineSpan = document.createElement('span');
                        lineSpan.textContent = line + '\n';
                        contentDiv.appendChild(lineSpan);
                    });
                    contentDiv.scrollTop = contentDiv.scrollHeight;
                    pt.output_buffer = [];
                }
            }
        } else {
            pollTaskStatus(data.task_id, contentDiv, statusDiv, win, 0);
        }
    } else if (data.status === 'success') {
        contentDiv.innerHTML = '';
        if (data.type === 'html' && data.trusted_source) { contentDiv.innerHTML = data.output || ''; }
        else { typeWriter(contentDiv, data.output || '', 0); }
        if (statusDiv) { statusDiv.innerText = window.t('operation_complete'); statusDiv.style.color = 'var(--highlight-color)'; statusDiv.style.borderColor = 'var(--highlight-color)'; }
        if (win && data.output) { parseScanOutput(win._scanTool, win._scanTarget, data.output); }
        updateStats();
    } else {
        contentDiv.innerHTML = '<pre style="color:var(--danger-color);">' + escapeHtml(data.message) + '</pre>';
        if (statusDiv) { statusDiv.innerText = 'ERROR'; statusDiv.style.color = 'var(--danger-color)'; statusDiv.style.borderColor = 'var(--danger-color)'; }
    }
}

async function pollTaskStatus(taskId, contentDiv, statusDiv, win, offset) {
    try {
        const response = await fetch('/api/task/' + taskId + '?offset=' + offset);
        const data = await response.json();
        if (data.status === 'success' || data.status === 'error') {
            if (contentDiv && (!contentDiv.innerHTML || contentDiv.innerHTML.includes('CONNECTING'))) {
                contentDiv.innerHTML = '';
                if (data.type === 'html' && data.trusted_source) { contentDiv.innerHTML = data.output || ''; }
                else { typeWriter(contentDiv, data.output || '', 0); }
            }
            if (statusDiv) {
                statusDiv.innerText = data.status === 'success' ? window.t('operation_complete') : 'ERROR: ' + (data.message || 'Unknown');
                statusDiv.style.color = data.status === 'success' ? 'var(--highlight-color)' : 'var(--danger-color)';
            }
            if (data.status === 'success' && win && data.output) { parseScanOutput(win._scanTool, win._scanTarget, data.output); }
            updateStats();
            return;
        }
        if (data.status === 'pending') {
            if (data.output_lines && data.output_lines.length > 0) {
                if (contentDiv.innerHTML.includes('CONNECTING TO THE WORLD TREE')) { contentDiv.innerHTML = ''; }
                data.output_lines.forEach(function (line) {
                    const lineSpan = document.createElement('span');
                    lineSpan.textContent = line + '\n';
                    contentDiv.appendChild(lineSpan);
                });
                contentDiv.scrollTop = contentDiv.scrollHeight;
                offset = data.next_offset;
            }
            setTimeout(function () { pollTaskStatus(taskId, contentDiv, statusDiv, win, offset); }, 2000);
        }
    } catch (e) { }
}

async function runCustomHandler(action, formData, title) {
    const target = formData.get('target') || document.getElementById('target-input').value;
    const { contentDiv, statusDiv, win } = openTerminalWindow(title || 'PROCESS', action, target);
    try {
        formData.append('tool', action);
        formData.append('action', 'run');
        const response = await fetch('/api/action', { method: 'POST', body: formData });
        const data = await response.json();
        handleTaskResponse(data, contentDiv, statusDiv, win);
    } catch (error) {
        contentDiv.innerHTML = '<span style="color:var(--danger-color);">' + escapeHtml(error.message) + '</span>';
        statusDiv.innerText = window.t('err_execute');
        statusDiv.style.color = 'var(--danger-color)';
    }
}

async function runTool(toolName) {
    const target = document.getElementById('target-input').value.trim();
    if (window.toolsConfig && window.toolsConfig[toolName] && window.toolsConfig[toolName].requires_target && !target) {
        alert(window.t('err_target'));
        document.getElementById('target-input').focus();
        return;
    }
    if (window.toolsConfig && window.toolsConfig[toolName]) {
        const tConf = window.toolsConfig[toolName];
        if (tConf.requires_target) {
            window._lastScanRequest = { tool: toolName, target: target };
        } else {
            window._lastScanRequest = { tool: toolName, target: 'N/A' };
        }
    }
    try {
        const response = await fetch('/api/tool/check', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool: toolName })
        });
        const data = await response.json();
        if (data.status === 'missing') {
            showInstallModal(toolName);
        } else {
            executeTool(toolName, target);
        }
    } catch (error) {
        alert(window.t('err_execute') + ': ' + error);
    }
}

async function executeTool(tool, target) {
    if (tool === 'google_dorks') {
        openTerminalWindow(tool, target);
        generateDorks(target);
        return;
    }
    if (tool === 'wayback') {
        openTerminalWindow(tool, target);
        runWayback(target);
        return;
    }

    const { contentDiv, statusDiv, win } = openTerminalWindow(tool, tool, target);
    try {
        const formData = new FormData();
        formData.append('tool', tool);
        formData.append('target', target);
        formData.append('action', 'run');
        const response = await fetch('/api/action', { method: 'POST', body: formData });
        const data = await response.json();
        handleTaskResponse(data, contentDiv, statusDiv, win);
    } catch (error) {
        contentDiv.innerHTML = '<span style="color:var(--danger-color);">' + escapeHtml(error.message) + '</span>';
        statusDiv.innerText = window.t('err_execute');
        statusDiv.style.color = 'var(--danger-color)';
        statusDiv.style.borderColor = 'var(--danger-color)';
    }
}

// --- Heartbeat Monitor ---
let heartbeatInterval;

function startHeartbeatMonitor() {
    updateHeartbeat();
    heartbeatInterval = setInterval(updateHeartbeat, 5000);
}

async function updateHeartbeat() {
    try {
        const response = await fetch('/api/heartbeat');
        const data = await response.json();
        document.getElementById('heartbeat-cpu-val').innerText = data.cpu.toFixed(0) + '%';
        document.getElementById('heartbeat-cpu-bar').style.width = data.cpu + '%';
        document.getElementById('heartbeat-ram-val').innerText = data.ram.toFixed(0) + '%';
        document.getElementById('heartbeat-ram-bar').style.width = data.ram + '%';

        const pingEl = document.getElementById('heartbeat-ping-val');
        if (data.ping != null) {
            pingEl.innerText = 'ONLINE (' + data.ping + 'ms)';
            pingEl.style.color = '#a3be8c';
        } else {
            pingEl.innerText = 'OFFLINE';
            pingEl.style.color = '#bf616a';
        }

        const aiEl = document.getElementById('heartbeat-ai-val');
        if (data.ollama) {
            aiEl.innerText = 'ONLINE';
            aiEl.style.color = '#a3be8c';
        } else {
            aiEl.innerText = 'OFFLINE';
            aiEl.style.color = '#bf616a';
        }

        const activeDiv = document.getElementById('heartbeat-active-scans');
        let scansHtml = '';
        if (data.active_scans && data.active_scans.length > 0) {
            data.active_scans.forEach(function (scan) {
                scansHtml += '<div style="margin-top: 5px; font-size: 10px; color: var(--text-dim); display:flex; justify-content:space-between;">' +
                    '<span>🔄 ' + escapeHtml(scan.tool) + ' (' + escapeHtml(scan.target) + ')</span>' +
                    '<button onclick="abortHeartbeatScan(\'' + scan.task_id + '\')" style="background:none; border:1px solid #bf616a; color:#bf616a; padding:1px 4px; font-size:8px; cursor:pointer;">ABORT</button></div>';
            });
        } else {
            scansHtml = '<div style="margin-top: 5px; font-size: 10px; color: var(--text-dim);">No active scans</div>';
        }
        activeDiv.innerHTML = scansHtml;

    } catch (e) {
        document.getElementById('heartbeat-ping-val').innerText = 'ERROR';
        document.getElementById('heartbeat-ping-val').style.color = '#bf616a';
    }
}

async function abortHeartbeatScan(taskId) {
    try {
        await fetch('/api/task/' + taskId + '/abort', { method: 'POST' });
        updateHeartbeat();
    } catch (e) { }
}

// --- Helper ---
function setStatus(msg, type) {
    const statusDiv = document.getElementById('status-display');
    if (statusDiv) {
        statusDiv.innerText = msg;
        if (type === 'error') { statusDiv.style.color = 'var(--danger-color)'; }
        else { statusDiv.style.color = 'var(--highlight-color)'; }
    }
}
