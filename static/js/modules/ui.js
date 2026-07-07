// ==========================================
// ui.js — Layout, Themes & Zen Mode
// Yggdrasil Security Framework
// ==========================================

// --- Sidebar Layout Logic ---
function applyLayout(layout) {
    const body = document.body;
    body.classList.remove('layout-accordion', 'layout-tabbed', 'layout-grid', 'layout-flyout');

    if (layout !== 'default') {
        body.classList.add('layout-' + layout);
    }
    localStorage.setItem('sidebarLayout', layout);
    const sel = document.getElementById('sidebarLayoutSelect');
    if (sel) sel.value = layout;

    const groups = document.querySelectorAll('.tool-group');
    groups.forEach(g => g.classList.remove('active'));
    if (layout === 'accordion' || layout === 'tabbed') {
        if (groups.length > 0) groups[0].classList.add('active');
    }
}

function initSidebarLayouts() {
    const savedLayout = localStorage.getItem('sidebarLayout') || 'default';
    applyLayout(savedLayout);

    document.querySelectorAll('.sidebar h3, .my-runes-title').forEach(header => {
        header.style.cursor = 'pointer';
        header.onclick = function () {
            const layout = localStorage.getItem('sidebarLayout') || 'default';
            if (layout === 'accordion' || layout === 'tabbed') {
                const parent = this.parentElement;
                if (layout === 'accordion' && parent.classList.contains('active')) {
                    parent.classList.remove('active');
                } else {
                    document.querySelectorAll('.tool-group').forEach(g => g.classList.remove('active'));
                    parent.classList.add('active');
                }
            }
        };
    });
}

window.filterTools = (function() {
    let filterTimeout;
    return function() {
        clearTimeout(filterTimeout);
        filterTimeout = setTimeout(function() {
            const searchEl = document.getElementById('sidebarSearch');
            if (!searchEl) return;
            const input = searchEl.value.toLowerCase();
            const groups = document.querySelectorAll('.tool-group');

            groups.forEach(function(group) {
                const buttons = group.querySelectorAll('button');
                let hasVisibleButton = false;
                buttons.forEach(function(btn) {
                    if (btn.innerText.toLowerCase().includes(input)) {
                        btn.style.display = '';
                        hasVisibleButton = true;
                    } else {
                        btn.style.display = 'none';
                    }
                });
                if (!hasVisibleButton && input !== '') {
                    group.style.display = 'none';
                } else {
                    group.style.display = '';
                }
            });

            const runesContainer = document.querySelector('.my-runes-container');
            if (runesContainer) {
                const visibleButtons = Array.from(runesContainer.querySelectorAll('button')).some(b => b.style.display !== 'none');
                runesContainer.style.display = (visibleButtons || input === '') ? '' : 'none';
            }
        }, 150);
    };
})();

// --- Odin Mode (AI Terminals) ---
function toggleOdinMode() {
    const body = document.body;
    const isActive = body.classList.contains('odin-mode');
    if (isActive) {
        playOdinTransition(function () {
            body.classList.remove('odin-mode');
            document.getElementById('odinToggleLabel').innerText = '' + window.t('btn_odin_mode') + '';
            document.getElementById('odinToggleIcon').style.transform = 'scale(1)';
            closeAiTerminals();
        });
        localStorage.setItem('odinMode', 'off');
    } else {
        playOdinTransition(function () {
            body.classList.add('odin-mode');
            document.getElementById('odinToggleLabel').innerText = '' + window.t('btn_odin_mode_exit') + '';
            document.getElementById('odinToggleIcon').style.transform = 'scale(1.2)';
            spawnAiTerminals();
        });
        localStorage.setItem('odinMode', 'on');
    }
}

function spawnAiTerminals() {
    const odinWin = window.createTerminalWindow("[ 👁️ ] ODIN'S EYE AI", 'odin_ai', 'SYSTEM');
    odinWin.parentNode.style.borderColor = '#ebcb8b';
    odinWin.parentNode.style.boxShadow = '0 0 15px rgba(235,203,139,0.3)';
    window.typeWriter(odinWin, '>> ODIN AI SYSTEM INITIALIZED...\n>> AWAITING INPUT...\n>> HINT: Use the button on the left panel to open the interactive chat modal.', 0);

    const autoWin = window.createTerminalWindow('[ ᛏ ] AUTONOMOUS AGENT', 'autonomous', 'SYSTEM');
    autoWin.parentNode.style.borderColor = '#bf616a';
    autoWin.parentNode.style.boxShadow = '0 0 15px rgba(191,97,106,0.3)';
    window.typeWriter(autoWin, '>> AUTONOMOUS AGENT READY...\n>> LISTENING FOR COMMANDS...', 0);

    const lokiWin = window.createTerminalWindow('[ ᚲ ] LOKI WAF EVADER', 'loki', 'SYSTEM');
    lokiWin.parentNode.style.borderColor = '#d08770';
    lokiWin.parentNode.style.boxShadow = '0 0 15px rgba(208,135,112,0.3)';
    window.typeWriter(lokiWin, '>> LOKI PAYLOAD MUTATOR LOADED...\n>> READY TO DECEIVE...', 0);

    const kvasirWin = window.createTerminalWindow('[ ᚱ ] KVASIR KNOWLEDGE', 'kvasir', 'SYSTEM');
    kvasirWin.parentNode.style.borderColor = '#a3be8c';
    kvasirWin.parentNode.style.boxShadow = '0 0 15px rgba(163,190,140,0.3)';
    window.typeWriter(kvasirWin, '>> KVASIR RAG ENGINE CONNECTED...\n>> KNOWLEDGE BASE SYNCED...', 0);
}

function closeAiTerminals() {
    const aiTools = ['odin_ai', 'autonomous', 'loki', 'kvasir'];
    const windows = document.querySelectorAll('.terminal-window');
    windows.forEach(win => {
        if (aiTools.includes(win._scanTool)) {
            win.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            win.style.opacity = '0';
            win.style.transform = 'scale(0.95)';
            setTimeout(function () {
                if (win.parentNode) {
                    const closeBtn = win.querySelector('.terminal-close-btn');
                    if (closeBtn) closeBtn.click();
                }
            }, 500);
        }
    });
}

function playOdinTransition(callback) {
    const overlay = document.getElementById('odinTransitionOverlay');
    overlay.classList.add('active');
    setTimeout(function () {
        overlay.classList.remove('active');
    }, 300);
    if (callback) {
        setTimeout(callback, 150);
    }
}

// --- Theme Management ---
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

// --- Profile Modal ---
function openProfileModal() {
    document.getElementById('profileModal').style.display = 'block';
}

function closeProfileModal() {
    document.getElementById('profileModal').style.display = 'none';
}

// --- Zen Mode ---
function toggleZenMode() {
    const isZen = document.body.classList.toggle('zen-mode');
    if (isZen) {
        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen().catch(function () { });
        }
    } else {
        if (document.fullscreenElement && document.exitFullscreen) {
            document.exitFullscreen().catch(function () { });
        }
    }
}

document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && document.body.classList.contains('zen-mode')) {
        toggleZenMode();
    }
});

// --- Global Actions ---
async function purgeWorkspace() {
    if (!confirm(window.t('purge_confirm') || 'Are you sure you want to completely purge the workspace? This will clear all terminals and scan history.')) return;
    try {
        await fetch('/api/history/clear', { method: 'POST' });
        document.getElementById('output-area').innerHTML = '';
        if (typeof resetValkyrieTree === 'function') resetValkyrieTree();
        alert('Workspace purged successfully.');
    } catch (e) {
        console.error(e);
    }
}

async function globalKillSwitch() {
    if (!confirm(window.t('killswitch_confirm') || 'CRITICAL: Are you sure you want to ABORT ALL active background scans and incursions?')) return;
    try {
        const res = await fetch('/api/task_kill_all', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            alert('Global Kill Switch Activated. ' + data.killed + ' active processes terminated.');
        }
    } catch (e) {
        console.error(e);
    }
}

// --- Pentest Notes ---
function openPentestNotesModal() {
    document.getElementById('pentestNotesModal').style.display = 'block';
    const notesArea = document.getElementById('pentestNotesArea');
    if (localStorage.getItem('ygg_pentest_notes')) {
        notesArea.value = localStorage.getItem('ygg_pentest_notes');
    }
    notesArea.addEventListener('input', function () {
        localStorage.setItem('ygg_pentest_notes', notesArea.value);
    });
}

function closePentestNotesModal() {
    document.getElementById('pentestNotesModal').style.display = 'none';
}
