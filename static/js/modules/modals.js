// ==========================================
// modals.js — Modal Open/Close & Form Submissions
// Yggdrasil Security Framework
// ==========================================

// --- Dependency Manager ---
async function openDependencyManager() {
    document.getElementById('depManagerModal').style.display = 'block';
    const tbody = document.getElementById('depTableBody');
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">' + window.t('dep_fetching') + '</td></tr>';
    try {
        const response = await fetch('/api/dependencies');
        const deps = await response.json();
        tbody.innerHTML = '';
        deps.forEach(function (dep) {
            const statusColor = dep.installed ? '#a3be8c' : 'var(--danger-color)';
            let statusText = window.t('dep_missing');
            if (dep.installed) {
                if (dep.installed_platform === 'wsl') statusText = window.t('dep_installed') + ' (WSL)';
                else if (dep.installed_platform === 'windows') statusText = window.t('dep_installed') + ' (Windows)';
                else if (dep.installed_platform === 'linux') statusText = window.t('dep_installed') + ' (Linux)';
                else statusText = window.t('dep_installed');
            }
            const supportColor = dep.supported ? (dep.is_wsl ? '#b48ead' : 'var(--highlight-color)') : '#888';
            const supportText = dep.supported ? (dep.is_wsl ? 'NATIVE (WSL)' : window.t('dep_native')) : window.t('dep_manual');
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid rgba(136, 192, 208, 0.2)';
            tr.innerHTML =
                '<td style="padding: 10px;"><input type="checkbox" class="dep-checkbox" value="' + escapeHtml(dep.tool_key) + '"></td>' +
                '<td style="padding: 10px; font-weight: bold;">' + escapeHtml(dep.tool_key) + '</td>' +
                '<td style="padding: 10px;">' + escapeHtml(dep.name) + '</td>' +
                '<td style="padding: 10px; color: ' + statusColor + '; font-weight: bold;">' + escapeHtml(statusText) + '</td>' +
                '<td style="padding: 10px; color: ' + supportColor + ';">' + escapeHtml(supportText) + '</td>';
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--danger-color);">' + window.t('dep_fetch_fail') + '</td></tr>';
    }
}

function closeDependencyManager() { document.getElementById('depManagerModal').style.display = 'none'; }

function toggleSelectAllDeps() {
    const selectAll = document.getElementById('selectAllDeps').checked;
    document.querySelectorAll('.dep-checkbox').forEach(function (cb) { cb.checked = selectAll; });
}

async function installSelectedDependencies() {
    const checkboxes = document.querySelectorAll('.dep-checkbox:checked');
    const toolsToInstall = Array.from(checkboxes).map(function (cb) { return cb.value; });
    if (toolsToInstall.length === 0) { alert(window.t('dep_err_select')); return; }
    closeDependencyManager();
    for (const tool of toolsToInstall) {
        const contentDiv = createTerminalWindow(window.t('dep_installing') + tool.toUpperCase());
        const statusDiv = document.getElementById('status-display');
        statusDiv.innerText = window.t('initiating_ritual', { tool: tool.toUpperCase() });
        typeWriter(contentDiv, window.t('dep_req_seq') + tool + '...\n', 0);
        const formData = new FormData();
        formData.append('tool', tool);
        formData.append('action', 'install');
        try {
            const response = await fetch('/api/action', { method: 'POST', body: formData });
            const data = await response.json();
            const msg = data.message || 'Unknown error';
            if (data.status === 'success') { contentDiv.innerText += '\n' + window.t('dep_success') + '\n\n' + msg; }
            else { contentDiv.innerText += '\n' + window.t('dep_err_seq') + '\n\n' + msg; }
        } catch (error) { contentDiv.innerText += '\n' + window.t('dep_sys_err') + error; }
        contentDiv.scrollTop = contentDiv.scrollHeight;
    }
}

async function updateSelectedDependencies() {
    const checkboxes = document.querySelectorAll('.dep-checkbox:checked');
    const toolsToInstall = Array.from(checkboxes).map(function (cb) { return cb.value; });
    if (toolsToInstall.length === 0) { alert(window.t('dep_err_select') || 'Please select at least one tool.'); return; }
    closeDependencyManager();
    for (const tool of toolsToInstall) {
        const contentDiv = createTerminalWindow('UPDATING: ' + tool.toUpperCase());
        const statusDiv = document.getElementById('status-display');
        statusDiv.innerText = '>> UPDATING ' + tool.toUpperCase() + '...';
        typeWriter(contentDiv, 'Sending update command for ' + tool + '...\n', 0);
        const formData = new FormData();
        formData.append('tool', tool);
        formData.append('action', 'update');
        try {
            const response = await fetch('/api/action', { method: 'POST', body: formData });
            const data = await response.json();
            const msg = data.message || 'Unknown error';
            if (data.status === 'success') { contentDiv.innerText += '\n[+] UPDATE SUCCESSFUL:\n\n' + msg; }
            else { contentDiv.innerText += '\n[-] UPDATE FAILED:\n\n' + msg; }
        } catch (error) { contentDiv.innerText += '\n[!] SYSTEM ERROR: ' + error; }
        contentDiv.scrollTop = contentDiv.scrollHeight;
    }
}

async function removeSelectedDependencies() {
    const checkboxes = document.querySelectorAll('.dep-checkbox:checked');
    const toolsToInstall = Array.from(checkboxes).map(function (cb) { return cb.value; });
    if (toolsToInstall.length === 0) { alert(window.t('dep_err_select') || 'Please select at least one tool.'); return; }
    if (!confirm('Are you sure you want to remove the selected tools?')) return;
    closeDependencyManager();
    for (const tool of toolsToInstall) {
        const contentDiv = createTerminalWindow('REMOVING: ' + tool.toUpperCase());
        const statusDiv = document.getElementById('status-display');
        statusDiv.innerText = '>> REMOVING ' + tool.toUpperCase() + '...';
        typeWriter(contentDiv, 'Sending removal command for ' + tool + '...\n', 0);
        const formData = new FormData();
        formData.append('tool', tool);
        formData.append('action', 'remove');
        try {
            const response = await fetch('/api/action', { method: 'POST', body: formData });
            const data = await response.json();
            const msg = data.message || 'Unknown error';
            if (data.status === 'success') { contentDiv.innerText += '\n[-] UNINSTALL SUCCESSFUL:\n\n' + msg; }
            else { contentDiv.innerText += '\n[!] UNINSTALL FAILED:\n\n' + msg; }
        } catch (error) { contentDiv.innerText += '\n[!] SYSTEM ERROR: ' + error; }
        contentDiv.scrollTop = contentDiv.scrollHeight;
    }
}

// --- AI Package Manager ---
let currentAiTiers = [];
let installedAiModels = [];

async function openAiPackageManager() {
    document.getElementById('aiPackageManagerModal').style.display = 'block';
    await refreshAiPackageManager();
}
function closeAiPackageManager() { document.getElementById('aiPackageManagerModal').style.display = 'none'; }

async function refreshAiPackageManager() {
    const container = document.getElementById('aiTiersContainer');
    container.innerHTML = '<div style="text-align:center; padding: 20px;">Summoning tiers...</div>';
    try {
        const [modelsRes, diskRes] = await Promise.all([fetch('/api/ai/models'), fetch('/api/ai/disk')]);
        const modelsData = await modelsRes.json();
        const diskData = await diskRes.json();
        if (diskData.status === 'success') {
            document.getElementById('aiDiskUsage').innerText = 'ᛚ Disk Used: ' + diskData.total_size_gb.toFixed(2) + ' GB (' + diskData.total_models + ' models)';
        }
        currentAiTiers = modelsData.tiers ? modelsData.tiers.tiers || [] : [];
        installedAiModels = modelsData.installed ? modelsData.installed.models ? modelsData.installed.models.map(function (m) { return m.name; }) : [] : [];
        container.innerHTML = '';
        currentAiTiers.forEach(function (tier, index) {
            const isSelected = index === 1;
            const tierDiv = document.createElement('div');
            tierDiv.style.cssText = 'border: 1px solid ' + (isSelected ? '#b48ead' : 'rgba(180, 142, 173, 0.3)') + '; border-radius: 4px; padding: 15px; background: ' + (isSelected ? 'rgba(180, 142, 173, 0.1)' : 'rgba(0,0,0,0.2)') + '; cursor: pointer; transition: all 0.3s;';
            tierDiv.onclick = function () { selectAiTier(tier.id); };
            tierDiv.id = 'ai-tier-card-' + tier.id;
            let modelsHtml = '';
            tier.models.forEach(function (m) {
                const isInstalled = installedAiModels.some(function (im) { return im.startsWith(m) || m.startsWith(im.split(':')[0]); });
                const statusColor = isInstalled ? '#a3be8c' : 'var(--text-dim)';
                const statusIcon = isInstalled ? '✅' : '❌';
                modelsHtml += '<span style="display:inline-block; margin-right: 15px; color: ' + statusColor + ';">' + statusIcon + ' ' + m + '</span>';
            });
            tierDiv.innerHTML =
                '<div style="display: flex; align-items: flex-start; gap: 15px;">' +
                '<input type="radio" name="aiTierSelect" value="' + tier.id + '" ' + (isSelected ? 'checked' : '') + ' style="margin-top: 5px; accent-color: #b48ead; transform: scale(1.2);">' +
                '<div style="flex: 1;">' +
                '<div style="font-weight: bold; color: ' + (isSelected ? '#b48ead' : 'var(--wood-light)') + '; font-size: 16px; margin-bottom: 5px;" id="ai-tier-title-' + tier.id + '">' + (window.t(tier.id + '_title') || tier.name) + '</div>' +
                '<div style="color: var(--text-color); font-size: 13px; margin-bottom: 8px;">' + (window.t(tier.id + '_desc') || tier.description) + '</div>' +
                '<div style="font-size: 12px; color: var(--accent-color); margin-bottom: 8px;">' + (window.t(tier.id + '_specs') || '<strong>RAM:</strong> ' + tier.ram + ' | <strong>GPU:</strong> ' + tier.gpu + ' | <strong>Speed:</strong> ' + tier.speed) + '</div>' +
                '<div style="font-size: 13px; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 4px;">' + modelsHtml + '</div></div></div>';
            container.appendChild(tierDiv);
        });
    } catch (e) {
        container.innerHTML = '<div style="color:var(--danger-color); padding: 20px;">Error loading AI tiers: ' + escapeHtml(String(e)) + '</div>';
    }
}

function selectAiTier(tierId) {
    document.querySelector('input[name="aiTierSelect"][value="' + tierId + '"]').checked = true;
    currentAiTiers.forEach(function (t) {
        const card = document.getElementById('ai-tier-card-' + t.id);
        const title = document.getElementById('ai-tier-title-' + t.id);
        if (t.id === tierId) {
            card.style.border = '1px solid #b48ead';
            card.style.background = 'rgba(180, 142, 173, 0.1)';
            title.style.color = '#b48ead';
        } else {
            card.style.border = '1px solid rgba(180, 142, 173, 0.3)';
            card.style.background = 'rgba(0,0,0,0.2)';
            title.style.color = 'var(--wood-light)';
        }
    });
}

function getSelectedAiTier() {
    const selected = document.querySelector('input[name="aiTierSelect"]:checked');
    if (!selected) return null;
    return currentAiTiers.find(function (t) { return t.id === selected.value; });
}

async function installSelectedAiTier() {
    const tier = getSelectedAiTier();
    if (!tier) return alert('No tier selected');
    for (const model of tier.models) {
        try {
            const res = await fetch('/api/ai/pull', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: model })
            });
            const data = await res.json();
            if (data.status !== 'success') { alert('Error pulling ' + model + ': ' + data.message); }
        } catch (e) { alert('Network error pulling ' + model); }
    }
}

async function updateSelectedAiTier() { await installSelectedAiTier(); }

async function purgeSelectedAiTier() {
    const tier = getSelectedAiTier();
    if (!tier) return alert('No tier selected');
    if (!confirm('Are you sure you want to purge all models in ' + tier.name + '?')) return;
    for (const model of tier.models) {
        const installedMatch = installedAiModels.find(function (im) { return im.startsWith(model) || model.startsWith(im.split(':')[0]); });
        const modelToRemove = installedMatch || model;
        try {
            const res = await fetch('/api/ai/remove', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: modelToRemove })
            });
        } catch (e) { }
    }
    alert('Purge completed for ' + tier.name + '.');
    await refreshAiPackageManager();
}

// --- Install Modal ---
function showInstallModal(toolName) {
    const toolInfo = window.toolsConfig[toolName];
    const displayName = toolInfo ? toolInfo.name : toolName;
    document.getElementById('installMsg').innerText = 'The tool \'' + displayName.toUpperCase() + '\' is not present.\n\nDo you wish to summon it now?';
    document.getElementById('installModal').style.display = 'block';
}

function closeModal(modalId) {
    if (typeof modalId === 'string' && modalId.trim() !== '') {
        const el = document.getElementById(modalId);
        if (el) el.style.display = 'none';
    } else {
        const instModal = document.getElementById('installModal');
        if (instModal) instModal.style.display = 'none';
        const statDisp = document.getElementById('status-display');
        if (statDisp && typeof window.t === 'function') statDisp.innerText = '>> RITUAL ' + window.t('abort') + 'ED.';
    }
}

async function confirmInstall() {
    closeModal();
    const statusDiv = document.getElementById('status-display');
    const toolInfo = window.toolsConfig[currentTool || ''];
    const displayName = toolInfo ? toolInfo.name : (currentTool || 'TOOL');
    statusDiv.innerText = '>> SUMMONING ' + displayName.toUpperCase() + '... PLEASE WAIT...';
    const formData = new FormData();
    formData.append('tool', currentTool || '');
    formData.append('action', 'install');
    try {
        const response = await fetch('/api/action', { method: 'POST', body: formData });
        const data = await response.json();
        if (data.status === 'success') {
            statusDiv.innerText = '>> SUMMONING COMPLETE. ENGAGING TOOL...';
            const target = document.getElementById('target-input').value;
            executeTool(currentTool, target);
        } else {
            statusDiv.innerText = '>> SUMMONING FAILED: ' + data.message;
            statusDiv.style.color = 'var(--danger-color)';
        }
    } catch (error) { statusDiv.innerText = 'INSTALLATION ERROR: ' + error; }
}

// --- Update Check ---
let updateContentDiv = null;

async function initiateUpdateCheck() {
    const statusDiv = document.getElementById('status-display');
    statusDiv.innerText = '>> CONSULTING THE ARCHIVES FOR KNOWLEDGE (CHECKING UPDATES)...';
    statusDiv.style.color = 'var(--wood-light)';
    updateContentDiv = createTerminalWindow('[ SYSTEM OPERATIONS - RUNE SYNC ]');
    updateContentDiv.innerHTML = '<span style=\'color: var(--highlight-color);\'>[ SCANNING GITHUB REPOSITORIES... ]</span>';
    const formData = new FormData();
    formData.append('action', 'check_updates');
    try {
        const response = await fetch('/api/action', { method: 'POST', body: formData });
        const data = await response.json();
        if (data.updates && data.updates.length > 0) {
            let html = '<div style="color: var(--wood-light); margin-bottom: 20px; font-family: monospace;">' +
                '<h3>[ ᛊ ] NEW KNOWLEDGE DISCOVERED</h3>' +
                '<p>The following Runes have updates available from their source:</p>' +
                '<ul style="color: var(--highlight-color);">';
            data.updates.forEach(function (u) { html += '<li>' + escapeHtml(u) + '</li>'; });
            html += '</ul><p>Do you wish to integrate these updates into the framework?</p>' +
                '<button onclick="applyUpdates()" class="btn-install" style="margin-right: 10px; width: auto; padding: 10px 20px;">YES, INTEGRATE UPDATES</button>' +
                '<button onclick="cancelUpdates()" class="btn-cancel" style="width: auto; padding: 10px 20px;">NO, KEEP CURRENT</button></div>';
            updateContentDiv.innerHTML = html;
            statusDiv.innerText = '>> AWAITING YOUR COMMAND.';
        } else {
            updateContentDiv.innerHTML = '<span style=\'color: #a3be8c;\'>[ ALL RUNES ARE CURRENTLY UP TO DATE. THE ROOTS ARE UNTOUCHED. ]</span>';
            statusDiv.innerText = '>> THE ARCHIVES ARE SYNCED.';
        }
    } catch (error) {
        if (updateContentDiv) updateContentDiv.innerText = 'RUNTIME ERROR: ' + error;
        statusDiv.innerText = window.t('chant_failed');
        statusDiv.style.color = 'var(--danger-color)';
    }
}

function cancelUpdates() {
    if (updateContentDiv) { updateContentDiv.innerHTML = '<span style=\'color: #a3be8c;\'>[ UPDATE ' + window.t('cancel') + 'LED. THE ROOTS REMAIN UNTOUCHED. ]</span>'; }
    document.getElementById('status-display').innerText = '>> OPERATION ' + window.t('abort') + 'ED.';
}

async function applyUpdates() {
    const statusDiv = document.getElementById('status-display');
    statusDiv.innerText = '>> WEAVING NEW FATE (APPLYING UPDATES & RECOMPILING)...';
    if (updateContentDiv) { updateContentDiv.innerHTML = '<span style=\'color: var(--highlight-color);\'>[ DOWNLOADING AND INTEGRATING... ]</span>'; }
    const formData = new FormData();
    formData.append('action', 'apply_updates');
    try {
        const response = await fetch('/api/action', { method: 'POST', body: formData });
        const data = await response.json();
        if (updateContentDiv) { setSanitizedHtml(updateContentDiv, data.output || ''); }
        statusDiv.innerText = '>> FATE HAS BEEN WOVEN. UPDATES INTEGRATED.';
        statusDiv.style.color = 'var(--highlight-color)';
    } catch (error) {
        if (updateContentDiv) updateContentDiv.innerText = 'RUNTIME ERROR: ' + error;
        statusDiv.innerText = window.t('chant_failed');
        statusDiv.style.color = 'var(--danger-color)';
    }
}

// --- Hydra Modal ---
function openHydraModal() { document.getElementById('hydraModal').style.display = 'block'; }
function closeHydraModal() { document.getElementById('hydraModal').style.display = 'none'; }

function toggleHydraUserMode() {
    const mode = document.getElementById('hydraUserMode').value;
    const input = document.getElementById('hydraUserVal');
    if (mode === 'list') { input.placeholder = '/path/to/users.txt'; input.value = '/usr/share/wordlists/fasttrack.txt'; }
    else { input.placeholder = 'admin'; input.value = 'admin'; }
}

function toggleHydraPassMode() {
    const mode = document.getElementById('hydraPassMode').value;
    const input = document.getElementById('hydraPassVal');
    if (mode === 'list') { input.placeholder = '/path/to/passwords.txt'; input.value = '/usr/share/wordlists/rockyou.txt'; }
    else { input.placeholder = 'password123'; input.value = 'password123'; }
}

async function submitHydraScan() {
    const target = document.getElementById('target-input').value;
    if (!target) { alert(window.t('err_target')); return; }
    closeHydraModal();
    const statusDiv = document.getElementById('status-display');
    statusDiv.innerText = '>> WEAVING FATE WITH HYDRA...';
    statusDiv.style.color = 'var(--wood-light)';
    const protocol = document.getElementById('hydraProtocol').value;
    const port = document.getElementById('hydraPort').value;
    const threads = document.getElementById('hydraThreads').value;
    const userMode = document.getElementById('hydraUserMode').value;
    const userVal = document.getElementById('hydraUserVal').value;
    const passMode = document.getElementById('hydraPassMode').value;
    const passVal = document.getElementById('hydraPassVal').value;
    const verbose = document.getElementById('hydraVerbose').checked ? 'true' : 'false';
    const formData = new FormData();
    formData.append('tool', 'hydra');
    formData.append('target', target);
    formData.append('action', 'run');
    formData.append('protocol', protocol);
    formData.append('port', port);
    formData.append('threads', threads);
    formData.append('user_type', userMode);
    formData.append('user_val', userVal);
    formData.append('pass_type', passMode);
    formData.append('pass_val', passVal);
    formData.append('verbose', verbose);
    window._lastScanRequest = { tool: 'hydra', target: target };
    const contentDiv = createTerminalWindow('[ HYDRA - ' + target + ' ]', 'hydra', target);
    contentDiv.innerHTML = '<span style=\'color: var(--highlight-color);\'>[ INITIATING BRUTE FORCE RITUAL... ]</span>';
    try {
        const response = await fetch('/api/action', { method: 'POST', body: formData });
        const data = await response.json();
        contentDiv.innerHTML = '';
        contentDiv.innerHTML = highlightSafe(data.output);
        updateStats();
    } catch (error) {
        contentDiv.innerHTML = '<span style="color:var(--danger-color);">RUNTIME ERROR: ' + escapeHtml(String(error)) + '</span>';
    }
}

// --- Subfinder Modal ---
function openSubfinderModal() { document.getElementById('subfinderModal').style.display = 'block'; }
function closeSubfinderModal() { document.getElementById('subfinderModal').style.display = 'none'; }

async function submitSubfinderScan() {
    const target = document.getElementById('target-input').value;
    if (!target) { alert(window.t('err_target')); return; }
    closeSubfinderModal();
    const threads = document.getElementById('subfinderThreads').value;
    const all_sources = document.getElementById('subfinderAll').checked ? 'true' : 'false';
    const formData = new FormData();
    formData.append('target', target);
    formData.append('action', 'subfinder');
    formData.append('threads', threads);
    formData.append('all_sources', all_sources);
    runCustomHandler('subfinder', formData, '[ SUBFINDER - ' + target + ' ]');
}

// --- Knockpy Modal ---
function openKnockpyModal() { document.getElementById('knockpyModal').style.display = 'block'; }
function closeKnockpyModal() { document.getElementById('knockpyModal').style.display = 'none'; }

async function submitKnockpyScan() {
    const target = document.getElementById('target-input').value;
    if (!target) { alert(window.t('err_target')); return; }
    closeKnockpyModal();
    const threads = document.getElementById('knockpyThreads').value;
    const wordlist = document.getElementById('knockpyWordlist').value;
    const formData = new FormData();
    formData.append('target', target);
    formData.append('action', 'knockpy');
    formData.append('threads', threads);
    formData.append('wordlist', wordlist);
    runCustomHandler('knockpy', formData, '[ KNOCKPY - ' + target + ' ]');
}

// --- Gobuster DNS Modal ---
function openGobusterDnsModal() { document.getElementById('gobusterDnsModal').style.display = 'block'; }
function closeGobusterDnsModal() { document.getElementById('gobusterDnsModal').style.display = 'none'; }

async function submitGobusterDnsScan() {
    const target = document.getElementById('target-input').value;
    if (!target) { alert(window.t('err_target')); return; }
    closeGobusterDnsModal();
    const threads = document.getElementById('gobusterThreads').value;
    const wordlist = document.getElementById('gobusterWordlist').value;
    const formData = new FormData();
    formData.append('target', target);
    formData.append('tool', 'gobuster_dns');
    formData.append('action', 'run');
    formData.append('threads', threads);
    formData.append('wordlist', wordlist);
    runCustomHandler('gobuster_dns', formData, '[ GOBUSTER DNS - ' + target + ' ]');
}

// --- Muninn Modal ---
function openMuninnModal() { document.getElementById('muninnScannerModal').style.display = 'block'; }
function closeMuninnModal() { document.getElementById('muninnScannerModal').style.display = 'none'; }

async function submitMuninnScan() {
    const target = document.getElementById('target-input').value;
    if (!target) { alert(window.t('err_target')); return; }
    closeMuninnModal();
    const formData = new FormData();
    formData.append('target', target);
    formData.append('tool', 'muninn_scanner');
    formData.append('action', 'run');
    if (document.getElementById('muninnOptAll').checked) formData.append('all', 'true');
    if (document.getElementById('muninnOptNuclei').checked) formData.append('nuclei', 'true');
    if (document.getElementById('muninnOptNmap').checked) formData.append('nmap', 'true');
    if (document.getElementById('muninnOptMonitor').checked) formData.append('monitor', 'true');
    runCustomHandler('muninn_scan', formData, '[ MUNINN SCAN - ' + target + ' ]');
}

// --- Sleipnir Modal ---
function openSleipnirModal() {
    document.getElementById('sleipnirScannerModal').style.display = 'block';
    var target = document.getElementById('target-input').value;
    if (target) {
        document.getElementById('sleipnirUrl').value = target;
    }
    // Thread slider listener
    var threadSlider = document.getElementById('sleipnirThreads');
    var threadVal = document.getElementById('sleipnirThreadsVal');
    threadSlider.oninput = function () {
        threadVal.innerText = this.value;
    };
}

function closeSleipnirModal() {
    document.getElementById('sleipnirScannerModal').style.display = 'none';
}

async function submitSleipnirScan() {
    var target = document.getElementById('sleipnirUrl').value.trim();
    if (!target) {
        alert(window.t('err_target') || 'Please enter a target URL.');
        return;
    }
    closeSleipnirModal();
    var formData = new FormData();
    formData.append('tool', 'sleipnir_scanner');
    formData.append('target', target);
    formData.append('action', 'run');
    formData.append('sleipnir_mode', document.getElementById('sleipnirMode').value);
    formData.append('sleipnir_profile', document.getElementById('sleipnirProfile').value);
    formData.append('sleipnir_threads', document.getElementById('sleipnirThreads').value);
    formData.append('sleipnir_headers', document.getElementById('sleipnirHeaders').value);
    window._lastScanRequest = { tool: 'sleipnir_scanner', target: target };
    runCustomHandler('sleipnir_scan', formData, '[ SLEIPNIR - ' + target + ' ]');
}

// --- SYN Modal ---
function openSynModal() {
    document.getElementById('synScannerModal').style.display = 'block';
    const target = document.getElementById('target-input').value;
    if (target) {
        document.getElementById('synAutoTarget').value = target;
        document.getElementById('synManTarget').value = target;
    }
}
function closeSynModal() { document.getElementById('synScannerModal').style.display = 'none'; }

function toggleSynFields() {
    const mode = document.getElementById('synMode').value;
    if (mode === 'auto') {
        document.getElementById('synAutoFields').style.display = 'block';
        document.getElementById('synManualFields').style.display = 'none';
    } else {
        document.getElementById('synAutoFields').style.display = 'none';
        document.getElementById('synManualFields').style.display = 'block';
    }
}

function submitSynScan() {
    closeSynModal();
    const mode = document.getElementById('synMode').value;
    let target = '';
    const formData = new FormData();
    formData.append('tool', 'adv_syn_scan');
    formData.append('action', 'run');
    formData.append('syn_mode', mode);
    if (mode === 'auto') {
        target = document.getElementById('synAutoTarget').value;
        formData.append('target', target);
        formData.append('max_port', document.getElementById('synAutoPort').value || '1000');
    } else {
        target = document.getElementById('synManTarget').value;
        formData.append('target', target);
        formData.append('source_ip', document.getElementById('synManSource').value);
        formData.append('start_port', document.getElementById('synManStart').value || '1');
        formData.append('end_port', document.getElementById('synManEnd').value || '1000');
    }
    const statusDiv = document.getElementById('status-display');
    if (!target) {
        statusDiv.innerText = window.t('err_target');
        statusDiv.style.color = 'var(--danger-color)';
        statusDiv.style.borderColor = 'var(--danger-color)';
        return;
    }
    currentTool = 'adv_syn_scan';
    statusDiv.style.color = 'var(--wood-light)';
    statusDiv.style.borderColor = 'var(--wood-light)';
    statusDiv.innerText = window.t('weaving_syn', { target: target });
    window._lastScanRequest = { tool: 'adv_syn_scan', target: target };
    const contentDiv = createTerminalWindow('[ ADVANCED SYN SCAN - ' + target + ' ]', 'adv_syn_scan', target);
    contentDiv.innerHTML = '<span style=\'color: var(--highlight-color);\'>[ CONNECTING TO THE WORLD TREE... ]</span>';
    fetch('/api/action', { method: 'POST', body: formData })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            const win = contentDiv ? contentDiv.parentNode.parentNode : null;
            handleTaskResponse(data, contentDiv, statusDiv, win);
        })
        .catch(function (error) {
            contentDiv.innerText = window.t('runtime_error') + error;
            statusDiv.innerText = window.t('chant_failed');
            statusDiv.style.color = 'var(--danger-color)';
            statusDiv.style.borderColor = 'var(--danger-color)';
        });
}

// --- Erebus Modal ---
function openErebusModal() {
    document.getElementById('erebusScannerModal').style.display = 'block';
    const target = document.getElementById('target-input').value;
    if (target) { document.getElementById('erebusTarget').value = target; }
}
function closeErebusModal() { document.getElementById('erebusScannerModal').style.display = 'none'; }

function submitErebusScan() {
    closeErebusModal();
    const target = document.getElementById('erebusTarget').value;
    const ports = document.getElementById('erebusPorts').value || '1-1024';
    const proxy = document.getElementById('erebusProxy').value;
    const banner = document.getElementById('erebusBanner').checked;
    const randomize = document.getElementById('erebusRandomize').checked;
    const adaptive = document.getElementById('erebusAdaptive').checked;
    const statusDiv = document.getElementById('status-display');
    if (!target) {
        statusDiv.innerText = window.t('err_target_erebus');
        statusDiv.style.color = 'var(--danger-color)'; statusDiv.style.borderColor = 'var(--danger-color)';
        return;
    }
    const formData = new FormData();
    formData.append('tool', 'erebus');
    formData.append('action', 'run');
    formData.append('target', target);
    formData.append('ports', ports);
    if (proxy && proxy.trim()) { formData.append('proxy', proxy.trim()); }
    formData.append('banner', banner ? 'true' : 'false');
    formData.append('randomize', randomize ? 'true' : 'false');
    formData.append('adaptive', adaptive ? 'true' : 'false');
    currentTool = 'erebus';
    statusDiv.style.color = 'var(--wood-light)'; statusDiv.style.borderColor = 'var(--wood-light)';
    statusDiv.innerText = window.t('weaving_erebus', { target: target });
    window._lastScanRequest = { tool: 'erebus', target: target };
    const contentDiv = createTerminalWindow('[ EREBUS SCANNER - ' + target + ' ]', 'erebus', target);
    contentDiv.innerHTML = '<span style=\'color: var(--highlight-color);\'>[ CONNECTING TO THE WORLD TREE / CARGO RUNNING... ]</span>';
    fetch('/api/action', { method: 'POST', body: formData })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            const win = contentDiv ? contentDiv.parentNode.parentNode : null;
            handleTaskResponse(data, contentDiv, statusDiv, win);
        })
        .catch(function (error) {
            contentDiv.innerText = window.t('runtime_error') + error;
            statusDiv.innerText = window.t('chant_failed');
            statusDiv.style.color = 'var(--danger-color)'; statusDiv.style.borderColor = 'var(--danger-color)';
        });
}

// --- Packet Injector Modal ---
function openPacketInjectorModal() {
    document.getElementById('packetInjectorModal').style.display = 'block';
    const target = document.getElementById('target-input').value;
    if (target) { document.getElementById('injectorTarget').value = target; }
}
function closePacketInjectorModal() { document.getElementById('packetInjectorModal').style.display = 'none'; }

function toggleInjectorFields() {
    const action = document.getElementById('injectorAction').value;
    const injectFields = document.getElementById('injectorInjectFields');
    if (action === 'inject') { injectFields.style.display = 'block'; toggleInjectorProtocolFields(); }
    else { injectFields.style.display = 'none'; }
}

function toggleInjectorProtocolFields() {
    const protocol = document.getElementById('injectorProtocol').value;
    if (protocol === 'tcp') { document.getElementById('injectorTcpFields').style.display = 'block'; document.getElementById('injectorArpFields').style.display = 'none'; }
    else if (protocol === 'arp') { document.getElementById('injectorTcpFields').style.display = 'none'; document.getElementById('injectorArpFields').style.display = 'block'; }
}

function submitPacketInjector() {
    closePacketInjectorModal();
    const action = document.getElementById('injectorAction').value;
    const iface = document.getElementById('injectorInterface').value || 'eth0';
    const target = document.getElementById('injectorTarget').value;
    const formData = new FormData();
    formData.append('tool', 'packet_injector');
    formData.append('action', 'run');
    formData.append('packet_action', action);
    formData.append('interface', iface);
    if (action === 'inject') {
        const protocol = document.getElementById('injectorProtocol').value;
        formData.append('protocol', protocol);
        formData.append('target', target);
        formData.append('src_ip', document.getElementById('injectorSrcIp').value);
        formData.append('src_mac', document.getElementById('injectorSrcMac').value);
        formData.append('dst_mac', document.getElementById('injectorDstMac').value);
        formData.append('ttl', document.getElementById('injectorTtl').value);
        if (protocol === 'tcp') {
            formData.append('dst_port', document.getElementById('injectorDstPort').value);
            formData.append('src_port', document.getElementById('injectorSrcPort').value);
            formData.append('seq', document.getElementById('injectorSeq').value);
            formData.append('ack_num', document.getElementById('injectorAckNum').value);
            formData.append('window', document.getElementById('injectorWindow').value);
            formData.append('flags', document.getElementById('injectorFlags').value);
        } else if (protocol === 'arp') {
            formData.append('arp_op', document.getElementById('injectorArpOp').value);
        }
        formData.append('rate', document.getElementById('injectorRate').value);
        formData.append('count', document.getElementById('injectorCount').value);
        formData.append('duration', document.getElementById('injectorDuration').value);
        formData.append('burst', document.getElementById('injectorBurst').value);
    } else { formData.append('target', target || 'none'); }
    const statusDiv = document.getElementById('status-display');
    if (action === 'inject' && !target) {
        statusDiv.innerText = window.t('err_target_injection');
        statusDiv.style.color = 'var(--danger-color)'; statusDiv.style.borderColor = 'var(--danger-color)';
        return;
    }
    currentTool = 'packet_injector';
    statusDiv.style.color = 'var(--wood-light)'; statusDiv.style.borderColor = 'var(--wood-light)';
    statusDiv.innerText = window.t('initiating_injector', { action: action.toUpperCase(), interface: iface });
    window._lastScanRequest = { tool: 'packet_injector', target: target };
    const contentDiv = createTerminalWindow('[ PACKET INJECTOR - ' + action.toUpperCase() + ' ]', 'packet_injector', target || '');
    contentDiv.innerHTML = '<span style=\'color: var(--highlight-color);\'>[ ENGAGING PACKET CRAFTING ENGINE... ]</span>';
    fetch('/api/action', { method: 'POST', body: formData })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            const win = contentDiv ? contentDiv.parentNode.parentNode : null;
            handleTaskResponse(data, contentDiv, statusDiv, win);
        })
        .catch(function (error) {
            contentDiv.innerText = window.t('runtime_error') + error;
            statusDiv.innerText = window.t('crafting_failed');
            statusDiv.style.color = 'var(--danger-color)'; statusDiv.style.borderColor = 'var(--danger-color)';
        });
}

// --- Fenrir Modal ---
function openFenrirModal() {
    document.getElementById('fenrirModal').style.display = 'block';
    const target = document.getElementById('target-input').value;
    if (target) { document.getElementById('fenrirTarget').value = target; }
}
function closeFenrirModal() { document.getElementById('fenrirModal').style.display = 'none'; }

function submitFenrirScan() {
    closeFenrirModal();
    const target = document.getElementById('fenrirTarget').value;
    const hashMode = document.getElementById('fenrirHashMode').value;
    const attackMode = document.getElementById('fenrirAttackMode').value;
    const wordlist = document.getElementById('fenrirWordlist').value;
    if (!target) {
        const statusDiv = document.getElementById('status-display');
        statusDiv.innerText = window.t('err_target_req');
        statusDiv.style.color = 'var(--danger-color)';
        return;
    }
    if (isProcessRunning) { alert(window.t('err_process_run')); return; }
    const formData = new FormData();
    formData.append('tool', 'fenrir');
    formData.append('target', target);
    formData.append('action', 'run');
    formData.append('fenrir_hash_mode', hashMode);
    formData.append('fenrir_attack_mode', attackMode);
    formData.append('fenrir_wordlist', wordlist);
    isProcessRunning = true;
    currentTool = 'fenrir';
    const statusDiv = document.getElementById('status-display');
    statusDiv.innerText = '>> AWAKENING FENRIR ON [ ' + escapeHtml(target) + ' ]...';
    window._lastScanRequest = { tool: 'fenrir', target: target };
    const contentDiv = createTerminalWindow('[ ᚹ FENRIR - ' + escapeHtml(hashMode.toUpperCase()) + ' - ' + escapeHtml(target) + ' ]', 'fenrir', target);
    fetch('/api/action', { method: 'POST', body: formData })
        .then(function (response) { return response.json(); })
        .then(function (data) {
            isProcessRunning = false;
            if (data.status === 'success') {
                contentDiv.innerHTML = '<pre>' + escapeHtml(data.output) + '</pre>';
                statusDiv.innerText = window.t('fate_woven');
            } else {
                contentDiv.innerHTML = '<pre style="color:var(--danger-color);">' + escapeHtml(data.message) + '</pre>';
                statusDiv.innerText = window.t('err_execute');
            }
        })
        .catch(function (error) { isProcessRunning = false; console.error('Error:', error); statusDiv.innerText = window.t('err_network'); });
}

// --- WSL Settings ---
async function openWslSettings() {
    document.getElementById('wslSettingsModal').style.display = 'block';
    const select = document.getElementById('wslDistroSelect');
    select.innerHTML = '<option value="">Loading...</option>';
    try {
        const res = await fetch('/api/wsl/distros');
        const data = await res.json();
        select.innerHTML = '<option value="">-- Auto-Detect / Default --</option>';
        data.distros.forEach(function (distro) {
            const opt = document.createElement('option');
            opt.value = distro; opt.textContent = distro;
            if (data.preferred === distro) opt.selected = true;
            select.appendChild(opt);
        });
    } catch (err) { select.innerHTML = '<option value="">Failed to load distros</option>'; }
}

function closeWslSettings() { document.getElementById('wslSettingsModal').style.display = 'none'; }

async function saveWslSettings() {
    const select = document.getElementById('wslDistroSelect');
    const distro = select.value;
    try {
        const res = await fetch('/api/wsl/config', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ distro: distro })
        });
        const data = await res.json();
        const statusDiv = document.getElementById('status-display');
        if (data.status === 'success') { statusDiv.innerText = 'WSL configuration updated successfully.'; }
        else { statusDiv.innerText = 'Failed to update WSL configuration: ' + data.message; }
    } catch (err) { document.getElementById('status-display').innerText = 'Error saving WSL configuration.'; }
    closeWslSettings();
}

// --- Odin Chat Modal ---
async function openOdinChat() {
    document.getElementById('odinChatModal').style.display = 'block';
    document.getElementById('odinChatInput').focus();
    await refreshOdinModels();
    loadOdinTierInfo();
}
function closeOdinChat() { document.getElementById('odinChatModal').style.display = 'none'; }

async function refreshOdinModels() {
    const select = document.getElementById('odinModelSelect');
    const status = document.getElementById('odinStatus');
    select.innerHTML = '<option value="">-- Checking Ollama... --</option>';
    try {
        const res = await fetch('/api/ai/status');
        const data = await res.json();
        if (data.status === 'success') {
            status.innerText = '● ONLINE'; status.style.color = '#a3be8c';
            select.innerHTML = '';
            if (data.models && data.models.length > 0) {
                data.models.forEach(function (m) {
                    const opt = document.createElement('option');
                    opt.value = m.name; opt.textContent = m.name;
                    if (m.name === window.odinCurrentModel) opt.selected = true;
                    select.appendChild(opt);
                });
                if (!window.odinCurrentModel || !data.models.find(function (m) { return m.name === window.odinCurrentModel; })) {
                    window.odinCurrentModel = data.models[0].name;
                    select.value = window.odinCurrentModel;
                }
            } else { select.innerHTML = '<option value="">-- No models installed --</option>'; }
        } else {
            status.innerText = '● OFFLINE'; status.style.color = 'var(--danger-color)';
            select.innerHTML = '<option value="">-- Ollama not running --</option>';
        }
    } catch (err) {
        status.innerText = '● OFFLINE'; status.style.color = 'var(--danger-color)';
        select.innerHTML = '<option value="">-- Connection error --</option>';
    }
}

function onOdinModelChange() { window.odinCurrentModel = document.getElementById('odinModelSelect').value; }

function handleOdinKeypress(event) { if (event.key === 'Enter') { event.preventDefault(); sendOdinMessage(); } }

async function sendOdinMessage() {
    const input = document.getElementById('odinChatInput');
    const sendBtn = document.getElementById('odinSendBtn');
    const userMessage = input.value.trim();
    if (!userMessage) return;
    if (!window.odinCurrentModel) { addOdinMessage('system', 'No AI model selected. Please install a model first (use PULL button).'); return; }
    addOdinMessage('user', userMessage);
    window.odinMessages.push({ role: 'user', content: userMessage });
    input.value = ''; input.disabled = true; sendBtn.disabled = true; sendBtn.innerText = '...';
    const thinkingId = 'odin-thinking-' + Date.now();
    const msgArea = document.getElementById('odinChatMessages');
    const thinkingDiv = document.createElement('div');
    thinkingDiv.id = thinkingId;
    thinkingDiv.style.cssText = 'color: var(--accent-color); font-style: italic; padding: 8px 0;';
    thinkingDiv.innerText = 'ᛟ Odin is thinking...';
    msgArea.appendChild(thinkingDiv);
    msgArea.scrollTop = msgArea.scrollHeight;
    try {
        const res = await fetch('/api/ai/chat', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: window.odinCurrentModel, messages: window.odinMessages })
        });
        const data = await res.json();
        const thinkEl = document.getElementById(thinkingId);
        if (thinkEl) thinkEl.remove();
        if (data.status === 'success') {
            addOdinMessage('assistant', data.response);
            window.odinMessages.push({ role: 'assistant', content: data.response });
        } else { addOdinMessage('system', 'Error: ' + escapeHtml(data.message || 'Unknown error')); }
    } catch (err) {
        const thinkEl = document.getElementById(thinkingId);
        if (thinkEl) thinkEl.remove();
        addOdinMessage('system', 'Network error: Could not reach the server.');
    }
    input.disabled = false; sendBtn.disabled = false; sendBtn.innerText = 'SEND ᛫'; input.focus();
}

function addOdinMessage(role, content) {
    const msgArea = document.getElementById('odinChatMessages');
    const div = document.createElement('div');
    div.style.cssText = 'margin-bottom: 12px; padding: 10px; border-radius: 4px; white-space: pre-wrap; word-break: break-word;';
    if (role === 'user') {
        div.style.background = 'rgba(136, 192, 208, 0.1)'; div.style.borderLeft = '3px solid var(--highlight-color)';
        div.innerHTML = '<span style="color: var(--highlight-color); font-weight: bold;">᛫ YOU:</span>\n' + escapeHtml(content);
    } else if (role === 'assistant') {
        div.style.background = 'rgba(235, 203, 139, 0.08)'; div.style.borderLeft = '3px solid #ebcb8b';
        div.innerHTML = '<span style="color: #ebcb8b; font-weight: bold;">ᛟ ODIN:</span>\n' + escapeHtml(content);
    } else {
        div.style.background = 'rgba(191, 97, 106, 0.1)'; div.style.borderLeft = '3px solid var(--danger-color)';
        div.style.color = 'var(--danger-color)'; div.innerText = '⚡ ' + content;
    }
    const placeholder = msgArea.querySelector('div[style*="text-align: center"]');
    if (placeholder) placeholder.remove();
    msgArea.appendChild(div);
    msgArea.scrollTop = msgArea.scrollHeight;
}

async function pullOdinModel() {
    const modelName = prompt('Enter model name to pull (e.g. qwen2.5-coder:7b, deepseek-r1:14b):\n\nRecommended Tier 2 models:\n- qwen2.5-coder:7b\n- deepseek-r1:14b\n- llama3.2:3b');
    if (!modelName || !modelName.trim()) return;
    addOdinMessage('system', 'Starting pull for: ' + modelName + '\nCheck the new terminal window for progress...');
    try {
        const res = await fetch('/api/ai/pull', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: modelName.trim() })
        });
        const data = await res.json();
        addOdinMessage('system', data.message || (data.status === 'success' ? 'Pull started.' : 'Pull failed.'));
    } catch (err) { addOdinMessage('system', 'Error starting model pull.'); }
}

async function removeOdinModel() {
    if (!window.odinCurrentModel) { alert('No model selected to remove.'); return; }
    if (!confirm('Remove model "' + window.odinCurrentModel + '"?\nThis will free disk space but the model will need to be re-downloaded to use again.')) return;
    addOdinMessage('system', 'Removing model: ' + window.odinCurrentModel + '...');
    try {
        const res = await fetch('/api/ai/remove', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: window.odinCurrentModel })
        });
        const data = await res.json();
        addOdinMessage('system', data.message || 'Model removed.');
        window.odinCurrentModel = '';
        await refreshOdinModels();
    } catch (err) { addOdinMessage('system', 'Error removing model.'); }
}

function clearOdinChat() {
    window.odinMessages = [];
    const msgArea = document.getElementById('odinChatMessages');
    msgArea.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 60px 20px;"><div style="font-size: 48px; margin-bottom: 15px;">ᛟ</div><p style="color: #ebcb8b;">Chat cleared. Odin awaits your command.</p></div>';
}

async function loadOdinTierInfo() {
    try {
        const res = await fetch('/api/ai/tiers');
        const data = await res.json();
        const tierDiv = document.getElementById('odinTierInfo');
        let html = '';
        if (data.tiers) {
            html += '<strong>Hardware Tiers:</strong> ';
            data.tiers.forEach(function (t) { html += '<span style="margin: 0 10px; color: #ebcb8b;">[' + t.name.split(':')[0] + ']</span> '; });
        }
        try {
            const diskRes = await fetch('/api/ai/disk');
            const diskData = await diskRes.json();
            if (diskData.status === 'success') { html += '<span style="margin-left: 10px; color: var(--accent-color);">| ᛚ ' + diskData.total_size_gb + ' GB used by ' + diskData.total_models + ' models</span>'; }
        } catch (e) { }
        html += '<span style="color: var(--text-dim); margin-left: 10px;">— Use PULL to download models</span>';
        tierDiv.innerHTML = html;
    } catch (e) { }
}
