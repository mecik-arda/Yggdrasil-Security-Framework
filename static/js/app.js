const originalFetch = window.fetch;
        window._lastScanRequest = { tool: '', target: '' };
        window.fetch = async function() {
            let [resource, config] = arguments;
            if (config && config.method && config.method.toUpperCase() === 'POST') {
                config.headers = config.headers || {};
                config.headers['X-CSRFToken'] = window.csrfToken;
            }
            const res = await originalFetch(resource, config);
            if (resource === '/api/action') {
                const clone = res.clone();
                try {
                    const data = await clone.json();
                    if (data.status === 'pending' && data.task_id) {
                        const taskId = data.task_id;
                        const scanInfo = { ...window._lastScanRequest };
                        while (true) {
                            await new Promise(r => setTimeout(r, 1000));
                            const pollRes = await originalFetch('/api/task_status?task_id=' + taskId);
                            const pollData = await pollRes.json();
                            if (pollData.status !== 'running') {
                                if (pollData.status === 'success' && pollData.output && pollData.output.trim()) {
                                    autoAnalyzeScan(pollData.output, scanInfo.tool || 'unknown', scanInfo.target || '');
                                }
                                return new Response(JSON.stringify(pollData), {
                                    status: 200,
                                    headers: { 'Content-Type': 'application/json' }
                                });
                            }
                        }
                    }
                } catch(e) { }
            }
            return res;
        };
        const translations = window.jsTranslations;
        function t(key, params={}) {
            let text = translations[key] || key;
            for (const [k, v] of Object.entries(params)) {
                text = text.replace(`{${k}}`, v);
            }
            return text;
        }
        function setLang(lang) {
            fetch('/api/set_lang', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lang: lang })
            }).then(() => window.location.reload());
        }
        let currentTool = '';
        let typewriterTimeouts = [];
        let isProcessRunning = false;
        function escapeHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }
        function highlightSafe(output) {
            let safe = escapeHtml(output);
            safe = safe.replace(/&gt;&gt; SYSTEM ERROR/g, '<span style="color:var(--danger-color); font-weight:bold;">&gt;&gt; SYSTEM ERROR</span>');
            safe = safe.replace(/\[\+\]/g, '<span style="color:var(--highlight-color); font-weight:bold;">[+]</span>');
            safe = safe.replace(/\[-\]/g, '<span style="color:var(--danger-color); font-weight:bold;">[-]</span>');
            return safe;
        }
        async function loadTools() {
            try {
                const response = await fetch('/api/tools');
                const tools = await response.json();
                window.toolsConfig = tools;
                Object.keys(tools).forEach(toolKey => {
                    const tool = tools[toolKey];
                    const categoryContainer = document.querySelector(`[data-category="${tool.category}"]`);
                    if (categoryContainer) {
                        const btn = document.createElement('button');
                        btn.innerText = t(tool.name);
                        btn.onclick = () => {
                            if (toolKey === 'update_modules') {
                                initiateUpdateCheck();
                            } else if (tool.has_modal) {
                                if (toolKey === 'erebus') {
                                    openErebusModal();
                                    return;
                                }
                                if (toolKey === 'fenrir') {
                                    openFenrirModal();
                                    return;
                                }
                                if (toolKey === 'packet_injector') {
                                    openPacketInjectorModal();
                                } else if (toolKey === 'hydra') {
                                    openHydraModal();
                                } else if (toolKey === 'subfinder') {
                                    openSubfinderModal();
                                } else if (toolKey === 'knockpy') {
                                    openKnockpyModal();
                                } else if (toolKey === 'gobuster_dns') {
                                    openGobusterDnsModal();
                                } else if (toolKey === 'muninn_scanner') {
                                    openMuninnModal();
                                } else {
                                    openSynModal();
                                }
                            } else {
                                runTool(toolKey);
                            }
                        };
                        categoryContainer.appendChild(btn);
                    }
                });
            } catch (e) {}
        }
        loadTools();
        async function updateStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                document.getElementById('stat-scans').innerText = stats.total_scans;
                document.getElementById('stat-target').innerText = stats.last_target;
            } catch (e) {}
        }
        setInterval(updateStats, 5000);
        updateStats();
        async function openDependencyManager() {
            document.getElementById('depManagerModal').style.display = 'block';
            const tbody = document.getElementById('depTableBody');
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">' + t('dep_fetching') + '</td></tr>';
            try {
                const response = await fetch('/api/dependencies');
                const deps = await response.json();
                tbody.innerHTML = '';
                deps.forEach(dep => {
                    const statusColor = dep.installed ? '#a3be8c' : 'var(--danger-color)';
                    const statusText = dep.installed ? t('dep_installed') : t('dep_missing');
                    const supportColor = dep.supported ? (dep.is_wsl ? '#b48ead' : 'var(--highlight-color)') : '#888';
                    const supportText = dep.supported ? (dep.is_wsl ? 'NATIVE (WSL)' : t('dep_native')) : t('dep_manual');
                    const disabledAttr = '';
                    const tr = document.createElement('tr');
                    tr.style.borderBottom = '1px solid rgba(136, 192, 208, 0.2)';
                    tr.innerHTML = `
                        <td style="padding: 10px;"><input type="checkbox" class="dep-checkbox" value="${escapeHtml(dep.tool_key)}" ${disabledAttr}></td>
                        <td style="padding: 10px; font-weight: bold;">${escapeHtml(dep.tool_key)}</td>
                        <td style="padding: 10px;">${escapeHtml(dep.name)}</td>
                        <td style="padding: 10px; color: ${statusColor}; font-weight: bold;">${escapeHtml(statusText)}</td>
                        <td style="padding: 10px; color: ${supportColor};">${escapeHtml(supportText)}</td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch (e) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--danger-color);">' + t('dep_fetch_fail') + '</td></tr>';
            }
        }
        function closeDependencyManager() {
            document.getElementById('depManagerModal').style.display = 'none';
        }
        function toggleSelectAllDeps() {
            const selectAll = document.getElementById('selectAllDeps').checked;
            const checkboxes = document.querySelectorAll('.dep-checkbox');
            checkboxes.forEach(cb => cb.checked = selectAll);
        }
        async function installSelectedDependencies() {
            const checkboxes = document.querySelectorAll('.dep-checkbox:checked');
            const toolsToInstall = Array.from(checkboxes).map(cb => cb.value);
            if (toolsToInstall.length === 0) {
                alert(t('dep_err_select'));
                return;
            }
            closeDependencyManager();
            for (const tool of toolsToInstall) {
                const contentDiv = createTerminalWindow(t('dep_installing') + tool.toUpperCase());
                const statusDiv = document.getElementById('status-display');
                statusDiv.innerText = t('initiating_ritual', {tool: tool.toUpperCase()});
                typeWriter(contentDiv, t('dep_req_seq') + tool + '...\n', 0);
                const formData = new FormData();
                formData.append('tool', tool);
                formData.append('action', 'install');
                try {
                    const response = await fetch('/api/action', { method: 'POST', body: formData });
                    const data = await response.json();
                    const msg = data.message || "Unknown error";
                    if (data.status === 'success') {
                        contentDiv.innerText += '\n' + t('dep_success') + '\n\n' + msg;
                    } else {
                        contentDiv.innerText += '\n' + t('dep_err_seq') + '\n\n' + msg;
                    }
                } catch (error) {
                    contentDiv.innerText += '\n' + t('dep_sys_err') + error;
                }
                contentDiv.scrollTop = contentDiv.scrollHeight;
            }
        }
        async function updateSelectedDependencies() {
            const checkboxes = document.querySelectorAll('.dep-checkbox:checked');
            const toolsToInstall = Array.from(checkboxes).map(cb => cb.value);
            if (toolsToInstall.length === 0) {
                alert(t('dep_err_select') || "Please select at least one tool.");
                return;
            }
            closeDependencyManager();
            for (const tool of toolsToInstall) {
                const contentDiv = createTerminalWindow("UPDATING: " + tool.toUpperCase());
                const statusDiv = document.getElementById('status-display');
                statusDiv.innerText = ">> UPDATING " + tool.toUpperCase() + "...";
                typeWriter(contentDiv, "Sending update command for " + tool + '...\n', 0);
                const formData = new FormData();
                formData.append('tool', tool);
                formData.append('action', 'update');
                try {
                    const response = await fetch('/api/action', { method: 'POST', body: formData });
                    const data = await response.json();
                    const msg = data.message || "Unknown error";
                    if (data.status === 'success') {
                        contentDiv.innerText += '\n[+] UPDATE SUCCESSFUL:\n\n' + msg;
                    } else {
                        contentDiv.innerText += '\n[-] UPDATE FAILED:\n\n' + msg;
                    }
                } catch (error) {
                    contentDiv.innerText += '\n[!] SYSTEM ERROR: ' + error;
                }
                contentDiv.scrollTop = contentDiv.scrollHeight;
            }
        }
        async function removeSelectedDependencies() {
            const checkboxes = document.querySelectorAll('.dep-checkbox:checked');
            const toolsToInstall = Array.from(checkboxes).map(cb => cb.value);
            if (toolsToInstall.length === 0) {
                alert(t('dep_err_select') || "Please select at least one tool.");
                return;
            }
            if(!confirm("Are you sure you want to remove the selected tools?")) return;
            closeDependencyManager();
            for (const tool of toolsToInstall) {
                const contentDiv = createTerminalWindow("REMOVING: " + tool.toUpperCase());
                const statusDiv = document.getElementById('status-display');
                statusDiv.innerText = ">> REMOVING " + tool.toUpperCase() + "...";
                typeWriter(contentDiv, "Sending removal command for " + tool + '...\n', 0);
                const formData = new FormData();
                formData.append('tool', tool);
                formData.append('action', 'remove');
                try {
                    const response = await fetch('/api/action', { method: 'POST', body: formData });
                    const data = await response.json();
                    const msg = data.message || "Unknown error";
                    if (data.status === 'success') {
                        contentDiv.innerText += '\n[-] UNINSTALL SUCCESSFUL:\n\n' + msg;
                    } else {
                        contentDiv.innerText += '\n[!] UNINSTALL FAILED:\n\n' + msg;
                    }
                } catch (error) {
                    contentDiv.innerText += '\n[!] SYSTEM ERROR: ' + error;
                }
                contentDiv.scrollTop = contentDiv.scrollHeight;
            }
        }
        let currentAiTiers = [];
        let installedAiModels = [];
        async function openAiPackageManager() {
            document.getElementById('aiPackageManagerModal').style.display = 'block';
            await refreshAiPackageManager();
        }
        function closeAiPackageManager() {
            document.getElementById('aiPackageManagerModal').style.display = 'none';
        }
        async function refreshAiPackageManager() {
            const container = document.getElementById('aiTiersContainer');
            container.innerHTML = '<div style="text-align:center; padding: 20px;">Summoning tiers...</div>';
            try {
                const [modelsRes, diskRes] = await Promise.all([
                    fetch('/api/ai/models'),
                    fetch('/api/ai/disk')
                ]);
                const modelsData = await modelsRes.json();
                const diskData = await diskRes.json();
                if (diskData.status === 'success') {
                    document.getElementById('aiDiskUsage').innerText = `ᛚ Disk Used: ${diskData.total_size_gb.toFixed(2)} GB (${diskData.total_models} models)`;
                }
                currentAiTiers = modelsData.tiers?.tiers || [];
                installedAiModels = modelsData.installed?.models?.map(m => m.name) || [];
                container.innerHTML = '';
                currentAiTiers.forEach((tier, index) => {
                    const isSelected = index === 1; // Default select Tier 2
                    const tierDiv = document.createElement('div');
                    tierDiv.style.cssText = `border: 1px solid ${isSelected ? '#b48ead' : 'rgba(180, 142, 173, 0.3)'}; border-radius: 4px; padding: 15px; background: ${isSelected ? 'rgba(180, 142, 173, 0.1)' : 'rgba(0,0,0,0.2)'}; cursor: pointer; transition: all 0.3s;`;
                    tierDiv.onclick = () => selectAiTier(tier.id);
                    tierDiv.id = `ai-tier-card-${tier.id}`;
                    let modelsHtml = '';
                    tier.models.forEach(m => {
                        const isInstalled = installedAiModels.some(im => im.startsWith(m) || m.startsWith(im.split(':')[0]));
                        const statusColor = isInstalled ? '#a3be8c' : 'var(--text-dim)';
                        const statusIcon = isInstalled ? '✅' : '❌';
                        modelsHtml += `<span style="display:inline-block; margin-right: 15px; color: ${statusColor};">${statusIcon} ${m}</span>`;
                    });
                    tierDiv.innerHTML = `
                        <div style="display: flex; align-items: flex-start; gap: 15px;">
                            <input type="radio" name="aiTierSelect" value="${tier.id}" ${isSelected ? 'checked' : ''} style="margin-top: 5px; accent-color: #b48ead; transform: scale(1.2);">
                            <div style="flex: 1;">
                                <div style="font-weight: bold; color: ${isSelected ? '#b48ead' : 'var(--wood-light)'}; font-size: 16px; margin-bottom: 5px;" id="ai-tier-title-${tier.id}">${t(tier.id + '_title') || tier.name}</div>
                                <div style="color: var(--text-color); font-size: 13px; margin-bottom: 8px;">${t(tier.id + '_desc') || tier.description}</div>
                                <div style="font-size: 12px; color: var(--accent-color); margin-bottom: 8px;">
                                    ${t(tier.id + '_specs') || `<strong>RAM:</strong> ${tier.ram} | <strong>GPU:</strong> ${tier.gpu} | <strong>Speed:</strong> ${tier.speed}`}
                                </div>
                                <div style="font-size: 13px; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 4px;">
                                    ${modelsHtml}
                                </div>
                            </div>
                        </div>
                    `;
                    container.appendChild(tierDiv);
                });
            } catch (e) {
                container.innerHTML = `<div style="color:var(--danger-color); padding: 20px;">Error loading AI tiers: ${escapeHtml(String(e))}</div>`;
            }
        }
        function selectAiTier(tierId) {
            document.querySelector(`input[name="aiTierSelect"][value="${tierId}"]`).checked = true;
            currentAiTiers.forEach(t => {
                const card = document.getElementById(`ai-tier-card-${t.id}`);
                const title = document.getElementById(`ai-tier-title-${t.id}`);
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
            return currentAiTiers.find(t => t.id === selected.value);
        }
        async function installSelectedAiTier() {
            const tier = getSelectedAiTier();
            if (!tier) return alert('No tier selected');
            for (const model of tier.models) {
                try {
                    const res = await fetch('/api/ai/pull', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ model: model })
                    });
                    const data = await res.json();
                    if (data.status === 'success') {
                    } else {
                        alert(`Error pulling ${model}: ${data.message}`);
                    }
                } catch (e) {
                    alert(`Network error pulling ${model}`);
                }
            }
        }
        async function updateSelectedAiTier() {
            await installSelectedAiTier();
        }
        async function purgeSelectedAiTier() {
            const tier = getSelectedAiTier();
            if (!tier) return alert('No tier selected');
            if (!confirm(`Are you sure you want to purge all models in ${tier.name}?`)) return;
            for (const model of tier.models) {
                const installedMatch = installedAiModels.find(im => im.startsWith(model) || model.startsWith(im.split(':')[0]));
                const modelToRemove = installedMatch || model;
                try {
                    const res = await fetch('/api/ai/remove', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ model: modelToRemove })
                    });
                    const data = await res.json();
                    if (data.status !== 'success' && !data.message && data.message.indexOf("not found") === -1) {
                        console.error(`Error removing ${modelToRemove}: ${data.message}`);
                    }
                } catch (e) {
                    console.error(`Network error removing ${modelToRemove}`);
                }
            }
            alert(`Purge completed for ${tier.name}.`);
            await refreshAiPackageManager();
        }
        function typeWriter(element, text, i) {
            if (i < text.length) {
                let chunkSize = text.length > 5000 ? 50 : (text.length > 1000 ? 15 : 1);
                element.textContent += text.substring(i, i + chunkSize);
                element.scrollTop = element.scrollHeight;
                let timeout = setTimeout(() => typeWriter(element, text, i + chunkSize), 2);
                if (!element.typewriterTimeouts) element.typewriterTimeouts = [];
                element.typewriterTimeouts.push(timeout);
            } else if (element.typewriterTimeouts) {
                element.typewriterTimeouts.forEach(t => clearTimeout(t));
                element.typewriterTimeouts = [];
            }
        }
        
        function handleTaskResponse(data, contentDiv, statusDiv, win) {
            if (data.status === 'pending') {
                if (win) win._taskId = data.task_id;
                const checkStatus = setInterval(async () => {
                    try {
                        const res = await fetch(`/api/task_status?task_id=${data.task_id}`);
                        const statusData = await res.json();
                        if (statusData.status === 'success' || statusData.status === 'error') {
                            clearInterval(checkStatus);
                            updateStats();
                            if (contentDiv) {
                                contentDiv.innerHTML = ""; 
                                if (statusData.type === 'html') {
                                    contentDiv.innerHTML = statusData.output || statusData.message;
                                } else {
                                    typeWriter(contentDiv, statusData.output || statusData.message, 0);
                                }
                                if (win && statusData.status === 'success') {
                                    parseScanOutput(win._scanTool, win._scanTarget, statusData.output);
                                }
                            }
                            if (statusDiv) {
                                statusDiv.innerText = t('operation_complete');
                                statusDiv.style.color = "var(--highlight-color)";
                                statusDiv.style.borderColor = "var(--highlight-color)";
                            }
                        }
                    } catch (err) {
                        console.error(err);
                    }
                }, 1000);
            } else {
                updateStats();
                if (contentDiv) {
                    contentDiv.innerHTML = ""; 
                    if (data.type === 'html') {
                        contentDiv.innerHTML = data.output || data.message;
                    } else {
                        typeWriter(contentDiv, data.output || data.message, 0);
                    }
                    if (win && data.status === 'success') {
                        parseScanOutput(win._scanTool, win._scanTarget, data.output);
                    }
                }
                if (statusDiv) {
                    statusDiv.innerText = t('operation_complete');
                    statusDiv.style.color = "var(--highlight-color)";
                    statusDiv.style.borderColor = "var(--highlight-color)";
                }
            }
        }

        function createTerminalWindow(title, toolName, target) {
            const outputArea = document.getElementById('output-area');
            const win = document.createElement('div');
            win.className = 'terminal-window';
            win._scanTool = toolName || '';
            win._scanTarget = target || '';
            if (title.toUpperCase().includes('INSTALLING') || title.toUpperCase().includes('UPDATING') || title.toUpperCase().includes('REMOVING')) {
                win.classList.add('terminal-install');
            }
            const header = document.createElement('div');
            header.className = 'terminal-header';
            const titleSpan = document.createElement('span');
            titleSpan.className = 'terminal-title';
            titleSpan.innerText = title;
            const actions = document.createElement('div');
            actions.className = 'terminal-actions';
            const copyBtn = document.createElement('button');
            copyBtn.className = 'btn-mini';
            copyBtn.innerText = 'COPY';
            copyBtn.onclick = () => {
                navigator.clipboard.writeText(content.innerText);
                copyBtn.innerText = 'COPIED!';
                setTimeout(() => copyBtn.innerText = 'COPY', 2000);
            };
            const aiBtn = document.createElement('button');
            aiBtn.className = 'btn-mini';
            aiBtn.style.color = '#ebcb8b';
            aiBtn.style.borderColor = 'rgba(235, 203, 139, 0.4)';
            aiBtn.innerText = '🧠 AI';
            aiBtn.title = 'Analyze with Heimdall AI';
            aiBtn.onclick = () => {
                const scanOutput = content.innerText;
                if (!scanOutput || !scanOutput.trim()) return;
                aiBtn.innerText = '...';
                aiBtn.disabled = true;
                analyzeTerminalContent(content, scanOutput, win._scanTool || 'unknown', win._scanTarget || '');
                aiBtn.innerText = '🧠 AI';
                aiBtn.disabled = false;
            };
            const closeBtn = document.createElement('button');
            closeBtn.className = 'btn-mini terminal-close-btn';
            closeBtn.innerText = 'X';
            closeBtn.onclick = () => {
                if (content.typewriterTimeouts) {
                    content.typewriterTimeouts.forEach(t => clearTimeout(t));
                }
                if (win._taskId) {
                    const fd = new FormData();
                    fd.append('task_id', win._taskId);
                    fetch('/api/task_kill', { method: 'POST', body: fd }).catch(e=>console.error(e));
                }
                win.remove();
            };
            actions.appendChild(aiBtn);
            actions.appendChild(copyBtn);
            actions.appendChild(closeBtn);
            header.appendChild(titleSpan);
            header.appendChild(actions);
            const content = document.createElement('div');
            content.className = 'terminal-content';
            content.typewriterTimeouts = [];
            win.appendChild(header);
            win.appendChild(content);
            
            if (toolName === 'odin_ai') {
                const promptContainer = document.createElement('div');
                promptContainer.className = 'terminal-input-container';
                promptContainer.style.cssText = 'display:flex; align-items:center; gap:5px; margin:10px 15px; border-top:1px solid rgba(235,203,139,0.2); padding-top:10px;';
                
                const arrow = document.createElement('span');
                arrow.style.cssText = 'color:#ebcb8b; font-family:monospace; font-weight:bold; font-size:14px;';
                arrow.innerText = '>';
                
                const input = document.createElement('input');
                input.type = 'text';
                input.placeholder = 'Chant a query to Odin... (Press Enter)';
                input.style.cssText = 'background:transparent; border:none; outline:none; color:var(--text-color); font-family:monospace; flex:1; padding:0; margin:0; font-size:13px;';
                
                promptContainer.appendChild(arrow);
                promptContainer.appendChild(input);
                win.appendChild(promptContainer);
                
                input.addEventListener('keypress', async (e) => {
                    if (e.key === 'Enter') {
                        const val = input.value.trim();
                        if (!val) return;
                        input.value = '';
                        input.disabled = true;
                        
                        const userDiv = document.createElement('div');
                        userDiv.style.cssText = 'margin-top: 8px; margin-bottom: 8px; font-family: monospace; font-size:13px;';
                        userDiv.innerHTML = `<span style="color:#88c0d0; font-weight:bold;">[USER]:</span> ${escapeHtml(val)}`;
                        content.appendChild(userDiv);
                        content.scrollTop = content.scrollHeight;
                        
                        const thinkingDiv = document.createElement('div');
                        thinkingDiv.style.cssText = 'color:#ebcb8b; font-style:italic; font-size:12px; margin-bottom:8px; font-family: monospace;';
                        thinkingDiv.innerText = 'ᛟ Odin is thinking...';
                        content.appendChild(thinkingDiv);
                        content.scrollTop = content.scrollHeight;
                        
                        odinMessages.push({role: 'user', content: val});
                        
                        try {
                            if (!odinCurrentModel) {
                                const statusRes = await fetch('/api/ai/status');
                                const statusData = await statusRes.json();
                                if (statusData.status === 'success' && statusData.models && statusData.models.length > 0) {
                                    odinCurrentModel = statusData.models[0].name;
                                }
                            }
                            
                            const res = await fetch('/api/ai/chat', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    model: odinCurrentModel || 'qwen2.5-coder:7b',
                                    messages: odinMessages
                                })
                            });
                            const data = await res.json();
                            thinkingDiv.remove();
                            
                            const odinResponseDiv = document.createElement('div');
                            odinResponseDiv.style.cssText = 'margin-bottom: 12px; font-family: monospace; font-size:13px;';
                            const prefix = document.createElement('span');
                            prefix.style.cssText = 'color:#ebcb8b; font-weight:bold; margin-right:5px;';
                            prefix.innerText = '[ODIN]:';
                            odinResponseDiv.appendChild(prefix);
                            
                            const textSpan = document.createElement('span');
                            odinResponseDiv.appendChild(textSpan);
                            content.appendChild(odinResponseDiv);
                            
                            if (data.status === 'success') {
                                odinMessages.push({role: 'assistant', content: data.response});
                                typeWriter(textSpan, data.response, 0);
                            } else {
                                textSpan.style.color = 'var(--danger-color)';
                                textSpan.innerText = 'Error: ' + (data.message || 'Ollama offline');
                            }
                        } catch (err) {
                            if (thinkingDiv.parentNode) thinkingDiv.remove();
                            const errDiv = document.createElement('div');
                            errDiv.style.color = 'var(--danger-color)';
                            errDiv.style.fontFamily = 'monospace';
                            errDiv.innerText = 'System Error: ' + err.message;
                            content.appendChild(errDiv);
                        }
                        
                        input.disabled = false;
                        input.focus();
                        setTimeout(() => { content.scrollTop = content.scrollHeight; }, 100);
                    }
                });
            }
            
            outputArea.insertBefore(win, outputArea.firstChild);
            return content;
        }
        function openHydraModal() {
            document.getElementById('hydraModal').style.display = 'block';
        }
        function closeHydraModal() {
            document.getElementById('hydraModal').style.display = 'none';
        }
        function toggleHydraUserMode() {
            const mode = document.getElementById('hydraUserMode').value;
            const input = document.getElementById('hydraUserVal');
            if (mode === 'list') {
                input.placeholder = '/path/to/users.txt';
                input.value = '/usr/share/wordlists/fasttrack.txt';
            } else {
                input.placeholder = 'admin';
                input.value = 'admin';
            }
        }
        function toggleHydraPassMode() {
            const mode = document.getElementById('hydraPassMode').value;
            const input = document.getElementById('hydraPassVal');
            if (mode === 'list') {
                input.placeholder = '/path/to/passwords.txt';
                input.value = '/usr/share/wordlists/rockyou.txt';
            } else {
                input.placeholder = 'password123';
                input.value = 'password123';
            }
        }
        async function submitHydraScan() {
            const target = document.getElementById('target-input').value;
            if (!target) {
                alert(t('err_target'));
                return;
            }
            closeHydraModal();
            const statusDiv = document.getElementById('status-display');
            statusDiv.innerText = ">> WEAVING FATE WITH HYDRA...";
            statusDiv.style.color = "var(--wood-light)";
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
            const contentDiv = createTerminalWindow(`[ HYDRA - ${target} ]`, 'hydra', target);
            contentDiv.innerHTML = "<span style='color: var(--highlight-color);'>[ INITIATING BRUTE FORCE RITUAL... ]</span>";
            try {
                const response = await fetch('/api/action', { method: 'POST', body: formData });
                const data = await response.json();
                contentDiv.innerHTML = "";
                contentDiv.innerHTML = highlightSafe(data.output);
                updateStats();
            } catch (error) {
                contentDiv.innerHTML = `<span style="color:var(--danger-color);">RUNTIME ERROR: ${escapeHtml(String(error))}</span>`;
            }
        }
        function openSubfinderModal() { document.getElementById('subfinderModal').style.display = 'block'; }
        function closeSubfinderModal() { document.getElementById('subfinderModal').style.display = 'none'; }
        async function submitSubfinderScan() {
            const target = document.getElementById('target-input').value;
            if (!target) { alert(t('err_target')); return; }
            closeSubfinderModal();
            const threads = document.getElementById('subfinderThreads').value;
            const all_sources = document.getElementById('subfinderAll').checked ? 'true' : 'false';
            const formData = new FormData();
            formData.append('target', target);
            formData.append('action', 'subfinder');
            formData.append('threads', threads);
            formData.append('all_sources', all_sources);
            runCustomHandler('subfinder', formData, `[ SUBFINDER - ${target} ]`);
        }
        function openKnockpyModal() { document.getElementById('knockpyModal').style.display = 'block'; }
        function closeKnockpyModal() { document.getElementById('knockpyModal').style.display = 'none'; }
        async function submitKnockpyScan() {
            const target = document.getElementById('target-input').value;
            if (!target) { alert(t('err_target')); return; }
            closeKnockpyModal();
            const threads = document.getElementById('knockpyThreads').value;
            const wordlist = document.getElementById('knockpyWordlist').value;
            const formData = new FormData();
            formData.append('target', target);
            formData.append('action', 'knockpy');
            formData.append('threads', threads);
            formData.append('wordlist', wordlist);
            runCustomHandler('knockpy', formData, `[ KNOCKPY - ${target} ]`);
        }
        function openGobusterDnsModal() { document.getElementById('gobusterDnsModal').style.display = 'block'; }
        function closeGobusterDnsModal() { document.getElementById('gobusterDnsModal').style.display = 'none'; }
        async function submitGobusterDnsScan() {
            const target = document.getElementById('target-input').value;
            if (!target) { alert(t('err_target')); return; }
            closeGobusterDnsModal();
            const threads = document.getElementById('gobusterThreads').value;
            const wordlist = document.getElementById('gobusterWordlist').value;
            const formData = new FormData();
            formData.append('target', target);
            formData.append('tool', 'gobuster_dns');
            formData.append('action', 'run');
            formData.append('threads', threads);
            formData.append('wordlist', wordlist);
            runCustomHandler('gobuster_dns', formData, `[ GOBUSTER DNS - ${target} ]`);
        }
        function openMuninnModal() { document.getElementById('muninnScannerModal').style.display = 'block'; }
        function closeMuninnModal() { document.getElementById('muninnScannerModal').style.display = 'none'; }
        async function submitMuninnScan() {
            const target = document.getElementById('target-input').value;
            if (!target) { alert(t('err_target')); return; }
            closeMuninnModal();
            const formData = new FormData();
            formData.append('target', target);
            formData.append('tool', 'muninn_scanner');
            formData.append('action', 'run');
            if (document.getElementById('muninnOptAll').checked) formData.append('all', 'true');
            if (document.getElementById('muninnOptNuclei').checked) formData.append('nuclei', 'true');
            if (document.getElementById('muninnOptNmap').checked) formData.append('nmap', 'true');
            if (document.getElementById('muninnOptMonitor').checked) formData.append('monitor', 'true');
            runCustomHandler('muninn_scan', formData, `[ MUNINN SCAN - ${target} ]`);
        }
        async function runCustomHandler(action, formData, title) {
            const target = document.getElementById('target-input').value;
            window._lastScanRequest = { tool: action, target: target };
            const statusDiv = document.getElementById('status-display');
            statusDiv.innerText = `>> WEAVING FATE WITH ${action.toUpperCase()}...`;
            statusDiv.style.color = "var(--wood-light)";
            const contentDiv = createTerminalWindow(title, action, target);
            contentDiv.innerHTML = "<span style='color: var(--highlight-color);'>[ INITIATING RITUAL... ]</span>";
            try {
                const response = await fetch('/api/action', { method: 'POST', body: formData });
                const data = await response.json();
                contentDiv.innerHTML = "";
                contentDiv.innerHTML = highlightSafe(data.output);
                updateStats();
            } catch (error) {
                contentDiv.innerHTML = `<span style="color:var(--danger-color);">RUNTIME ERROR: ${escapeHtml(String(error))}</span>`;
            }
        }
        async function runTool(toolName) {
            const target = document.getElementById('target-input').value;
            window._lastScanRequest = { tool: toolName, target: target };
            const statusDiv = document.getElementById('status-display');
            const toolInfo = window.toolsConfig[toolName];
            if (toolInfo && toolInfo.requires_target && !target) {
                statusDiv.innerText = t('err_target');
                statusDiv.style.color = "var(--danger-color)";
                statusDiv.style.borderColor = "var(--danger-color)";
                return;
            }
            statusDiv.style.color = "var(--wood-light)";
            statusDiv.style.borderColor = "var(--wood-light)";
            currentTool = toolName;
            statusDiv.innerText = t('consulting_roots', {tool: toolInfo ? toolInfo.name.toUpperCase() : toolName.toUpperCase()});
            const formData = new FormData();
            formData.append('tool', toolName);
            formData.append('target', target);
            formData.append('action', 'check');
            try {
                const response = await fetch('/api/action', { method: 'POST', body: formData });
                const data = await response.json();
                if (data.status === 'missing') {
                    showInstallModal(toolName);
                } else {
                    executeTool(toolName, target);
                }
            } catch (error) {
                statusDiv.innerText = "SYSTEM ERROR: " + error;
                statusDiv.style.color = "var(--danger-color)";
            }
        }
        let updateContentDiv = null;
        async function initiateUpdateCheck() {
            const statusDiv = document.getElementById('status-display');
            statusDiv.innerText = ">> CONSULTING THE ARCHIVES FOR KNOWLEDGE (CHECKING UPDATES)...";
            statusDiv.style.color = "var(--wood-light)";
            updateContentDiv = createTerminalWindow("[ SYSTEM OPERATIONS - RUNE SYNC ]");
            updateContentDiv.innerHTML = "<span style='color: var(--highlight-color);'>[ SCANNING GITHUB REPOSITORIES... ]</span>";
            const formData = new FormData();
            formData.append('action', 'check_updates');
            try {
                const response = await fetch('/api/action', { method: 'POST', body: formData });
                const data = await response.json();
                if (data.updates && data.updates.length > 0) {
                    let html = `<div style="color: var(--wood-light); margin-bottom: 20px; font-family: monospace;">
                        <h3>[ ᛊ ] NEW KNOWLEDGE DISCOVERED</h3>
                        <p>The following Runes have updates available from their source:</p>
                        <ul style="color: var(--highlight-color);">`;
                    data.updates.forEach(u => html += `<li>${escapeHtml(u)}</li>`);
                    html += `</ul>
                        <p>Do you wish to integrate these updates into the framework?</p>
                        <button onclick="applyUpdates()" class="btn-install" style="margin-right: 10px; width: auto; padding: 10px 20px;">YES, INTEGRATE UPDATES</button>
                        <button onclick="cancelUpdates()" class="btn-cancel" style="width: auto; padding: 10px 20px;">NO, KEEP CURRENT</button>
                    </div>`;
                    updateContentDiv.innerHTML = html;
                    statusDiv.innerText = ">> AWAITING YOUR COMMAND.";
                } else {
                    updateContentDiv.innerHTML = "<span style='color: #a3be8c;'>[ ALL RUNES ARE CURRENTLY UP TO DATE. THE ROOTS ARE UNTOUCHED. ]</span>";
                    statusDiv.innerText = ">> THE ARCHIVES ARE SYNCED.";
                }
            } catch (error) {
                if(updateContentDiv) updateContentDiv.innerText = "RUNTIME ERROR: " + error;
                statusDiv.innerText = t('chant_failed');
                statusDiv.style.color = "var(--danger-color)";
            }
        }
        function cancelUpdates() {
            if(updateContentDiv) {
                updateContentDiv.innerHTML = "<span style='color: #a3be8c;'>[ UPDATE " + t("cancel") + "LED. THE ROOTS REMAIN UNTOUCHED. ]</span>";
            }
            document.getElementById('status-display').innerText = ">> OPERATION " + t("abort") + "ED.";
        }
        async function applyUpdates() {
            const statusDiv = document.getElementById('status-display');
            statusDiv.innerText = ">> WEAVING NEW FATE (APPLYING UPDATES & RECOMPILING)...";
            if(updateContentDiv) {
                updateContentDiv.innerHTML = "<span style='color: var(--highlight-color);'>[ DOWNLOADING AND INTEGRATING... ]</span>";
            }
            const formData = new FormData();
            formData.append('action', 'apply_updates');
            try {
                const response = await fetch('/api/action', { method: 'POST', body: formData });
                const data = await response.json();
                if(updateContentDiv) {
                    updateContentDiv.innerHTML = data.output;
                }
                statusDiv.innerText = ">> FATE HAS BEEN WOVEN. UPDATES INTEGRATED.";
                statusDiv.style.color = "var(--highlight-color)";
            } catch (error) {
                if(updateContentDiv) updateContentDiv.innerText = "RUNTIME ERROR: " + error;
                statusDiv.innerText = t('chant_failed');
                statusDiv.style.color = "var(--danger-color)";
            }
        }
        function showInstallModal(toolName) {
            const toolInfo = window.toolsConfig[toolName];
            const displayName = toolInfo ? toolInfo.name : toolName;
            document.getElementById('installMsg').innerText = `The tool '${displayName.toUpperCase()}' is not present.\n\nDo you wish to summon it now?`;
            document.getElementById('installModal').style.display = 'block';
        }
        function closeModal() {
            document.getElementById('installModal').style.display = 'none';
            document.getElementById('status-display').innerText = ">> RITUAL " + t("abort") + "ED.";
        }
        async function confirmInstall() {
            closeModal();
            const statusDiv = document.getElementById('status-display');
            const toolInfo = window.toolsConfig[currentTool];
            const displayName = toolInfo ? toolInfo.name : currentTool;
            statusDiv.innerText = `>> SUMMONING ${displayName.toUpperCase()}... PLEASE WAIT...`;
            const formData = new FormData();
            formData.append('tool', currentTool);
            formData.append('action', 'install');
            try {
                const response = await fetch('/api/action', { method: 'POST', body: formData });
                const data = await response.json();
                if (data.status === 'success') {
                    statusDiv.innerText = ">> SUMMONING COMPLETE. ENGAGING TOOL...";
                    const target = document.getElementById('target-input').value;
                    executeTool(currentTool, target);
                } else {
                    statusDiv.innerText = ">> SUMMONING FAILED: " + data.message;
                    statusDiv.style.color = "var(--danger-color)";
                }
            } catch (error) {
                statusDiv.innerText = "INSTALLATION ERROR: " + error;
            }
        }
        async function executeTool(tool, target) {
            const statusDiv = document.getElementById('status-display');
            const toolInfo = window.toolsConfig[tool];
            const displayName = toolInfo ? toolInfo.name : tool;
            statusDiv.innerText = `>> WEAVING FATE WITH ${displayName.toUpperCase()} ON [${target || 'NO TARGET'}]...`;
            const contentDiv = createTerminalWindow(`[ ${displayName.toUpperCase()} - ${target || 'SYSTEM'} ]`, tool, target || '');
            const win = contentDiv.parentNode.parentNode; // get the terminal window element
            contentDiv.innerHTML = "<span style='color: var(--highlight-color);'>[ CONNECTING TO THE WORLD TREE... ]</span>";
            const formData = new FormData();
            formData.append('tool', tool);
            formData.append('target', target);
            formData.append('action', 'run');
            try {
                const response = await fetch('/api/action', { method: 'POST', body: formData });
                const data = await response.json();
                
                if (data.status === 'pending') {
                    win._taskId = data.task_id;
                    const checkStatus = setInterval(async () => {
                        try {
                            const res = await fetch(`/api/task_status?task_id=${data.task_id}`);
                            const statusData = await res.json();
                            if (statusData.status === 'success' || statusData.status === 'error') {
                                clearInterval(checkStatus);
                                updateStats();
                                contentDiv.innerHTML = ""; 
                                if (statusData.type === 'html') {
                                    contentDiv.innerHTML = statusData.output || statusData.message;
                                } else {
                                    typeWriter(contentDiv, statusData.output || statusData.message, 0);
                                }
                                statusDiv.innerText = t('operation_complete');
                                statusDiv.style.color = "var(--highlight-color)";
                                statusDiv.style.borderColor = "var(--highlight-color)";
                            }
                        } catch (err) {
                            console.error(err);
                        }
                    }, 1000);
                } else {
                    updateStats();
                    contentDiv.innerHTML = ""; 
                    if (data.type === 'html') {
                        contentDiv.innerHTML = data.output || data.message;
                    } else {
                        typeWriter(contentDiv, data.output || data.message, 0);
                    }
                    statusDiv.innerText = t('operation_complete');
                    statusDiv.style.color = "var(--highlight-color)";
                    statusDiv.style.borderColor = "var(--highlight-color)";
                }
            } catch (error) {
                contentDiv.innerText = t('runtime_error') + String(error);
                statusDiv.innerText = t('chant_failed');
                statusDiv.style.color = "var(--danger-color)";
            }
        }
        function downloadArtifact(type) {
            const content = document.getElementById('output-area').innerText;
            const target = document.getElementById('target-input').value || 'unknown_target';
            const tool = currentTool || 'tool';
            const timestamp = new Date().toISOString().slice(0,10);
            let filename = `yggdrasil_${target}_${tool}_${timestamp}.${type}`;
            let blob;
            if (type === 'json') {
                const data = { target: target, tool: tool, date: timestamp, log: content };
                blob = new Blob([JSON.stringify(data, null, 4)], { type: "application/json" });
            } else {
                blob = new Blob([content], { type: "text/plain" });
            }
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            link.click();
        }
        function openSynModal() {
            document.getElementById('synScannerModal').style.display = 'block';
            const target = document.getElementById('target-input').value;
            if (target) {
                document.getElementById('synAutoTarget').value = target;
                document.getElementById('synManTarget').value = target;
            }
        }
        function closeSynModal() {
            document.getElementById('synScannerModal').style.display = 'none';
        }
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
            let target = "";
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
            const outputDiv = document.getElementById('output-area');
            if (!target) {
                statusDiv.innerText = t('err_target');
                statusDiv.style.color = "var(--danger-color)";
                statusDiv.style.borderColor = "var(--danger-color)";
                return;
            }
            currentTool = 'adv_syn_scan';
            statusDiv.style.color = "var(--wood-light)";
            statusDiv.style.borderColor = "var(--wood-light)";
            statusDiv.innerText = t('weaving_syn', {target: target});
            window._lastScanRequest = { tool: 'adv_syn_scan', target: target };
            const contentDiv = createTerminalWindow(`[ ADVANCED SYN SCAN - ${target} ]`, 'adv_syn_scan', target);
            contentDiv.innerHTML = "<span style='color: var(--highlight-color);'>[ CONNECTING TO THE WORLD TREE... ]</span>";
            fetch('/api/action', { method: 'POST', body: formData })
                .then(r => r.json())
                .then(data => {
                    const win = contentDiv ? contentDiv.parentNode.parentNode : null;
                    handleTaskResponse(data, contentDiv, statusDiv, win);
                })
                .catch(error => {
                    contentDiv.innerText = t('runtime_error') + error;
                    statusDiv.innerText = t('chant_failed');
                    statusDiv.style.color = "var(--danger-color)";
                    statusDiv.style.borderColor = "var(--danger-color)";
                });
        }
        function openErebusModal() {
            document.getElementById('erebusScannerModal').style.display = 'block';
            const target = document.getElementById('target-input').value;
            if (target) {
                document.getElementById('erebusTarget').value = target;
            }
        }
        function closeErebusModal() {
            document.getElementById('erebusScannerModal').style.display = 'none';
        }
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
                statusDiv.innerText = t('err_target_erebus');
                statusDiv.style.color = "var(--danger-color)";
                statusDiv.style.borderColor = "var(--danger-color)";
                return;
            }
            const formData = new FormData();
            formData.append('tool', 'erebus');
            formData.append('action', 'run');
            formData.append('target', target);
            formData.append('ports', ports);
            if (proxy && proxy.trim()) {
                formData.append('proxy', proxy.trim());
            }
            formData.append('banner', banner ? 'true' : 'false');
            formData.append('randomize', randomize ? 'true' : 'false');
            formData.append('adaptive', adaptive ? 'true' : 'false');
            currentTool = 'erebus';
            statusDiv.style.color = "var(--wood-light)";
            statusDiv.style.borderColor = "var(--wood-light)";
            statusDiv.innerText = t('weaving_erebus', {target: target});
            window._lastScanRequest = { tool: 'erebus', target: target };
            const contentDiv = createTerminalWindow(`[ EREBUS SCANNER - ${target} ]`, 'erebus', target);
            contentDiv.innerHTML = "<span style='color: var(--highlight-color);'>[ CONNECTING TO THE WORLD TREE / CARGO RUNNING... ]</span>";
            fetch('/api/action', { method: 'POST', body: formData })
                .then(r => r.json())
                .then(data => {
                    const win = contentDiv ? contentDiv.parentNode.parentNode : null;
                    handleTaskResponse(data, contentDiv, statusDiv, win);
                })
                .catch(error => {
                    contentDiv.innerText = t('runtime_error') + error;
                    statusDiv.innerText = t('chant_failed');
                    statusDiv.style.color = "var(--danger-color)";
                    statusDiv.style.borderColor = "var(--danger-color)";
                });
        }
        function openPacketInjectorModal() {
            document.getElementById('packetInjectorModal').style.display = 'block';
            const target = document.getElementById('target-input').value;
            if (target) {
                document.getElementById('injectorTarget').value = target;
            }
        }
        function closePacketInjectorModal() {
            document.getElementById('packetInjectorModal').style.display = 'none';
        }
        function toggleInjectorFields() {
            const action = document.getElementById('injectorAction').value;
            const injectFields = document.getElementById('injectorInjectFields');
            if (action === 'inject') {
                injectFields.style.display = 'block';
                toggleInjectorProtocolFields();
            } else {
                injectFields.style.display = 'none';
            }
        }
        function toggleInjectorProtocolFields() {
            const protocol = document.getElementById('injectorProtocol').value;
            const tcpFields = document.getElementById('injectorTcpFields');
            const arpFields = document.getElementById('injectorArpFields');
            if (protocol === 'tcp') {
                tcpFields.style.display = 'block';
                arpFields.style.display = 'none';
            } else if (protocol === 'arp') {
                tcpFields.style.display = 'none';
                arpFields.style.display = 'block';
            }
        }
        function submitPacketInjector() {
            closePacketInjectorModal();
            const action = document.getElementById('injectorAction').value;
            const interface = document.getElementById('injectorInterface').value || 'eth0';
            const target = document.getElementById('injectorTarget').value;
            const formData = new FormData();
            formData.append('tool', 'packet_injector');
            formData.append('action', 'run');
            formData.append('packet_action', action);
            formData.append('interface', interface);
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
            } else {
                formData.append('target', target || 'none');
            }
            const statusDiv = document.getElementById('status-display');
            if (action === 'inject' && !target) {
                statusDiv.innerText = t('err_target_injection');
                statusDiv.style.color = "var(--danger-color)";
                statusDiv.style.borderColor = "var(--danger-color)";
                return;
            }
            currentTool = 'packet_injector';
            statusDiv.style.color = "var(--wood-light)";
            statusDiv.style.borderColor = "var(--wood-light)";
            statusDiv.innerText = t('initiating_injector', {action: action.toUpperCase(), interface: interface});
            window._lastScanRequest = { tool: 'packet_injector', target: target };
            const contentDiv = createTerminalWindow(`[ PACKET INJECTOR - ${action.toUpperCase()} ]`, 'packet_injector', target || '');
            contentDiv.innerHTML = "<span style='color: var(--highlight-color);'>[ ENGAGING PACKET CRAFTING ENGINE... ]</span>";
            fetch('/api/action', { method: 'POST', body: formData })
                .then(r => r.json())
                .then(data => {
                    const win = contentDiv ? contentDiv.parentNode.parentNode : null;
                    handleTaskResponse(data, contentDiv, statusDiv, win);
                })
                .catch(error => {
                    contentDiv.innerText = t('runtime_error') + error;
                    statusDiv.innerText = t('crafting_failed');
                    statusDiv.style.color = "var(--danger-color)";
                    statusDiv.style.borderColor = "var(--danger-color)";
                });
        }
        function openFenrirModal() {
            document.getElementById('fenrirModal').style.display = 'block';
            const target = document.getElementById('target-input').value;
            if (target) {
                document.getElementById('fenrirTarget').value = target;
            }
        }
        function closeFenrirModal() {
            document.getElementById('fenrirModal').style.display = 'none';
        }
        function submitFenrirScan() {
            closeFenrirModal();
            const target = document.getElementById('fenrirTarget').value;
            const hashMode = document.getElementById('fenrirHashMode').value;
            const attackMode = document.getElementById('fenrirAttackMode').value;
            const wordlist = document.getElementById('fenrirWordlist').value;
            if (!target) {
                const statusDiv = document.getElementById('status-display');
                statusDiv.innerText = t('err_target_req');
                statusDiv.style.color = "var(--danger-color)";
                return;
            }
            if (isProcessRunning) {
                alert(t('err_process_run'));
                return;
            }
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
            statusDiv.innerText = `>> AWAKENING FENRIR ON [ ${escapeHtml(target)} ]...`;
            window._lastScanRequest = { tool: 'fenrir', target: target };
            const contentDiv = createTerminalWindow(`[ ᚹ FENRIR - ${escapeHtml(hashMode.toUpperCase())} - ${escapeHtml(target)} ]`, 'fenrir', target);
            fetch('/api/action', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                isProcessRunning = false;
                if (data.status === 'success') {
                    contentDiv.innerHTML = `<pre>${escapeHtml(data.output)}</pre>`;
                    statusDiv.innerText = t('fate_woven');
                } else {
                    contentDiv.innerHTML = `<pre style="color:var(--danger-color);">${escapeHtml(data.message)}</pre>`;
                    statusDiv.innerText = t('err_execute');
                }
            })
            .catch(error => {
                isProcessRunning = false;
                console.error('Error:', error);
                statusDiv.innerText = t('err_network');
            });
        }
        async function openWslSettings() {
            document.getElementById('wslSettingsModal').style.display = 'block';
            const select = document.getElementById('wslDistroSelect');
            select.innerHTML = '<option value="">Loading...</option>';
            try {
                const res = await fetch('/api/wsl/distros');
                const data = await res.json();
                select.innerHTML = '<option value="">-- Auto-Detect / Default --</option>';
                data.distros.forEach(distro => {
                    const opt = document.createElement('option');
                    opt.value = distro;
                    opt.textContent = distro;
                    if (data.preferred === distro) {
                        opt.selected = true;
                    }
                    select.appendChild(opt);
                });
            } catch (err) {
                select.innerHTML = '<option value="">Failed to load distros</option>';
            }
        }
        function closeWslSettings() {
            document.getElementById('wslSettingsModal').style.display = 'none';
        }
        async function saveWslSettings() {
            const select = document.getElementById('wslDistroSelect');
            const distro = select.value;
            try {
                const res = await fetch('/api/wsl/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ distro: distro })
                });
                const data = await res.json();
                const statusDiv = document.getElementById('status-display');
                if(data.status === 'success') {
                    statusDiv.innerText = 'WSL configuration updated successfully.';
                } else {
                    statusDiv.innerText = 'Failed to update WSL configuration: ' + data.message;
                }
            } catch (err) {
                document.getElementById('status-display').innerText = 'Error saving WSL configuration.';
            }
            closeWslSettings();
        }
        let odinMessages = [];
        let odinCurrentModel = '';
        async function openOdinChat() {
            document.getElementById('odinChatModal').style.display = 'block';
            document.getElementById('odinChatInput').focus();
            await refreshOdinModels();
            loadOdinTierInfo();
        }
        function closeOdinChat() {
            document.getElementById('odinChatModal').style.display = 'none';
        }
        async function refreshOdinModels() {
            const select = document.getElementById('odinModelSelect');
            const status = document.getElementById('odinStatus');
            select.innerHTML = '<option value="">-- Checking Ollama... --</option>';
            try {
                const res = await fetch('/api/ai/status');
                const data = await res.json();
                if (data.status === 'success') {
                    status.innerText = '● ONLINE';
                    status.style.color = '#a3be8c';
                    select.innerHTML = '';
                    if (data.models && data.models.length > 0) {
                        data.models.forEach(m => {
                            const opt = document.createElement('option');
                            opt.value = m.name;
                            opt.textContent = m.name;
                            if (m.name === odinCurrentModel) opt.selected = true;
                            select.appendChild(opt);
                        });
                        if (!odinCurrentModel || !data.models.find(m => m.name === odinCurrentModel)) {
                            odinCurrentModel = data.models[0].name;
                            select.value = odinCurrentModel;
                        }
                    } else {
                        select.innerHTML = '<option value="">-- No models installed --</option>';
                    }
                } else {
                    status.innerText = '● OFFLINE';
                    status.style.color = 'var(--danger-color)';
                    select.innerHTML = '<option value="">-- Ollama not running --</option>';
                }
            } catch (err) {
                status.innerText = '● OFFLINE';
                status.style.color = 'var(--danger-color)';
                select.innerHTML = '<option value="">-- Connection error --</option>';
            }
        }
        function onOdinModelChange() {
            odinCurrentModel = document.getElementById('odinModelSelect').value;
        }
        function handleOdinKeypress(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                sendOdinMessage();
            }
        }
        async function sendOdinMessage() {
            const input = document.getElementById('odinChatInput');
            const sendBtn = document.getElementById('odinSendBtn');
            const userMessage = input.value.trim();
            if (!userMessage) return;
            if (!odinCurrentModel) {
                addOdinMessage('system', 'No AI model selected. Please install a model first (use PULL button).');
                return;
            }
            addOdinMessage('user', userMessage);
            odinMessages.push({ role: 'user', content: userMessage });
            input.value = '';
            input.disabled = true;
            sendBtn.disabled = true;
            sendBtn.innerText = '...';
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
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        model: odinCurrentModel,
                        messages: odinMessages
                    })
                });
                const data = await res.json();
                const thinkEl = document.getElementById(thinkingId);
                if (thinkEl) thinkEl.remove();
                if (data.status === 'success') {
                    addOdinMessage('assistant', data.response);
                    odinMessages.push({ role: 'assistant', content: data.response });
                } else {
                    addOdinMessage('system', 'Error: ' + escapeHtml(data.message || 'Unknown error'));
                }
            } catch (err) {
                const thinkEl = document.getElementById(thinkingId);
                if (thinkEl) thinkEl.remove();
                addOdinMessage('system', 'Network error: Could not reach the server.');
            }
            input.disabled = false;
            sendBtn.disabled = false;
            sendBtn.innerText = 'SEND ᛫';
            input.focus();
        }
        function addOdinMessage(role, content) {
            const msgArea = document.getElementById('odinChatMessages');
            const div = document.createElement('div');
            div.style.cssText = 'margin-bottom: 12px; padding: 10px; border-radius: 4px; white-space: pre-wrap; word-break: break-word;';
            if (role === 'user') {
                div.style.background = 'rgba(136, 192, 208, 0.1)';
                div.style.borderLeft = '3px solid var(--highlight-color)';
                div.innerHTML = '<span style="color: var(--highlight-color); font-weight: bold;">᛫ YOU:</span>\n' + escapeHtml(content);
            } else if (role === 'assistant') {
                div.style.background = 'rgba(235, 203, 139, 0.08)';
                div.style.borderLeft = '3px solid #ebcb8b';
                div.innerHTML = '<span style="color: #ebcb8b; font-weight: bold;">ᛟ ODIN:</span>\n' + escapeHtml(content);
            } else {
                div.style.background = 'rgba(191, 97, 106, 0.1)';
                div.style.borderLeft = '3px solid var(--danger-color)';
                div.style.color = 'var(--danger-color)';
                div.innerText = '⚡ ' + content;
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
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model: modelName.trim() })
                });
                const data = await res.json();
                addOdinMessage('system', data.message || (data.status === 'success' ? 'Pull started.' : 'Pull failed.'));
            } catch (err) {
                addOdinMessage('system', 'Error starting model pull.');
            }
        }
        async function removeOdinModel() {
            if (!odinCurrentModel) {
                alert('No model selected to remove.');
                return;
            }
            if (!confirm('Remove model "' + odinCurrentModel + '"?\nThis will free disk space but the model will need to be re-downloaded to use again.')) return;
            addOdinMessage('system', 'Removing model: ' + odinCurrentModel + '...');
            try {
                const res = await fetch('/api/ai/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model: odinCurrentModel })
                });
                const data = await res.json();
                addOdinMessage('system', data.message || 'Model removed.');
                odinCurrentModel = '';
                await refreshOdinModels();
            } catch (err) {
                addOdinMessage('system', 'Error removing model.');
            }
        }
        function clearOdinChat() {
            odinMessages = [];
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
                    data.tiers.forEach(t => {
                        html += '<span style="margin: 0 10px; color: #ebcb8b;">[' + t.name.split(':')[0] + ']</span> ';
                    });
                }
                try {
                    const diskRes = await fetch('/api/ai/disk');
                    const diskData = await diskRes.json();
                    if (diskData.status === 'success') {
                        html += '<span style="margin-left: 10px; color: var(--accent-color);">| ᛚ ' + diskData.total_size_gb + ' GB used by ' + diskData.total_models + ' models</span>';
                    }
                } catch (e) {}
                html += '<span style="color: var(--text-dim); margin-left: 10px;">— Use PULL to download models</span>';
                tierDiv.innerHTML = html;
            } catch (e) {}
        }



        // --- Sidebar Layout Logic ---
        function applyLayout(layout) {
            const body = document.body;
            // Remove existing layout classes
            body.classList.remove('layout-accordion', 'layout-tabbed', 'layout-grid', 'layout-flyout');
            
            if (layout !== 'default') {
                body.classList.add('layout-' + layout);
            }
            localStorage.setItem('sidebarLayout', layout);
            document.getElementById('sidebarLayoutSelect').value = layout;
            
            // Reset active states for accordion/tabbed
            const groups = document.querySelectorAll('.tool-group');
            groups.forEach(g => g.classList.remove('active'));
            if (layout === 'accordion' || layout === 'tabbed') {
                // Open first one by default
                if(groups.length > 0) groups[0].classList.add('active');
            }
        }

        function initSidebarLayouts() {
            const savedLayout = localStorage.getItem('sidebarLayout') || 'default';
            applyLayout(savedLayout);

            // Add click listeners to headers for Accordion/Tabbed switching
            document.querySelectorAll('.sidebar h3, .my-runes-title').forEach(header => {
                header.style.cursor = 'pointer';
                header.onclick = function() {
                    const layout = localStorage.getItem('sidebarLayout') || 'default';
                    if (layout === 'accordion' || layout === 'tabbed') {
                        const parent = this.parentElement;
                        // If it's already active in accordion, toggle it off. In tabbed, keep it active.
                        if (layout === 'accordion' && parent.classList.contains('active')) {
                            parent.classList.remove('active');
                        } else {
                            // Close others
                            document.querySelectorAll('.tool-group').forEach(g => g.classList.remove('active'));
                            parent.classList.add('active');
                        }
                    }
                };
            });
        }

        function filterTools() {
            const input = document.getElementById('sidebarSearch').value.toLowerCase();
            const groups = document.querySelectorAll('.tool-group');
            
            groups.forEach(group => {
                const buttons = group.querySelectorAll('button');
                let hasVisibleButton = false;
                buttons.forEach(btn => {
                    if (btn.innerText.toLowerCase().includes(input)) {
                        btn.style.display = '';
                        hasVisibleButton = true;
                    } else {
                        btn.style.display = 'none';
                    }
                });
                // In default/grid/flyout, hide the entire group if no buttons match.
                // In accordion/tabbed, keep the headers visible but empty, or hide them? 
                // Better to just hide the group to clean up space.
                if (!hasVisibleButton && input !== '') {
                    group.style.display = 'none';
                } else {
                    group.style.display = '';
                }
            });
            // Also hide my-runes-container title if empty
            const runesContainer = document.querySelector('.my-runes-container');
            if (runesContainer) {
                const visibleButtons = Array.from(runesContainer.querySelectorAll('button')).some(b => b.style.display !== 'none');
                runesContainer.style.display = (visibleButtons || input === '') ? '' : 'none';
            }
        }
        function toggleOdinMode() {
            const body = document.body;
            const isActive = body.classList.contains('odin-mode');
            if (isActive) {
                playOdinTransition(() => {
                    body.classList.remove('odin-mode');
                    document.getElementById('odinToggleLabel').innerText = "" + t("btn_odin_mode") + "";
                    document.getElementById('odinToggleIcon').style.transform = 'scale(1)';
                    closeAiTerminals();
                });
                localStorage.setItem('odinMode', 'off');
            } else {
                playOdinTransition(() => {
                    body.classList.add('odin-mode');
                    document.getElementById('odinToggleLabel').innerText = "" + t("btn_odin_mode_exit") + "";
                    document.getElementById('odinToggleIcon').style.transform = 'scale(1.2)';
                    spawnAiTerminals();
                });
                localStorage.setItem('odinMode', 'on');
            }
        }
        function spawnAiTerminals() {
            const odinWin = createTerminalWindow("[ 👁️ ] ODIN'S EYE AI", 'odin_ai', 'SYSTEM');
            odinWin.parentNode.style.borderColor = "#ebcb8b";
            odinWin.parentNode.style.boxShadow = "0 0 15px rgba(235,203,139,0.3)";
            typeWriter(odinWin, ">> ODIN AI SYSTEM INITIALIZED...\n>> AWAITING INPUT...\n>> HINT: Use the button on the left panel to open the interactive chat modal.", 0);

            const autoWin = createTerminalWindow("[ ᛏ ] AUTONOMOUS AGENT", 'autonomous', 'SYSTEM');
            autoWin.parentNode.style.borderColor = "#bf616a";
            autoWin.parentNode.style.boxShadow = "0 0 15px rgba(191,97,106,0.3)";
            typeWriter(autoWin, ">> AUTONOMOUS AGENT READY...\n>> LISTENING FOR COMMANDS...", 0);

            const lokiWin = createTerminalWindow("[ ᚲ ] LOKI WAF EVADER", 'loki', 'SYSTEM');
            lokiWin.parentNode.style.borderColor = "#d08770";
            lokiWin.parentNode.style.boxShadow = "0 0 15px rgba(208,135,112,0.3)";
            typeWriter(lokiWin, ">> LOKI PAYLOAD MUTATOR LOADED...\n>> READY TO DECEIVE...", 0);

            const kvasirWin = createTerminalWindow("[ ᚱ ] KVASIR KNOWLEDGE", 'kvasir', 'SYSTEM');
            kvasirWin.parentNode.style.borderColor = "#a3be8c";
            kvasirWin.parentNode.style.boxShadow = "0 0 15px rgba(163,190,140,0.3)";
            typeWriter(kvasirWin, ">> KVASIR RAG ENGINE CONNECTED...\n>> KNOWLEDGE BASE SYNCED...", 0);
        }
        function closeAiTerminals() {
            const aiTools = ['odin_ai', 'autonomous', 'loki', 'kvasir'];
            const windows = document.querySelectorAll('.terminal-window');
            windows.forEach(win => {
                if (aiTools.includes(win._scanTool)) {
                    win.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                    win.style.opacity = '0';
                    win.style.transform = 'scale(0.95)';
                    setTimeout(() => {
                        if (win.parentNode) {
                            win.querySelector('.terminal-close-btn').click();
                        }
                    }, 500);
                }
            });
        }
        function playOdinTransition(callback) {
            const overlay = document.getElementById('odinTransitionOverlay');
            overlay.classList.add('active');
            setTimeout(() => {
                overlay.classList.remove('active');
            }, 300);
            if (callback) {
                setTimeout(callback, 150);
            }
        }
        function openThemeSettingsModal() {
            document.getElementById('themeSettingsModal').style.display = 'block';
            const currentTheme = localStorage.getItem('yggdrasilTheme') || 'standard';
            const radios = document.getElementsByName('themeSelect');
            for (let r of radios) {
                if (r.value === currentTheme) r.checked = true;
            }
        }
        function closeThemeSettingsModal() {
            document.getElementById('themeSettingsModal').style.display = 'none';
        }
        function applyTheme(themeName) {
            localStorage.setItem('yggdrasilTheme', themeName);
            if (themeName === 'dark-matte') {
                document.body.classList.add('dark-matte-theme');
            } else {
                document.body.classList.remove('dark-matte-theme');
            }
        }
        document.addEventListener('DOMContentLoaded', function initOdinMode() {
            const savedMode = localStorage.getItem('odinMode');
            applyTheme(localStorage.getItem('yggdrasilTheme') || 'standard');
            initSidebarLayouts();
            if (savedMode === 'on') {
                document.body.classList.add('odin-mode');
                document.getElementById('odinToggleLabel').innerText = 'ACTIVE';
                document.getElementById('odinToggleIcon').style.transform = 'scale(1.2)';
            }
            startHeartbeatMonitor();
            drawValkyrieTree();
        });
        let aiAnalysisCount = 0;
        async function autoAnalyzeScan(output, toolName, target) {
            if (!document.body.classList.contains('odin-mode')) return;
            if (!output || output.length < 50) return;
            analyzeTerminalContent(null, output, toolName, target);
        }
        async function analyzeTerminalContent(contentDiv, output, toolName, target) {
            const panel = document.getElementById('aiSuggestionsPanel');
            const panelContent = document.getElementById('aiSuggestionsContent');
            panel.style.display = 'block';
            const loadingId = 'ai-loading-' + Date.now();
            const loadingCard = document.createElement('div');
            loadingCard.id = loadingId;
            loadingCard.style.cssText = 'border: 1px solid rgba(235, 203, 139, 0.3); border-radius: 4px; padding: 15px; margin-bottom: 15px; background: rgba(235, 203, 139, 0.04);';
            loadingCard.innerHTML = '<span style="color: #ebcb8b;">ᛟ Heimdall analyzing <strong>' + escapeHtml(toolName.toUpperCase()) + '</strong> output' + (target ? ' on <strong>' + escapeHtml(target) + '</strong>' : '') + '...</span>';
            panelContent.insertBefore(loadingCard, panelContent.firstChild);
            const placeholder = panelContent.querySelector('div[style*="text-align: center"]');
            if (placeholder) placeholder.remove();
            try {
                const res = await fetch('/api/ai/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        output: output,
                        tool_name: toolName,
                        target: target
                    })
                });
                const data = await res.json();
                const loadEl = document.getElementById(loadingId);
                if (loadEl) loadEl.remove();
                if (data.status === 'success' && data.analysis) {
                    aiAnalysisCount++;
                    document.getElementById('aiSuggestionCount').innerText = '(' + aiAnalysisCount + ')';
                    renderAnalysisCard(panelContent, data.analysis, toolName, target, data.model);
                } else {
                    renderAnalysisError(panelContent, data.message || 'Analysis failed', toolName);
                }
            } catch (err) {
                const loadEl = document.getElementById(loadingId);
                if (loadEl) loadEl.remove();
                renderAnalysisError(panelContent, 'Network error during analysis', toolName);
            }
            panelContent.scrollTop = 0;
        }
        function renderAnalysisCard(container, analysis, toolName, target, model) {
            const card = document.createElement('div');
            card.style.cssText = 'border: 1px solid rgba(235, 203, 139, 0.35); border-radius: 4px; padding: 18px; margin-bottom: 15px; background: rgba(10, 12, 18, 0.95); animation: fadeInUp 0.4s ease-out;';
            let html = '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid rgba(235, 203, 139, 0.2); padding-bottom: 10px;">';
            html += '<span style="color: #ebcb8b; font-weight: bold; font-size: 15px;">ᛟ Heimdall Analysis: ' + escapeHtml(toolName.toUpperCase()) + '</span>';
            html += '<span style="font-size: 10px; color: var(--accent-color);">Model: ' + escapeHtml(model || 'AI') + ' | Target: ' + escapeHtml(target || 'N/A') + '</span>';
            html += '</div>';
            if (analysis.summary) {
                html += '<div style="color: #d8dee9; margin-bottom: 15px; font-style: italic; padding: 10px; background: rgba(94, 129, 172, 0.08); border-left: 3px solid #5E81AC; border-radius: 2px;">' + escapeHtml(analysis.summary) + '</div>';
            }
            if (analysis.findings && analysis.findings.length > 0) {
                html += '<div style="margin-bottom: 15px;"><h4 style="color: #ebcb8b; margin: 0 0 8px 0; font-size: 13px;">🔍 Extracted Findings (' + analysis.findings.length + ')</h4>';
                analysis.findings.forEach(f => {
                    const sevColor = { critical: '#bf616a', high: '#d08770', medium: '#ebcb8b', low: '#88c0d0', info: '#a3be8c' }[f.severity] || '#888';
                    html += '<div style="margin-bottom: 6px; padding: 6px 10px; background: rgba(94, 129, 172, 0.05); border-radius: 2px; font-size: 13px;">';
                    html += '<span style="display: inline-block; background: ' + sevColor + '; color: #0d0f18; padding: 1px 6px; border-radius: 2px; font-size: 10px; font-weight: bold; margin-right: 8px; text-transform: uppercase;">' + escapeHtml(f.severity || 'info') + '</span>';
                    html += '<span style="color: var(--text-dim); font-size: 10px; margin-right: 6px;">[' + escapeHtml(f.type || 'finding') + ']</span> ';
                    html += '<span style="color: #d8dee9;">' + escapeHtml(f.detail || '') + '</span>';
                    html += '</div>';
                });
                html += '</div>';
            }
            if (analysis.recommendations && analysis.recommendations.length > 0) {
                html += '<div><h4 style="color: #a3be8c; margin: 0 0 8px 0; font-size: 13px;">⚡ Recommended Next Steps (' + analysis.recommendations.length + ')</h4>';
                analysis.recommendations.forEach(r => {
                    html += '<div style="margin-bottom: 6px; padding: 8px 12px; background: rgba(163, 190, 140, 0.06); border-left: 3px solid #a3be8c; border-radius: 2px; font-size: 13px;">';
                    html += '<div style="color: #d8dee9; font-weight: bold;">' + escapeHtml(r.action || '') + '</div>';
                    if (r.tool) html += '<div style="color: #ebcb8b; font-size: 11px;">🛠️ Recommended tool: <strong>' + escapeHtml(r.tool) + '</strong></div>';
                    if (r.reason) html += '<div style="color: var(--text-dim); font-size: 11px;">' + escapeHtml(r.reason) + '</div>';
                    html += '</div>';
                });
                html += '</div>';
            }
            if (analysis.stats && Object.keys(analysis.stats).length > 0) {
                html += '<div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(235, 203, 139, 0.15); font-size: 11px; color: var(--accent-color); display: flex; gap: 20px;">';
                if (analysis.stats.open_ports) html += '<span>🔌 Open Ports: <strong>' + analysis.stats.open_ports + '</strong></span>';
                if (analysis.stats.services_found) html += '<span>ᛣ Services: <strong>' + analysis.stats.services_found + '</strong></span>';
                if (analysis.stats.vulnerabilities_found) html += '<span>⚠️ Vulns: <strong>' + analysis.stats.vulnerabilities_found + '</strong></span>';
                html += '</div>';
            }
            card.innerHTML = html;
            container.insertBefore(card, container.firstChild);
        }
        function renderAnalysisError(container, message, toolName) {
            const card = document.createElement('div');
            card.style.cssText = 'border: 1px solid rgba(191, 97, 106, 0.4); border-radius: 4px; padding: 15px; margin-bottom: 15px; background: rgba(191, 97, 106, 0.06);';
            card.innerHTML = '<span style="color: var(--danger-color);">⚠️ Heimdall analysis failed for <strong>' + escapeHtml(toolName.toUpperCase()) + '</strong>: ' + escapeHtml(message) + '</span>' +
                '<div style="font-size: 11px; color: var(--accent-color); margin-top: 6px;">Make sure Ollama is running with a model installed (e.g. qwen2.5-coder:7b).</div>';
            container.insertBefore(card, container.firstChild);
        }
        function toggleSuggestionsPanel() {
            const content = document.getElementById('aiSuggestionsContent');
            const toggle = document.getElementById('aiPanelToggle');
            if (content.style.display === 'none') {
                content.style.display = 'block';
                toggle.innerText = '▼';
            } else {
                content.style.display = 'none';
                toggle.innerText = '▶';
            }
        }
        function openKvasirPanel() {
            document.getElementById('kvasirModal').style.display = 'block';
            document.getElementById('kvasirSearchInput').focus();
            checkKvasirStatus();
        }
        function closeKvasirPanel() {
            document.getElementById('kvasirModal').style.display = 'none';
        }
        async function checkKvasirStatus() {
            try {
                const res = await fetch('/api/rag/status');
                const data = await res.json();
                const statusEl = document.getElementById('kvasirStatus');
                if (data.chromadb_available && data.ollama_available) {
                    statusEl.innerText = '● Online (Vector)';
                    statusEl.style.color = '#a3be8c';
                } else if (data.ollama_available) {
                    statusEl.innerText = '● Online (Keyword)';
                    statusEl.style.color = '#ebcb8b';
                } else {
                    statusEl.innerText = '● Offline KB';
                    statusEl.style.color = 'var(--accent-color)';
                }
            } catch (e) {
                document.getElementById('kvasirStatus').innerText = '● Offline KB';
            }
        }
        async function searchKvasir() {
            const query = document.getElementById('kvasirSearchInput').value.trim();
            if (!query) return;
            const resultsDiv = document.getElementById('kvasirResults');
            const searchBtn = document.getElementById('kvasirSearchBtn');
            resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--accent-color);">ᚱ Searching the roots of knowledge...</div>';
            searchBtn.disabled = true;
            searchBtn.innerText = '...';
            const collections = [];
            if (document.getElementById('kvasirColGTFOBins').checked) collections.push('gtfobins');
            if (document.getElementById('kvasirColExploitDB').checked) collections.push('exploitdb');
            if (document.getElementById('kvasirColPayloads').checked) collections.push('payloads');
            try {
                const res = await fetch('/api/rag/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, collections: collections, top_k: 5 })
                });
                const data = await res.json();
                if (data.status === 'success' && data.total_hits > 0) {
                    renderKvasirResults(resultsDiv, data);
                } else {
                    resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: #d08770;">ᚱ No knowledge found. Try different keywords or broader terms.</div>';
                }
            } catch (err) {
                resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--danger-color);">⚠️ Search failed. Is the server running?</div>';
            }
            searchBtn.disabled = false;
            searchBtn.innerText = '🔍 SEARCH';
        }
        function renderKvasirResults(container, data) {
            let html = '';
            const methodLabel = data.method === 'vector' ? '🧠 Vector Search' : '📖 Keyword Search';
            html += '<div style="font-size: 10px; color: var(--accent-color); margin-bottom: 15px;">' + methodLabel + ' · ' + data.total_hits + ' results · Query: \"' + escapeHtml(data.query) + '\"</div>';
            const collectionColors = {
                'gtfobins': { color: '#d08770', icon: '💻', label: 'GTFOBins' },
                'exploitdb': { color: '#88c0d0', icon: '⚠️', label: 'Exploit-DB' },
                'payloads': { color: '#ebcb8b', icon: '⚡', label: 'Payloads' }
            };
            for (const [colName, hits] of Object.entries(data.results)) {
                const cc = collectionColors[colName] || { color: '#a3be8c', icon: 'ᛒ', label: colName };
                html += '<div style="margin-bottom: 15px; border: 1px solid ' + cc.color + '33; border-radius: 4px; overflow: hidden;">';
                html += '<div style="background: ' + cc.color + '15; padding: 8px 12px; color: ' + cc.color + '; font-weight: bold; font-size: 12px;">' + cc.icon + ' ' + cc.label + ' (' + hits.length + ')</div>';
                hits.forEach(hit => {
                    html += '<div style="padding: 10px 14px; border-top: 1px solid rgba(255,255,255,0.03); font-size: 12px;">';
                    html += '<pre style="margin: 0; white-space: pre-wrap; color: #d8dee9; line-height: 1.5;">' + escapeHtml(hit.content) + '</pre>';
                    if (hit.score !== undefined) {
                        html += '<div style="margin-top: 4px; font-size: 10px; color: var(--accent-color);">Relevance: ' + (hit.score * 100).toFixed(0) + '%</div>';
                    }
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
                if (data.status === 'success') {
                    resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: #a3be8c;">✅ ' + escapeHtml(data.message) + '</div>';
                } else {
                    resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: #d08770;">⚠️ ' + escapeHtml(data.message) + '</div>';
                }
                checkKvasirStatus();
            } catch (err) {
                resultsDiv.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--danger-color);">⚠️ Indexing failed. Is the server running?</div>';
            }
        }
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
            if (agentPollTimer) {
                clearInterval(agentPollTimer);
                agentPollTimer = null;
            }
            document.getElementById('agentModal').style.display = 'none';
        }
        async function startAgentScan() {
            const target = document.getElementById('agentTargetInput').value.trim();
            if (!target) {
                alert('Please enter a target IP or domain.');
                return;
            }
            document.getElementById('btnStartAgent').disabled = true;
            document.getElementById('btnStartAgent').innerText = 'Starting...';
            try {
                const res = await fetch('/api/agent/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
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
                } else {
                    alert(data.message || 'Failed to start agent.');
                }
            } catch (err) {
                alert('Error starting agent. Check server connection.');
            }
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
                s.steps.forEach(step => {
                    const icon = step.status === 'completed' ? '✅' : step.status === 'running' ? '🔄' : step.status === 'blocked' ? '🚫' : '❌';
                    const bgColor = step.status === 'completed' ? 'rgba(163, 190, 140, 0.04)' :
                                    step.status === 'running' ? 'rgba(235, 203, 139, 0.06)' :
                                    step.status === 'blocked' ? 'rgba(191, 97, 106, 0.06)' : 'rgba(191, 97, 106, 0.04)';
                    html += '<div style="padding: 10px 14px; margin-bottom: 8px; background: ' + bgColor + '; border-left: 3px solid ' +
                        (step.status === 'completed' ? '#a3be8c' : step.status === 'running' ? '#ebcb8b' : '#bf616a') +
                        '; border-radius: 2px;">';
                    html += '<div style="display: flex; justify-content: space-between; align-items: center;">';
                    html += '<span>' + icon + ' <strong style="color: #ebcb8b;">Step ' + step.step + '</strong>: ' + escapeHtml(step.tool) + '</span>';
                    html += '<span style="font-size: 10px; color: var(--accent-color);">' + escapeHtml(step.status.toUpperCase()) + '</span>';
                    html += '</div>';
                    if (step.reasoning) {
                        html += '<div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">💭 ' + escapeHtml(step.reasoning) + '</div>';
                    }
                    if (step.summary) {
                        html += '<div style="font-size: 11px; color: var(--accent-color); margin-top: 3px;">📊 ' + escapeHtml(step.summary) + '</div>';
                    }
                    html += '</div>';
                });
                if (s.status === 'running' && s.current_tool) {
                    html += '<div style="text-align: center; padding: 10px; color: #ebcb8b; font-style: italic;">🔄 Executing ' + escapeHtml(s.current_tool) + '...</div>';
                }
                logDiv.innerHTML = html;
                logDiv.scrollTop = logDiv.scrollHeight;
                if (s.status === 'completed' || s.status === 'stopped' || s.status === 'error') {
                    clearInterval(agentPollTimer);
                    agentPollTimer = null;
                    const summaryDiv = document.getElementById('agentFinalSummary');
                    summaryDiv.style.display = 'block';
                    document.getElementById('agentSummaryText').innerText = s.final_summary || 'Mission complete.';
                    document.getElementById('agentPhaseBadge').innerText = s.status.toUpperCase();
                    document.getElementById('btnStopAgent').style.display = 'none';
                    if (s.status === 'completed' && document.body.classList.contains('odin-mode')) {
                        const allOutput = s.steps.map(st => st.output || '').join('\n---\n');
                        if (allOutput.trim()) {
                            autoAnalyzeScan(allOutput, 'autonomous_agent', s.target);
                        }
                    }
                }
                if (s.scope_warning) {
                    logDiv.innerHTML += '<div style="color: #d08770; font-size: 11px; margin-top: 8px; font-style: italic;">⚠️ ' + escapeHtml(s.scope_warning) + '</div>';
                }
            } catch (err) {
            }
        }
        async function stopAgentScan() {
            if (!agentSessionId) return;
            try {
                await fetch('/api/agent/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: agentSessionId })
                });
                if (agentPollTimer) {
                    clearInterval(agentPollTimer);
                    agentPollTimer = null;
                }
                document.getElementById('btnStopAgent').style.display = 'none';
                document.getElementById('agentPhaseBadge').innerText = 'STOPPED';
            } catch (err) {}
        }
        async function purgeWorkspace() {
            if (!confirm(t('purge_confirm') || 'Are you sure you want to completely purge the workspace? This will clear all terminals and scan history.')) return;
            try {
                // Clear History DB
                await fetch('/api/history/clear', { method: 'POST' });
                // Clear Terminal UI
                document.getElementById('output-area').innerHTML = '';
                // Reset Valkyrie Tree
                if (typeof resetValkyrieTree === 'function') resetValkyrieTree();
                alert('Workspace purged successfully.');
            } catch (e) {
                console.error(e);
            }
        }

        async function globalKillSwitch() {
            if (!confirm(t('killswitch_confirm') || 'CRITICAL: Are you sure you want to ABORT ALL active background scans and incursions?')) return;
            try {
                const res = await fetch('/api/task_kill_all', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    alert(`Global Kill Switch Activated. ${data.killed} active processes terminated.`);
                }
            } catch (e) {
                console.error(e);
            }
        }

        let valkyrieReportContent = '';
        async function generateValkyrieReport() {
            const terminals = [];
            const windows = document.querySelectorAll('.terminal-window');
            windows.forEach(win => {
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
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ source: 'agent_session', session_id: agentSessionId })
                    });
                    const data = await res.json();
                    if (data.status === 'success') {
                        showValkyrieReport(data.report);
                        return;
                    }
                } catch (err) {}
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
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ source: 'terminals', terminals: terminals })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    showValkyrieReport(data.report);
                } else {
                    document.getElementById('valkyrieLoading').innerHTML = '<p style=\"color: var(--danger-color);\">Failed to generate report: ' + escapeHtml(data.message || 'Unknown error') + '</p>';
                }
            } catch (err) {
                document.getElementById('valkyrieLoading').innerHTML = '<p style=\"color: var(--danger-color);\">Error generating report.</p>';
            }
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
        function closeValkyrieModal() {
            document.getElementById('valkyrieModal').style.display = 'none';
        }
        function printValkyrieReport() {
            if (!valkyrieReportContent) return;
            const win = window.open('', '_blank', 'width=900,height=700');
            fetch('/api/ai/report/html', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source: 'terminals',
                    terminals: [{ tool: 'report', target: document.getElementById('target-input').value || 'unknown', output: valkyrieReportContent }]
                })
            }).then(r => r.text()).then(html => {
                win.document.write(html);
                win.document.close();
                setTimeout(() => win.print(), 500);
            }).catch(() => alert('Failed to open print view.'));
        }
        async function fetchGtfobinsLive() {
            const resultsDiv = document.getElementById('kvasirResults');
            resultsDiv.innerHTML = '<div style=\"text-align: center; padding: 40px; color: var(--accent-color);\">🔄 Fetching latest GTFOBins data from GitHub...<br><small>This may take a moment.</small></div>';
            try {
                const res = await fetch('/api/rag/fetch', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    resultsDiv.innerHTML = '<div style=\"text-align: center; padding: 40px; color: #a3be8c;\">✅ ' + escapeHtml(data.message) + '</div>';
                } else {
                    resultsDiv.innerHTML = '<div style=\"text-align: center; padding: 40px; color: #d08770;\">⚠️ ' + escapeHtml(data.message) + '</div>';
                }
            } catch (err) {
                resultsDiv.innerHTML = '<div style=\"text-align: center; padding: 40px; color: var(--danger-color);\">⚠️ Fetch failed. Check internet connection.</div>';
            }
        }
        function openLokiPanel() {
            document.getElementById('lokiModal').style.display = 'block';
            loadLokiTechniques();
        }
        function closeLokiPanel() {
            document.getElementById('lokiModal').style.display = 'none';
        }
        async function loadLokiTechniques() {
            try {
                const res = await fetch('/api/loki/techniques');
                const data = await res.json();
                const list = document.getElementById('lokiTechniquesList');
                if (data.status === 'success') {
                    let html = '<label style=\"display:block; margin-bottom:3px; cursor:pointer;\"><input type=\"checkbox\" id=\"lokiSelectAll\" checked onchange=\"toggleAllLokiTechniques()\"> <strong>Select All</strong></label>';
                    data.techniques.forEach(t => {
                        html += '<label style=\"display:block; margin-bottom:3px; cursor:pointer; font-size:12px;\" title=\"' + escapeHtml(t.description) + '\">';
                        html += '<input type=\"checkbox\" class=\"loki-tech-cb\" value=\"' + t.key + '\" checked> ';
                        html += '<span style=\"color:#d08770;\">[' + t.category + ']</span> ' + escapeHtml(t.name);
                        html += '</label>';
                    });
                    list.innerHTML = html;
                }
            } catch (e) {
                document.getElementById('lokiTechniquesList').innerHTML = '<span style=\"color:var(--danger-color);\">Failed to load techniques.</span>';
            }
        }
        function toggleAllLokiTechniques() {
            const all = document.getElementById('lokiSelectAll').checked;
            document.querySelectorAll('.loki-tech-cb').forEach(cb => cb.checked = all);
        }
        async function mutateLokiPayload() {
            const payload = document.getElementById('lokiPayload').value.trim();
            if (!payload) return;
            const selected = [];
            document.querySelectorAll('.loki-tech-cb:checked').forEach(cb => selected.push(cb.value));
            const btn = document.getElementById('lokiMutateBtn');
            btn.disabled = true;
            btn.innerText = '...';
            const resultsDiv = document.getElementById('lokiResults');
            resultsDiv.innerHTML = '<div style=\"text-align:center;padding:30px;color:var(--accent-color);\">ᚲ Shapeshifting payloads...</div>';
            try {
                const res = await fetch('/api/loki/mutate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ payload: payload, techniques: selected, count: 8 })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    let html = '<div style=\"margin-bottom:10px;font-size:11px;color:var(--accent-color);\">Original: <code style=\"color:#d8dee9;\">' + escapeHtml(data.original) + '</code> — ' + data.total_generated + ' variants</div>';
                    data.mutations.forEach((m, i) => {
                        html += '<div style=\"margin-bottom:8px;padding:8px;background:rgba(208,135,112,0.05);border-left:3px solid #d08770;border-radius:2px;\">';
                        html += '<div style="font-size:10px;color:#d08770;margin-bottom:4px;">#' + (i+1) + ' ' + escapeHtml(m.name) + ' [' + m.category + ']</div>';
                        html += '<code style="color:#d8dee9;word-break:break-all;font-size:12px;">' + escapeHtml(m.payload) + '</code>';
                        html += '<button onclick="navigator.clipboard.writeText(\'' + m.payload.replace(/'/g, "\\'") + '\')" style="float:right;background:none;border:1px solid rgba(208,135,112,0.4);color:#d08770;padding:1px 6px;font-size:10px;cursor:pointer;width:auto;margin:0;">COPY</button>';
                        html += '</div>';
                    });
                    resultsDiv.innerHTML = html;
                } else {
                    resultsDiv.innerHTML = '<div style=\"color:var(--danger-color);text-align:center;padding:20px;\">' + escapeHtml(data.message) + '</div>';
                }
            } catch (err) {
                resultsDiv.innerHTML = '<div style=\"color:var(--danger-color);text-align:center;padding:20px;\">Mutation failed.</div>';
            }
            btn.disabled = false;
            btn.innerText = 'ᚲ MUTATE';
        }
        async function analyzeLokiWaf() {
            const code = document.getElementById('lokiWafCode').value;
            const body = document.getElementById('lokiWafBody').value;
            const analysisDiv = document.getElementById('lokiWafAnalysis');
            analysisDiv.innerHTML = '<span style=\"color:var(--accent-color);\">Analyzing WAF response...</span>';
            try {
                const res = await fetch('/api/loki/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status_code: parseInt(code), response_body: body })
                });
                const data = await res.json();
                if (data.status === 'success' && data.analysis) {
                    const a = data.analysis;
                    let html = '<div style=\"padding:10px;background:rgba(208,135,112,0.06);border:1px solid rgba(208,135,112,0.3);border-radius:4px;\">';
                    html += '<strong style=\"color:#d08770;\">🛡️ ' + escapeHtml(a.likely_waf) + '</strong> (' + a.block_type + ')<br>';
                    html += '<span style=\"font-size:11px;\">Suggested techniques: ';
                    a.suggestions.forEach(s => {
                        html += '<span style=\"background:rgba(208,135,112,0.15);padding:2px 6px;border-radius:2px;margin:2px;\">' + escapeHtml(s.technique) + '</span> ';
                    });
                    html += '</span></div>';
                    analysisDiv.innerHTML = html;
                }
            } catch (err) {
                analysisDiv.innerHTML = '<span style=\"color:var(--danger-color);\">Analysis failed.</span>';
            }
        }

        // --- YGGDRASIL HEARTBEAT & SCANS TRACKER ---
        function startHeartbeatMonitor() {
            updateHeartbeat();
            setInterval(updateHeartbeat, 3000);
        }

        async function updateHeartbeat() {
            try {
                const res = await fetch('/api/system_resources');
                const data = await res.json();
                
                // Update CPU Progress Bar
                const cpuVal = data.cpu || 0;
                document.getElementById('heartbeat-cpu-val').innerText = cpuVal.toFixed(0) + '%';
                document.getElementById('heartbeat-cpu-bar').style.width = cpuVal + '%';
                
                // Update RAM Progress Bar
                const ramVal = data.ram || 0;
                document.getElementById('heartbeat-ram-val').innerText = ramVal.toFixed(0) + '%';
                document.getElementById('heartbeat-ram-bar').style.width = ramVal + '%';
                
                // Update Ping
                const pingEl = document.getElementById('heartbeat-ping-val');
                if (data.ping !== null && data.ping !== undefined) {
                    pingEl.innerText = `ONLINE (${data.ping}ms)`;
                    pingEl.style.color = '#a3be8c';
                } else {
                    pingEl.innerText = 'OFFLINE';
                    pingEl.style.color = '#bf616a';
                }
                
                // Update AI Engine
                const aiEl = document.getElementById('heartbeat-ai-val');
                const modelEl = document.getElementById('heartbeat-model-val');
                if (data.ollama) {
                    aiEl.innerText = 'ONLINE';
                    aiEl.style.color = '#a3be8c';
                    
                    const activeModelName = odinCurrentModel || 'qwen2.5-coder:7b';
                    modelEl.innerText = activeModelName;
                    modelEl.title = activeModelName;
                    modelEl.style.color = '#81a1c1';
                } else {
                    aiEl.innerText = 'OFFLINE';
                    aiEl.style.color = '#bf616a';
                    modelEl.innerText = 'NONE';
                    modelEl.title = 'No model loaded';
                    modelEl.style.color = '#bf616a';
                }
                
                // Update Active Scans
                const container = document.getElementById('heartbeat-scans');
                const statTool = document.getElementById('stat-tool');
                if (data.active_scans && data.active_scans.length > 0) {
                    let html = '';
                    let badgeHtml = '';
                    data.active_scans.forEach(s => {
                        html += `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px; padding:3px; background:rgba(255,255,255,0.03); border-radius:2px;">`;
                        html += `<span>⚡ ${escapeHtml(s.tool.toUpperCase())} (${escapeHtml(s.target)})</span>`;
                        html += `<button onclick="abortHeartbeatScan('${s.task_id}')" style="width:auto; margin:0; padding:1px 6px; font-size:9px; border-color:var(--danger-color); color:var(--danger-color); background:none; cursor:pointer;">KILL</button>`;
                        html += `</div>`;
                        
                        let badgeColor = '#88c0d0'; 
                        let badgeBg = 'rgba(136, 192, 208, 0.1)';
                        let glowColor = 'rgba(136, 192, 208, 0.4)';
                        const tName = s.tool.toLowerCase();
                        if (tName.includes('odin') || tName.includes('loki') || tName.includes('autonomous') || tName.includes('kvasir')) {
                            badgeColor = '#ebcb8b'; 
                            badgeBg = 'rgba(235, 203, 139, 0.1)';
                            glowColor = 'rgba(235, 203, 139, 0.5)';
                        } else if (tName.includes('nmap') || tName.includes('scan') || tName.includes('erebus') || tName.includes('mimir')) {
                            badgeColor = '#a3be8c'; 
                            badgeBg = 'rgba(163, 190, 140, 0.1)';
                            glowColor = 'rgba(163, 190, 140, 0.5)';
                        } else if (tName.includes('packet') || tName.includes('inject') || tName.includes('flood') || tName.includes('hydra')) {
                            badgeColor = '#bf616a'; 
                            badgeBg = 'rgba(191, 97, 106, 0.1)';
                            glowColor = 'rgba(191, 97, 106, 0.5)';
                        }
                        
                        badgeHtml += `<span class="rune-active-badge" style="border-color: ${badgeColor}; color: ${badgeColor}; background: ${badgeBg}; --accent-color: ${badgeColor}; --accent-glow-color: ${glowColor};">${escapeHtml(s.tool.toUpperCase())}</span>`;
                    });
                    container.innerHTML = html;
                    statTool.innerHTML = badgeHtml;
                } else {
                    container.innerHTML = '<div style="color:var(--text-dim); font-style:italic;">No active incursions</div>';
                    statTool.innerHTML = `<span class="stat-value">${t('idle')}</span>`;
                }
            } catch (e) {
                console.error("Heartbeat monitor error:", e);
            }
        }

        async function abortHeartbeatScan(taskId) {
            if (!confirm('Are you sure you want to terminate this scan?')) return;
            const fd = new FormData();
            fd.append('task_id', taskId);
            try {
                const res = await fetch('/api/task_kill', { method: 'POST', body: fd });
                const data = await res.json();
                if (data.status === 'success') {
                    // Update heartbeat immediately
                    updateHeartbeat();
                    // Also trigger closing matching terminal windows
                    const windows = document.querySelectorAll('.terminal-window');
                    windows.forEach(win => {
                        if (win._taskId === taskId) {
                            win.remove();
                        }
                    });
                }
            } catch (e) {
                console.error(e);
            }
        }

        // --- VALKYRIE VULNERABILITY TREE MAP (CANVAS) ---
        let valkyrieTreeData = {
            target: '',
            ports: new Set(),
            subdomains: new Set(),
            vulns: new Set()
        };
        let valkyrieAnimFrame = null;
        let valkyriePanelCollapsed = false;

        function toggleValkyrieTreePanel() {
            const content = document.getElementById('valkyrieTreeContent');
            const toggle = document.getElementById('valkyriePanelToggle');
            if (valkyriePanelCollapsed) {
                content.style.display = 'block';
                toggle.innerText = '▼';
                valkyriePanelCollapsed = false;
                drawValkyrieTree();
            } else {
                content.style.display = 'none';
                toggle.innerText = '▲';
                valkyriePanelCollapsed = true;
                if (valkyrieAnimFrame) cancelAnimationFrame(valkyrieAnimFrame);
            }
        }

        function resetValkyrieTree() {
            valkyrieTreeData.target = '';
            valkyrieTreeData.ports.clear();
            valkyrieTreeData.subdomains.clear();
            valkyrieTreeData.vulns.clear();
            drawValkyrieTree();
        }

        function parseScanOutput(tool, target, output) {
            if (!output) return;
            
            // Set/update central target
            if (target && target !== 'NONE' && target !== 'SYSTEM') {
                valkyrieTreeData.target = target;
            } else if (!valkyrieTreeData.target) {
                valkyrieTreeData.target = document.getElementById('target-input').value || 'TARGET';
            }
            
            // 1. Match Open Ports
            const portRegex = /(\d+)\/(tcp|udp)\s+open/gi;
            let match;
            while ((match = portRegex.exec(output)) !== null) {
                valkyrieTreeData.ports.add(match[1]);
            }
            
            // 2. Match CVEs
            const cveRegex = /(CVE-\d{4}-\d+)/gi;
            while ((match = cveRegex.exec(output)) !== null) {
                valkyrieTreeData.vulns.add(match[1].toUpperCase());
            }
            
            // 3. Match Subdomains (if target domain is specified)
            const currentTarget = valkyrieTreeData.target;
            if (currentTarget && currentTarget.includes('.')) {
                // Escape target domain for regex
                const escapedDomain = currentTarget.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const subdomainRegex = new RegExp(`([a-zA-Z0-9-]+\\.${escapedDomain})`, 'gi');
                while ((match = subdomainRegex.exec(output)) !== null) {
                    if (match[1].toLowerCase() !== currentTarget.toLowerCase()) {
                        valkyrieTreeData.subdomains.add(match[1].toLowerCase());
                    }
                }
            }
            
            // Trigger visual redraw
            if (!valkyriePanelCollapsed) {
                drawValkyrieTree();
            }
        }

        function drawValkyrieTree() {
            const canvas = document.getElementById('valkyrieTreeMap');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            
            function animate(time) {
                if (valkyriePanelCollapsed) return;
                
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                const centerX = canvas.width / 2;
                const centerY = canvas.height / 2;
                const pulse = Math.sin(time / 500) * 5 + 15;
                const rotation = time / 12000;
                
                const targetText = valkyrieTreeData.target || 'NO TARGET SCAN';
                
                // Draw grid
                ctx.strokeStyle = 'rgba(136, 192, 208, 0.02)';
                ctx.lineWidth = 1;
                for (let i = 0; i < canvas.width; i += 40) {
                    ctx.beginPath();
                    ctx.moveTo(i, 0);
                    ctx.lineTo(i, canvas.height);
                    ctx.stroke();
                }
                for (let j = 0; j < canvas.height; j += 40) {
                    ctx.beginPath();
                    ctx.moveTo(0, j);
                    ctx.lineTo(canvas.width, j);
                    ctx.stroke();
                }

                // Compile nodes list
                const nodes = [];
                valkyrieTreeData.ports.forEach(port => {
                    nodes.push({ type: 'port', label: `Port ${port}`, color: '#a3be8c', glow: 'rgba(163, 190, 140, 0.4)' });
                });
                valkyrieTreeData.subdomains.forEach(sub => {
                    nodes.push({ type: 'subdomain', label: sub, color: '#88c0d0', glow: 'rgba(136, 192, 208, 0.4)' });
                });
                valkyrieTreeData.vulns.forEach(vuln => {
                    nodes.push({ type: 'vuln', label: vuln, color: '#bf616a', glow: 'rgba(191, 97, 106, 0.6)' });
                });
                
                const totalNodes = nodes.length;
                const radius = 110;
                
                nodes.forEach((node, i) => {
                    const angle = (i / totalNodes) * Math.PI * 2 + rotation;
                    const nodeX = centerX + Math.cos(angle) * radius;
                    const nodeY = centerY + Math.sin(angle) * radius;
                    
                    // Draw branch connecting lines (glowing arcs)
                    ctx.strokeStyle = 'rgba(94, 129, 172, 0.25)';
                    ctx.lineWidth = 1.5;
                    ctx.beginPath();
                    ctx.moveTo(centerX, centerY);
                    ctx.quadraticCurveTo((centerX + nodeX)/2 + 20*Math.sin(angle), (centerY + nodeY)/2 - 20*Math.cos(angle), nodeX, nodeY);
                    ctx.stroke();
                    
                    // Draw node point
                    ctx.shadowBlur = pulse;
                    ctx.shadowColor = node.glow;
                    ctx.fillStyle = node.color;
                    ctx.beginPath();
                    ctx.arc(nodeX, nodeY, 6, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.shadowBlur = 0;
                    
                    // Text
                    ctx.fillStyle = '#d8dee9';
                    ctx.font = '9px monospace';
                    ctx.textAlign = 'center';
                    ctx.fillText(node.label, nodeX, nodeY - 12);
                });
                
                // Draw trunk core
                ctx.shadowBlur = pulse + 12;
                ctx.shadowColor = 'rgba(235, 203, 139, 0.5)';
                ctx.fillStyle = '#ebcb8b';
                ctx.beginPath();
                ctx.arc(centerX, centerY, 18, 0, Math.PI * 2);
                ctx.fill();
                ctx.shadowBlur = 0;
                
                ctx.fillStyle = '#0d0f18';
                ctx.beginPath();
                ctx.arc(centerX, centerY, 14, 0, Math.PI * 2);
                ctx.fill();
                
                ctx.fillStyle = '#ebcb8b';
                ctx.font = 'bold 11px Cinzel, serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('ᛦ', centerX, centerY);
                
                ctx.fillStyle = '#ebcb8b';
                ctx.font = '10px Cinzel, serif';
                ctx.fillText(targetText, centerX, centerY + 32);
                
                valkyrieAnimFrame = requestAnimationFrame(animate);
            }
            
            if (valkyrieAnimFrame) cancelAnimationFrame(valkyrieAnimFrame);
            valkyrieAnimFrame = requestAnimationFrame(animate);
        }

        // --- INCURSIONS LOG (SCAN HISTORY) ---
        let scanHistoryCache = [];

        async function openHistoryModal() {
            document.getElementById('historyModal').style.display = 'block';
            const tbody = document.getElementById('historyTableBody');
            tbody.innerHTML = '<tr><td colspan="5" style="padding: 20px; text-align: center; color: var(--accent-color);">🔄 Retrieving scroll logs...</td></tr>';
            
            try {
                const res = await fetch('/api/history');
                const data = await res.json();
                
                if (data && data.length > 0) {
                    scanHistoryCache = data;
                    let html = '';
                    data.forEach(item => {
                        const statusColor = item.status === 'SUCCESS' ? '#a3be8c' : 
                                            item.status === 'RUNNING' ? '#ebcb8b' : '#bf616a';
                        
                        html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.05);">`;
                        html += `<td style="padding:10px;">${escapeHtml(item.timestamp)}</td>`;
                        html += `<td style="padding:10px; color:#81a1c1; font-weight:bold;">${escapeHtml(item.tool)}</td>`;
                        html += `<td style="padding:10px;">${escapeHtml(item.target)}</td>`;
                        html += `<td style="padding:10px; color:${statusColor}; font-weight:bold;">${escapeHtml(item.status)}</td>`;
                        html += `<td style="padding:10px;">`;
                        html += `<button onclick="viewHistoryOutput(${item.id})" class="btn-mini" style="width:auto; margin:0; padding:2px 8px; border-color:#88c0d0; color:#88c0d0;">VIEW</button>`;
                        html += `</td>`;
                        html += `</tr>`;
                    });
                    tbody.innerHTML = html;
                } else {
                    tbody.innerHTML = '<tr><td colspan="5" style="padding: 20px; text-align: center; color: var(--text-dim); font-style: italic;">No logs found.</td></tr>';
                }
            } catch (e) {
                tbody.innerHTML = `<tr><td colspan="5" style="padding: 20px; text-align: center; color: var(--danger-color);">⚠️ Failed to load scan history.</td></tr>`;
            }
        }

        function closeHistoryModal() {
            document.getElementById('historyModal').style.display = 'none';
        }

        async function clearScanHistory() {
            if (!confirm('Are you sure you want to permanently purge all scan logs? This cannot be undone.')) return;
            try {
                const res = await fetch('/api/history/clear', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    openHistoryModal();
                }
            } catch (e) {
                alert('Purge failed.');
            }
        }

        function viewHistoryOutput(id) {
            const item = scanHistoryCache.find(x => x.id === id);
            if (!item) return;
            closeHistoryModal();
            
            const content = createTerminalWindow(`[ HISTORIC: ${item.tool} - ${item.target} ]`, item.tool.toLowerCase(), item.target);
            typeWriter(content, item.output || '[No output logs saved]', 0);
        }

        // --- NEW MODALS (Pentest Notes, Loki, GTFOBins) ---
        function openPentestNotesModal() {
            document.getElementById('pentestNotesModal').style.display = 'block';
            const notesArea = document.getElementById('pentestNotesArea');
            if(localStorage.getItem('ygg_pentest_notes')) {
                notesArea.value = localStorage.getItem('ygg_pentest_notes');
            }
            notesArea.addEventListener('input', () => {
                localStorage.setItem('ygg_pentest_notes', notesArea.value);
            });
        }
        function closePentestNotesModal() {
            document.getElementById('pentestNotesModal').style.display = 'none';
        }

        async function openLokiModal() {
            document.getElementById('lokiPayloadsModal').style.display = 'block';
            try {
                const res = await fetch('/api/loki/techniques');
                const data = await res.json();
                const container = document.getElementById('lokiTechniques');
                container.innerHTML = '';
                if(data.techniques) {
                    data.techniques.forEach(tech => {
                        const lbl = document.createElement('label');
                        lbl.style.cssText = 'display: flex; align-items: center; gap: 5px; background: rgba(0,0,0,0.5); padding: 5px 10px; border-radius: 4px; border: 1px solid #a3be8c; color: #d8dee9; font-size: 12px; cursor: pointer;';
                        lbl.innerHTML = `<input type="checkbox" value="${tech.id}" style="accent-color: #a3be8c;"> ${tech.name}`;
                        container.appendChild(lbl);
                    });
                }
            } catch (err) {
                console.error('Failed to load Loki techniques', err);
            }
        }
        function closeLokiModal() {
            document.getElementById('lokiPayloadsModal').style.display = 'none';
        }
        async function mutatePayload() {
            const payload = document.getElementById('lokiBasePayload').value;
            if(!payload) return alert('Enter a base payload first.');
            
            const checkboxes = document.querySelectorAll('#lokiTechniques input[type="checkbox"]:checked');
            const techniques = Array.from(checkboxes).map(cb => cb.value);
            
            const resultsDiv = document.getElementById('lokiResults');
            resultsDiv.innerHTML = '<span style="color:#ebcb8b;">Mutating payload with Loki Engine...</span>';
            
            try {
                const res = await fetch('/api/loki/mutate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({payload, techniques, count: 5})
                });
                const data = await res.json();
                if(data.status === 'success') {
                    resultsDiv.innerHTML = '';
                    data.mutated_payloads.forEach(p => {
                        resultsDiv.innerHTML += `<div>${escapeHtml(p)}</div><hr style="border-color: rgba(163,190,140,0.2);">`;
                    });
                } else {
                    resultsDiv.innerHTML = `<span style="color:#bf616a;">Error: ${data.message}</span>`;
                }
            } catch(e) {
                resultsDiv.innerHTML = `<span style="color:#bf616a;">Connection error to Loki Engine.</span>`;
            }
        }

        function openGtfobinsModal() {
            document.getElementById('gtfobinsModal').style.display = 'block';
        }
        function closeGtfobinsModal() {
            document.getElementById('gtfobinsModal').style.display = 'none';
        }
        async function fetchGtfobins() {
            const query = document.getElementById('gtfobinsSearch').value.toLowerCase().trim();
            const resultsDiv = document.getElementById('gtfobinsResults');
            if(!query) return;
            
            resultsDiv.innerHTML = '<span style="color:#ebcb8b;">Connecting to GTFOBins Live...</span>';
            try {
                const res = await fetch('/api/rag/fetch', { method: 'POST' });
                const data = await res.json();
                if(data.status === 'success' && data.data && data.data[query]) {
                    const info = data.data[query];
                    let html = `<h3 style="color:#d08770; margin-top:0;">${query}</h3>`;
                    
                    for(const [funcName, funcData] of Object.entries(info)) {
                        html += `<div style="margin-bottom: 15px; border-left: 2px solid #d08770; padding-left: 10px;">
                                    <h4 style="color:#ebcb8b; margin: 0 0 5px 0;">${funcName}</h4>`;
                        if(Array.isArray(funcData)) {
                            funcData.forEach(item => {
                                if(item.description) html += `<p style="font-size:12px; margin: 5px 0;">${item.description}</p>`;
                                if(item.code) html += `<pre style="background: rgba(0,0,0,0.5); padding: 8px; border-radius: 4px; color: #a3be8c; overflow-x: auto;">${escapeHtml(item.code)}</pre>`;
                            });
                        }
                        html += `</div>`;
                    }
                    resultsDiv.innerHTML = html;
                } else {
                    resultsDiv.innerHTML = `<span style="color:#bf616a;">No GTFOBins data found for "${query}". Note: Only a subset of live binaries is currently indexed.</span>`;
                }
            } catch(e) {
                resultsDiv.innerHTML = `<span style="color:#bf616a;">Connection error.</span>`;
            }
        }