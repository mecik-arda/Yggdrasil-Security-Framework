// ==========================================
// app.js — Yggdrasil Main Orchestrator & Bootstrapper
// Loads after all modules. Initializes globals and triggers startup.
// ==========================================

// --- Translation helper (uses preloaded jsTranslations) ---
const translations = window.jsTranslations || {};
function t(key, params) {
    params = params || {};
    let text = translations[key] || key;
    for (const [k, v] of Object.entries(params)) {
        text = text.replace('{' + k + '}', v);
    }
    return text;
}
window.t = t;

function setLang(lang) {
    fetch('/api/set_lang', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lang: lang })
    }).then(function () { window.location.reload(); });
}
window.setLang = setLang;

// --- DOMContentLoaded: Kick off everything ---
document.addEventListener('DOMContentLoaded', function () {
    // Apply saved theme
    applyTheme(localStorage.getItem('yggdrasilTheme') || 'standard');

    // Initialize sidebar layouts
    initSidebarLayouts();

    // Initialize SocketIO
    initSocketIO();

    // Load tools into sidebar
    loadTools();

    // Initial stats fetch
    updateStats();

    // Stats polling fallback (when SocketIO not connected)
    if (!window.socketConnected) {
        setInterval(updateStats, 5000);
    }

    // Start heartbeat monitor
    startHeartbeatMonitor();

    // Draw Valkyrie tree
    if (typeof drawValkyrieTree === 'function') {
        drawValkyrieTree();
    }

    // Restore Odin mode if saved
    const savedMode = localStorage.getItem('odinMode');
    if (savedMode === 'on') {
        document.body.classList.add('odin-mode');
        const label = document.getElementById('odinToggleLabel');
        const icon = document.getElementById('odinToggleIcon');
        if (label) label.innerText = 'ACTIVE';
        if (icon) icon.style.transform = 'scale(1.2)';
    }
});
