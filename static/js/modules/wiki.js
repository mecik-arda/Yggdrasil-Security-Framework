// ==========================================
// wiki.js — Wiki/Cheat Sheet Rendering & Search
// Yggdrasil Security Framework
// ==========================================

(function() {
    let wikiDataCache = null;

    window.openWikiModal = function() {
        document.getElementById('wikiModal').style.display = 'block';
        if (!wikiDataCache) {
            fetch('/static/data/wiki_handbook.json')
                .then(res => res.json())
                .then(data => {
                    wikiDataCache = data;
                    window.renderWikiData();
                })
                .catch(err => {
                    document.getElementById('wikiResultsContainer').innerHTML = '<div style="color:#bf616a; padding: 20px;">Veri yuklenemedi: ' + err + '</div>';
                });
        }
    };

    window.renderWikiData = function() {
        const container = document.getElementById('wikiResultsContainer');
        if (!wikiDataCache) return;

        const isTr = (window.jsTranslations && window.jsTranslations['btn_logout'] && window.jsTranslations['btn_logout'] !== 'LOGOUT');
        const l = isTr ? 'tr' : 'en';

        let html = '';
        wikiDataCache.forEach(category => {
            html += '<div class="wiki-category" data-cat="' + category.cat + '" style="margin-bottom: 20px;">' +
                        '<h3 style="color: #81a1c1; text-transform: uppercase; border-bottom: 1px solid #4c566a; padding-bottom: 5px; margin-top: 10px;">' + category.cat + '</h3>';
            category.cmds.forEach(cmd => {
                html += '<div class="wiki-cmd-card" style="background: rgba(0,0,0,0.4); border-left: 3px solid #88c0d0; padding: 10px; margin-top: 10px; border-radius: 4px;">' +
                            '<div style="font-weight: bold; color: #a3be8c; font-size: 16px;">' + cmd.name + '</div>' +
                            '<div style="color: #d8dee9; font-size: 13px; margin: 5px 0;">' + (cmd[l] || cmd.en) + '</div>' +
                            '<div style="background: #2e3440; padding: 5px; font-family: monospace; color: #ebcb8b; font-size: 12px; margin-bottom: 5px;">' + (cmd.syntax || '') + '</div>';
                if (cmd.ex && cmd.ex.length > 0) {
                    html += '<div style="font-size: 12px; color: #88c0d0; margin-top: 8px;">Examples:</div><ul style="margin: 5px 0 0 20px; font-size: 12px; padding-left: 0;">';
                    cmd.ex.forEach(ex => {
                        html += '<li><code style="color: #b48ead;">' + ex.c + '</code> <span style="color: #eceff4;">- ' + (ex[l] || ex.en) + '</span></li>';
                    });
                    html += '</ul>';
                }
                html += '</div>';
            });
            html += '</div>';
        });
        container.innerHTML = html;
    };

    window.filterWiki = function() {
        const term = document.getElementById('wikiSearchInput').value.toLowerCase();
        const cards = document.querySelectorAll('.wiki-cmd-card');
        cards.forEach(card => {
            if (card.innerText.toLowerCase().includes(term)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });

        const categories = document.querySelectorAll('.wiki-category');
        categories.forEach(cat => {
            const visibleCards = cat.querySelectorAll('.wiki-cmd-card[style*="display: block"]');
            const allBlockCards = Array.from(cat.querySelectorAll('.wiki-cmd-card')).filter(c => c.style.display !== 'none');
            if (allBlockCards.length === 0 && term !== '') {
                cat.style.display = 'none';
            } else {
                cat.style.display = 'block';
            }
        });
    };

    window.closeWikiModal = function() {
        document.getElementById('wikiModal').style.display = 'none';
    };
})();
