// ==========================================
// Tool Mapper and Configuration
// Extracted from api.js
// ==========================================

async function loadTools() {
    try {
        const response = await fetch('/api/tools');
        const tools = await response.json();
        window.toolsConfig = tools;
        Object.keys(tools).forEach(function (toolKey) {
            const tool = tools[toolKey];
            const categoryContainer = document.querySelector('[data-category="' + tool.category + '"]');
            if (categoryContainer) {
                const btn = document.createElement('button');
                btn.innerText = window.t(tool.name);
                btn.onclick = function () {
                    if (toolKey === 'update_modules') {
                        initiateUpdateCheck();
                    } else if (tool.has_modal) {
                        if (toolKey === 'erebus') { openErebusModal(); return; }
                        if (toolKey === 'fenrir') { openFenrirModal(); return; }
                        if (toolKey === 'packet_injector') { openPacketInjectorModal(); }
                        else if (toolKey === 'hydra') { openHydraModal(); }
                        else if (toolKey === 'subfinder') { openSubfinderModal(); }
                        else if (toolKey === 'knockpy') { openKnockpyModal(); }
                        else if (toolKey === 'gobuster_dns') { openGobusterDnsModal(); }
                        else if (toolKey === 'muninn_scanner') { openMuninnModal(); }
                        else if (toolKey === 'sleipnir_scanner') { openSleipnirModal(); }
                        else if (toolKey === 'adv_syn_scan') { openSynModal(); }
                        else if (toolKey === 'loki') { openLokiPanel(); }
                        else if (toolKey === 'odin_ai') { openOdinChat(); }
                        else { openSynModal(); }
                    } else {
                        runTool(toolKey);
                    }
                };
                categoryContainer.appendChild(btn);
            }
        });
    } catch (e) { console.error("Error loading tools:", e); }
}
