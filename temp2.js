alert(1)</script>"
                        style="width: 100%; padding: 10px; background: var(--bg-dark); color: white; border: 1px solid rgba(208, 135, 112, 0.4); font-family: 'Courier New', monospace; font-size: 13px; resize: vertical; box-sizing: border-box;"></textarea>
                    <h4 style="color: #ebcb8b; margin: 15px 0 10px 0;">🛠️ Techniques</h4>
                    <div id="lokiTechniquesList" style="max-height: 200px; overflow-y: auto; font-size: 12px;">
                        <span style="color: var(--accent-color);">Loading techniques...</span>
                    </div>
                    <div style="display: flex; gap: 10px; margin-top: 15px;">
                        <button onclick="mutateLokiPayload()" id="lokiMutateBtn" class="btn-install" style="flex: 1; margin: 0; background: #d08770; color: white;">ᚲ MUTATE</button>
                        <button onclick="document.getElementById('lokiSelectAll').checked=!document.getElementById('lokiSelectAll').checked;toggleAllLokiTechniques()" style="width: auto; margin: 0; padding: 8px 12px; font-size: 11px;">All</button>
                    </div>
                </div>
                <!-- Right: Results -->
                <div>
                    <h4 style="color: #a3be8c; margin: 0 0 10px 0;">⚡ Mutated Payloads</h4>
                    <div id="lokiResults" style="background: rgba(10, 12, 18, 0.95); border: 1px solid rgba(208, 135, 112, 0.3); border-radius: 4px; min-height: 250px; max-height: 400px; overflow-y: auto; padding: 10px; font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.6;">
                        <div style="color: var(--text-dim); text-align: center; padding: 50px 20px;">
                            <div style="font-size: 36px;">ᚲ</div>
                            <p>Enter a payload and click MUTATE to generate WAF evasion variants.</p>
                        </div>
                    </div>
                </div>
            </div>
            <!-- WAF Analyzer strip -->
            <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(208, 135, 112, 0.2); display: flex; gap: 10px; align-items: center;">
                <span style="color: #d08770; font-weight: bold; white-space: nowrap;">🛡️ WAF Analyzer:</span>
                <select id="lokiWafCode" style="background: var(--bg-dark); color: white; border: 1px solid rgba(208, 135, 112, 0.4); padding: 5px; font-size: 12px;">
                    <option value="403">403 Forbidden</option>
                    <option value="406">406 Not Acceptable</option>
                    <option value="429">429 Rate Limited</option>
                </select>
                <input type="text" id="lokiWafBody" placeholder="Response body (optional)" style="flex: 1; padding: 5px 8px; background: var(--bg-dark); color: white; border: 1px solid rgba(208, 135, 112, 0.4); font-size: 12px; margin-bottom: 0;">
                <button onclick="analyzeLokiWaf()" class="btn-mini" style="color: #d08770; border-color: rgba(208, 135, 112, 0.4); white-space: nowrap;">ANALYZE</button>
            </div>
            <div id="lokiWafAnalysis" style="margin-top: 10px; font-size: 11px; color: var(--accent-color);"></div>
        </div>
    </div>
    <!-- ⚡ Valkyrie Report Modal -->
    <div id="valkyrieModal" class="modal">
        <div class="modal-content" style="max-width: 900px; width: 95%; max-height: 90vh; overflow-y: auto; text-align: left; padding: 30px; border: 2px solid #a3be8c; box-shadow: 0 0 40px rgba(163, 190, 140, 0.15);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid rgba(163, 190, 140, 0.3); padding-bottom: 15px;">
                <h2 style="color: #a3be8c; margin: 0; font-size: 22px; letter-spacing: 2px;">⚡ VALKYRIE — SECURITY REPORT</h2>
                <div style="display: flex; gap: 10px;">
                    <button onclick="downloadValkyrieReport()" class="btn-install" style="width: auto; margin: 0; padding: 8px 20px; background: #a3be8c; color: var(--bg-dark);">📥 DOWNLOAD .MD</button>
                    <button onclick="printValkyrieReport()" class="btn-install" style="width: auto; margin: 0; padding: 8px 20px; background: #5E81AC; color: white;">🖨️ PRINT / PDF</button>
                    <button onclick="closeValkyrieModal()" class="btn-cancel" style="width: auto; margin: 0; padding: 5px 15px;">✕</button>
                </div>
            </div>
            <!-- Loading -->
            <div id="valkyrieLoading" style="text-align: center; padding: 60px; color: var(--accent-color);">
                <div style="font-size: 48px; margin-bottom: 15px;">⚡</div>
                <p>Valkyrie is compiling the report...</p>
            </div>
            <!-- Report preview -->
            <div id="valkyriePreview" style="display: none; background: rgba(10, 12, 18, 0.95); border: 1px solid rgba(163, 190, 140, 0.2); border-radius: 4px; padding: 25px; font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.7; color: #d8dee9; max-height: 55vh; overflow-y: auto; white-space: pre-wrap;">
            </div>
        </div>
    </div>
    <div id="depManagerModal" class="modal">
        <div class="modal-content" style="max-width: 800px; width: 90%;">
            <h2 style="color: var(--wood-light); margin-top:0;">""</h2>
            <p style="color: var(--text-color); margin-bottom: 20px;">""</p>
            <div style="max-height: 50vh; overflow-y: auto; margin-bottom: 20px; border: 1px solid var(--accent-color); padding: 10px; background: rgba(0,0,0,0.3);">
                <table id="depTable" style="width: 100%; border-collapse: collapse; color: white; text-align: left; font-family: 'Courier New', Courier, monospace; font-size: 14px;">
                    <thead>
                        <tr style="border-bottom: 1px solid var(--accent-color);">
                            <th style="padding: 10px;"><input type="checkbox" id="selectAllDeps" onclick="toggleSelectAllDeps()"></th>
                            <th style="padding: 10px;">""</th>
                            <th style="padding: 10px;">""</th>
                            <th style="padding: 10px;">""</th>
                            <th style="padding: 10px;">""</th>
                        </tr>
                    </thead>
                    <tbody id="depTableBody">
                    </tbody>
                </table>
            </div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <button onclick="installSelectedDependencies()" class="btn-install" style="flex: 1; min-width: 120px; background-color: var(--highlight-color); border-color: var(--highlight-color); color: var(--bg-dark);">INSTALL</button>
                <button onclick="updateSelectedDependencies()" class="btn-install" style="flex: 1; min-width: 120px; background-color: #5E81AC; border-color: #5E81AC; color: white;">UPDATE</button>
                <button onclick="removeSelectedDependencies()" class="btn-cancel" style="flex: 1; min-width: 120px; background-color: var(--danger-color); border-color: var(--danger-color); color: white;">UNINSTALL</button>
                <button onclick="closeDependencyManager()" class="btn-cancel" style="flex: 1; min-width: 120px; background-color: #4C566A; border-color: #4C566A; color: white;">CLOSE</button>
            </div>
        </div>
    </div>
    <!-- AI Package Manager Modal -->
    <div id="aiPackageManagerModal" class="modal">
        <div class="modal-content" style="max-width: 800px; width: 90%; text-align: left; border: 2px solid #b48ead; box-shadow: 0 0 40px rgba(180, 142, 173, 0.2);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid rgba(180, 142, 173, 0.3); padding-bottom: 15px;">
                <h2 style="color: #b48ead; margin: 0; font-size: 22px; letter-spacing: 2px;">ᛟ ODIN'S EYE — PACKAGE MANAGER RITUAL</h2>
                <button onclick="closeAiPackageManager()" class="btn-cancel" style="width: auto; margin: 0; padding: 5px 15px;">✕</button>
            </div>
            <div style="margin-bottom: 20px; font-size: 14px; color: var(--text-color);">
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.3); padding: 10px 15px; border-radius: 4px; border: 1px solid var(--accent-color);">
                    <span>Select AI Profile Tier to install or manage local LLM weights.</span>
                    <span id="aiDiskUsage" style="color: #ebcb8b; font-weight: bold;">ᛚ Disk Used: 0.00 GB</span>
                </div>
            </div>
            <div id="aiTiersContainer" style="display: flex; flex-direction: column; gap: 15px; margin-bottom: 25px;">
                <!-- Tiers will be rendered here -->
            </div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <button onclick="installSelectedAiTier()" class="btn-install" style="flex: 1; min-width: 120px; background-color: #a3be8c; border-color: #a3be8c; color: var(--bg-dark);">⚡ INSTALL SELECTED TIER</button>
                <button onclick="updateSelectedAiTier()" class="btn-install" style="flex: 1; min-width: 120px; background-color: #5E81AC; border-color: #5E81AC; color: white;">🔄 UPDATE MODELS</button>
                <button onclick="purgeSelectedAiTier()" class="btn-cancel" style="flex: 1; min-width: 120px; background-color: var(--danger-color); border-color: var(--danger-color); color: white;">🗑️ PURGE TIER</button>
            </div>
        </div>
    </div>
    <script>
        const originalFetch = window.fetch;
        window._lastScanRequest = { tool: '', target: '' };
        window.fetch = async function() {
            let [resource, config] = arguments;
            if (config && config.method && config.method.toUpperCase() === 'POST') {
                config.headers = config.headers || {};
                config.headers['X-CSRFToken'] = '""';
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
        const translations = "";
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
                document.getElementById('stat-tool').innerText = stats.active_tool;
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
                                <div style="font-weight: bold; color: ${isSelected ? '#b48ead' : 'var(--wood-light)'}; font-size: 16px; margin-bottom: 5px;" id="ai-tier-title-${tier.id}">${tier.name}</div>
                                <div style="color: var(--text-color); font-size: 13px; margin-bottom: 8px;">${tier.description}</div>
                                <div style="font-size: 12px; color: var(--accent-color); margin-bottom: 8px;">
                                    <strong>RAM:</strong> ${tier.ram} | <strong>GPU:</strong> ${tier.gpu} | <strong>Speed:</strong> ${tier.speed}
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
                updateContentDiv.innerHTML = "<span style='color: #a3be8c;'>[ UPDATE ""LED. THE ROOTS REMAIN UNTOUCHED. ]</span>";
            }
            document.getElementById('status-display').innerText = ">> OPERATION ""ED.";
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
            document.getElementById('status-display').innerText = ">> RITUAL ""ED.";
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
            contentDiv.innerHTML = "<span style='color: var(--highlight-color);'>[ CONNECTING TO THE WORLD TREE... ]</span>";
            const formData = new FormData();
            formData.append('tool', tool);
            formData.append('target', target);
            formData.append('action', 'run');
            try {
                const response = await fetch('/api/action', { method: 'POST', body: formData });
                const data = await response.json();
                updateStats();
                contentDiv.innerHTML = ""; 
                if (data.type === 'html') {
                    contentDiv.innerHTML = data.output;
                } else {
                    typeWriter(contentDiv, data.output, 0);
                }
                statusDiv.innerText = t('operation_complete');
                statusDiv.style.color = "var(--highlight-color)";
                statusDiv.style.borderColor = "var(--highlight-color)";
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
                    updateStats();
                    contentDiv.innerHTML = ""; 
                    if (data.type === 'html') {
                        contentDiv.innerHTML = data.output;
                    } else {
                        typeWriter(contentDiv, data.output, 0);
                    }
                    statusDiv.innerText = t('operation_complete');
                    statusDiv.style.color = "var(--highlight-color)";
                    statusDiv.style.borderColor = "var(--highlight-color)";
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
                    updateStats();
                    contentDiv.innerHTML = ""; 
                    if (data.type === 'html') {
                        contentDiv.innerHTML = data.output;
                    } else {
                        typeWriter(contentDiv, data.output, 0);
                    }
                    statusDiv.innerText = t('operation_complete');
                    statusDiv.style.color = "var(--highlight-color)";
                    statusDiv.style.borderColor = "var(--highlight-color)";
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
                    updateStats();
                    contentDiv.innerHTML = ""; 
                    if (data.type === 'html') {
                        contentDiv.innerHTML = data.output;
                    } else {
                        typeWriter(contentDiv, data.output, 0);
                    }
                    statusDiv.innerText = t('injection_complete');
                    statusDiv.style.color = "var(--highlight-color)";
                    statusDiv.style.borderColor = "var(--highlight-color)";
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
        function toggleOdinMode() {
            const body = document.body;
            const isActive = body.classList.contains('odin-mode');
            if (isActive) {
                playOdinTransition(() => {
                    body.classList.remove('odin-mode');
                    document.getElementById('odinToggleLabel').innerText = 'ODIN MODE';
                    document.getElementById('odinToggleIcon').style.transform = 'scale(1)';
                });
                localStorage.setItem('odinMode', 'off');
            } else {
                playOdinTransition(() => {
                    body.classList.add('odin-mode');
                    document.getElementById('odinToggleLabel').innerText = 'ACTIVE';
                    document.getElementById('odinToggleIcon').style.transform = 'scale(1.2)';
                });
                localStorage.setItem('odinMode', 'on');
            }
        }
        function playOdinTransition(callback) {
            const overlay = document.getElementById('odinTransitionOverlay');
            overlay.classList.add('active');
            setTimeout(() => {
                overlay.classList.remove('active');
                if (callback) callback();
            }, 300);
            if (callback) {
                setTimeout(callback, 150);
            }
        }
        function toggleOdinAnimations() {
            const body = document.body;
            const isNoAnim = body.classList.contains('no-odin-animations');
            if (isNoAnim) {
                body.classList.remove('no-odin-animations');
                localStorage.setItem('odinAnimations', 'on');
                const btn = document.getElementById('odinSettingsBtn');
                btn.style.color = '#a3be8c';
                setTimeout(() => { btn.style.color = ''; }, 800);
            } else {
                body.classList.add('no-odin-animations');
                localStorage.setItem('odinAnimations', 'off');
                const btn = document.getElementById('odinSettingsBtn');
                btn.style.color = 'var(--danger-color)';
                setTimeout(() => { btn.style.color = ''; }, 800);
            }
        }
        document.addEventListener('DOMContentLoaded', function initOdinMode() {
            const savedMode = localStorage.getItem('odinMode');
            const savedAnim = localStorage.getItem('odinAnimations');
            if (savedMode === 'on') {
                document.body.classList.add('odin-mode');
                document.getElementById('odinToggleLabel').innerText = 'ACTIVE';
                document.getElementById('odinToggleIcon').style.transform = 'scale(1.2)';
            }
            if (savedAnim === 'off') {
                document.body.classList.add('no-odin-animations');
            }
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
                        html += '<div style=\"font-size:10px;color:#d08770;margin-bottom:4px;\">#' + (i+1) + ' ' + escapeHtml(m.name) + ' [' + m.category + ']</div>';
                        html += '<code style=\"color:#d8dee9;word-break:break-all;font-size:12px;\">' + escapeHtml(m.payload) + '</code>';
                        html += '<button onclick=\"navigator.clipboard.writeText(\'' + m.payload.replace(/'/g, \"\\'\") + '\')\" style=\"float:right;background:none;border:1px solid rgba(208,135,112,0.4);color:#d08770;padding:1px 6px;font-size:10px;cursor:pointer;width:auto;margin:0;\">COPY</button>';
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
    