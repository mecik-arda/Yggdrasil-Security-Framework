// ==========================================
// terminal.js — Terminal Creation, Streaming & Output Analysis
// Yggdrasil Security Framework
// ==========================================

let currentTool = '';
let isProcessRunning = false;
let aiAnalysisCount = 0;

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function htmlEscape(str) {
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

function typeWriter(element, text, i) {
    if (i < text.length) {
        let chunkSize = text.length > 5000 ? 50 : (text.length > 1000 ? 15 : 1);
        element.textContent += text.substring(i, i + chunkSize);
        element.scrollTop = element.scrollHeight;
        let timeout = setTimeout(function () { typeWriter(element, text, i + chunkSize); }, 2);
        if (!element.typewriterTimeouts) element.typewriterTimeouts = [];
        element.typewriterTimeouts.push(timeout);
    } else if (element.typewriterTimeouts) {
        element.typewriterTimeouts.forEach(function (t) { clearTimeout(t); });
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
    copyBtn.onclick = function () {
        navigator.clipboard.writeText(content.innerText);
        copyBtn.innerText = 'COPIED!';
        setTimeout(function () { copyBtn.innerText = 'COPY'; }, 2000);
    };
    const aiBtn = document.createElement('button');
    aiBtn.className = 'btn-mini';
    aiBtn.style.color = '#ebcb8b';
    aiBtn.style.borderColor = 'rgba(235, 203, 139, 0.4)';
    aiBtn.innerText = '🧠 AI';
    aiBtn.title = 'Analyze with Heimdall AI';
    aiBtn.onclick = function () {
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
    closeBtn.onclick = function () {
        if (content.typewriterTimeouts) {
            content.typewriterTimeouts.forEach(function (t) { clearTimeout(t); });
        }
        if (win._taskId) {
            const fd = new FormData();
            fd.append('task_id', win._taskId);
            fetch('/api/task_kill', { method: 'POST', body: fd }).catch(function (e) { console.error(e); });
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

        input.addEventListener('keypress', async function (e) {
            if (e.key === 'Enter') {
                const val = input.value.trim();
                if (!val) return;
                input.value = '';
                input.disabled = true;

                const userDiv = document.createElement('div');
                userDiv.style.cssText = 'margin-top: 8px; margin-bottom: 8px; font-family: monospace; font-size:13px;';
                userDiv.innerHTML = '<span style="color:#88c0d0; font-weight:bold;">[USER]:</span> ' + escapeHtml(val);
                content.appendChild(userDiv);
                content.scrollTop = content.scrollHeight;

                const thinkingDiv = document.createElement('div');
                thinkingDiv.style.cssText = 'color:#ebcb8b; font-style:italic; font-size:12px; margin-bottom:8px; font-family: monospace;';
                thinkingDiv.innerText = 'ᛟ Odin is thinking...';
                content.appendChild(thinkingDiv);
                content.scrollTop = content.scrollHeight;

                window.odinMessages.push({ role: 'user', content: val });

                try {
                    if (!window.odinCurrentModel) {
                        const statusRes = await fetch('/api/ai/status');
                        const statusData = await statusRes.json();
                        if (statusData.status === 'success' && statusData.models && statusData.models.length > 0) {
                            window.odinCurrentModel = statusData.models[0].name;
                        }
                    }

                    const res = await fetch('/api/ai/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            model: window.odinCurrentModel || 'qwen2.5-coder:7b',
                            messages: window.odinMessages
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
                        window.odinMessages.push({ role: 'assistant', content: data.response });
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
                setTimeout(function () { content.scrollTop = content.scrollHeight; }, 100);
            }
        });
    }

    outputArea.insertBefore(win, outputArea.firstChild);
    return content;
}

function downloadArtifact(type) {
    const content = document.getElementById('output-area').innerText;
    const target = document.getElementById('target-input').value || 'unknown_target';
    const tool = currentTool || 'tool';
    const timestamp = new Date().toISOString().slice(0, 10);
    let filename = 'yggdrasil_' + target + '_' + tool + '_' + timestamp + '.' + type;
    let blob;
    if (type === 'json') {
        const data = { target: target, tool: tool, date: timestamp, log: content };
        blob = new Blob([JSON.stringify(data, null, 4)], { type: 'application/json' });
    } else {
        blob = new Blob([content], { type: 'text/plain' });
    }
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
}

// --- AI Analysis ---
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
        analysis.findings.forEach(function (f) {
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
        analysis.recommendations.forEach(function (r) {
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

// --- Valkyrie Vulnerability Tree Map (Canvas) ---
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

    if (target && target !== 'NONE' && target !== 'SYSTEM') {
        valkyrieTreeData.target = target;
    } else if (!valkyrieTreeData.target) {
        valkyrieTreeData.target = document.getElementById('target-input').value || 'TARGET';
    }

    const portRegex = /(\d+)\/(tcp|udp)\s+open/gi;
    let match;
    while ((match = portRegex.exec(output)) !== null) {
        valkyrieTreeData.ports.add(match[1]);
    }

    const cveRegex = /(CVE-\d{4}-\d+)/gi;
    while ((match = cveRegex.exec(output)) !== null) {
        valkyrieTreeData.vulns.add(match[1].toUpperCase());
    }

    const currentTarget = valkyrieTreeData.target;
    if (currentTarget && currentTarget.includes('.')) {
        const escapedDomain = currentTarget.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const subdomainRegex = new RegExp('([a-zA-Z0-9-]+\\.' + escapedDomain + ')', 'gi');
        while ((match = subdomainRegex.exec(output)) !== null) {
            if (match[1].toLowerCase() !== currentTarget.toLowerCase()) {
                valkyrieTreeData.subdomains.add(match[1].toLowerCase());
            }
        }
    }

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

        const nodes = [];
        valkyrieTreeData.ports.forEach(function (port) {
            nodes.push({ type: 'port', label: 'Port ' + port, color: '#a3be8c', glow: 'rgba(163, 190, 140, 0.4)' });
        });
        valkyrieTreeData.subdomains.forEach(function (sub) {
            nodes.push({ type: 'subdomain', label: sub, color: '#88c0d0', glow: 'rgba(136, 192, 208, 0.4)' });
        });
        valkyrieTreeData.vulns.forEach(function (vuln) {
            nodes.push({ type: 'vuln', label: vuln, color: '#bf616a', glow: 'rgba(191, 97, 106, 0.6)' });
        });

        const totalNodes = nodes.length;
        const radius = 110;

        nodes.forEach(function (node, i) {
            const angle = (i / totalNodes) * Math.PI * 2 + rotation;
            const nodeX = centerX + Math.cos(angle) * radius;
            const nodeY = centerY + Math.sin(angle) * radius;

            ctx.strokeStyle = 'rgba(94, 129, 172, 0.25)';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.quadraticCurveTo((centerX + nodeX) / 2 + 20 * Math.sin(angle), (centerY + nodeY) / 2 - 20 * Math.cos(angle), nodeX, nodeY);
            ctx.stroke();

            ctx.shadowBlur = pulse;
            ctx.shadowColor = node.glow;
            ctx.fillStyle = node.color;
            ctx.beginPath();
            ctx.arc(nodeX, nodeY, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;

            ctx.fillStyle = '#d8dee9';
            ctx.font = '9px monospace';
            ctx.textAlign = 'center';
            ctx.fillText(node.label, nodeX, nodeY - 12);
        });

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
