import os

index_path = r'C:\Users\ardam\Desktop\Yggdrasil-Security-Framework\templates\index.html'

with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    # HTML Replacements
    "TOTAL INCURSIONS": "{{ t('total_incursions') }}",
    "LAST TARGET": "{{ t('last_target') }}",
    "ACTIVE RUNE": "{{ t('active_rune') }}",
    "IDLE": "{{ t('idle') }}",
    "NONE": "{{ t('none') }}",
    ">> ENTER TARGET IP/DOMAIN <<": "{{ t('target_placeholder') }}",
    "[ ᚠ ] PASSIVE RECON": "{{ t('cat_passive_recon') }}",
    "[ ᛉ ] DNS & SUBDOMAIN": "{{ t('cat_dns') }}",
    "[ ᛦ ] ACTIVE SCANNING": "{{ t('cat_active_scan') }}",
    "[ ᚾ ] NMAP VARIANTS": "{{ t('cat_nmap') }}",
    "[ ᛟ ] VULNERABILITY": "{{ t('cat_vuln') }}",
    "[ ᛝ ] MY RUNES": "{{ t('my_runes') }}",
    "[ ᛖ ] EREBUS SCANNER (RUST)": "{{ t('rune_erebus') }}",
    "[ ᚷ ] KALI GHOST SCRIPTS": "{{ t('rune_ghost') }}",
    "[ ᛋ ] ADVANCED SYN SCANNER": "{{ t('rune_adv_syn') }}",
    "[ ᛈ ] NETWORK SNIFFER (JAVA)": "{{ t('rune_java') }}",
    "[ ᛞ ] SNOOPDORK OSINT V3": "{{ t('rune_snoopdork') }}",
    "[ ᛇ ] PACKET INJECTOR": "{{ t('rune_packet') }}",
    "[ ᛗ ] MIMIR SCANNER": "{{ t('rune_mimir') }}",
    "[ ᛒ ] BIFROST GATEWAY": "{{ t('rune_bifrost') }}",
    "[ ᛊ ] SYSTEM OPERATIONS": "{{ t('sys_ops') }}",
    "[ 📦 ] DEPENDENCY MANAGER": "{{ t('dep_manager') }}",
    "ᛗ ARCHITECT OF THE SYSTEM ᛗ": "{{ t('architect') }}",
    "ᛈ SAVE LOG (.TXT)": "{{ t('save_log') }}",
    "ᛈ EXPORT DATA (.JSON)": "{{ t('export_data') }}",
    "[ ᚾ ] MISSING TOOL": "{{ t('missing_tool') }}",
    "INITIATE RITUAL (INSTALL)": "{{ t('initiate_ritual') }}",
    "ABORT": "{{ t('abort') }}",
    "CANCEL": "{{ t('cancel') }}",
    "START SCAN": "{{ t('start_scan') }}",
    "LAUNCH SCAN": "{{ t('launch_scan') }}",
    "EXECUTE RUNES": "{{ t('execute_runes') }}",
    "SYSTEM INITIALIZED. THE ROOTS ARE LISTENING...": "{{ t('sys_init') }}",
    
    # Javascript Replacements
    'statusDiv.innerText = ">> ERROR: A TARGET IP IS REQUIRED <<";': "statusDiv.innerText = t('err_target');",
    'statusDiv.innerText = ">> ERROR: A TARGET IP/DOMAIN IS REQUIRED FOR EREBUS <<";': "statusDiv.innerText = t('err_target_erebus');",
    'statusDiv.innerText = ">> ERROR: A TARGET IP IS REQUIRED FOR INJECTION <<";': "statusDiv.innerText = t('err_target_injection');",
    'statusDiv.innerText = ">> ERROR: A TARGET (IP/DOMAIN) IS REQUIRED <<";': "statusDiv.innerText = t('err_target');",
    'statusDiv.innerText = `>> WEAVING FATE WITH ADVANCED SYN SCAN ON [${target}]...`;': "statusDiv.innerText = t('weaving_syn', {target: target});",
    'statusDiv.innerText = `>> WEAVING FATE WITH EREBUS SCANNER ON [${target}]...`;': "statusDiv.innerText = t('weaving_erebus', {target: target});",
    'statusDiv.innerText = `>> INITIATING PACKET INJECTOR [${action.toUpperCase()}] ON INTERFACE [${interface}]...`;': "statusDiv.innerText = t('initiating_injector', {action: action.toUpperCase(), interface: interface});",
    'statusDiv.innerText = `>> INITIATING RITUAL FOR: ${tool.toUpperCase()}...`;': "statusDiv.innerText = t('initiating_ritual', {tool: tool.toUpperCase()});",
    'statusDiv.innerText = `>> CONSULTING THE ROOTS FOR: ${toolInfo ? toolInfo.name.toUpperCase() : toolName.toUpperCase()}...`;': "statusDiv.innerText = t('consulting_roots', {tool: toolInfo ? toolInfo.name.toUpperCase() : toolName.toUpperCase()});",
    'statusDiv.innerText = ">> FATE HAS BEEN WOVEN. OPERATION COMPLETE.";': "statusDiv.innerText = t('operation_complete');",
    'statusDiv.innerText = ">> RUNES CASTED. PACKET INJECTION COMPLETED.";': "statusDiv.innerText = t('injection_complete');",
    'statusDiv.innerText = ">> THE CHANT FAILED.";': "statusDiv.innerText = t('chant_failed');",
    'statusDiv.innerText = ">> THE CRAFTING FAILED.";': "statusDiv.innerText = t('crafting_failed');",
    'contentDiv.innerText = "RUNTIME ERROR: " + error;': "contentDiv.innerText = t('runtime_error') + error;"
}

for old, new in replacements.items():
    content = content.replace(old, new)

# Insert Language Selector
lang_selector = '''
        <div class="lang-selector" style="position: absolute; top: 20px; right: 20px; z-index: 100;">
            <button onclick="setLang('tr')" style="background: var(--bg-dark); color: {{ 'var(--highlight-color)' if current_lang == 'tr' else 'white' }}; border: 1px solid var(--accent-color); padding: 5px 10px; cursor: pointer;">🇹🇷 TR</button>
            <button onclick="setLang('en')" style="background: var(--bg-dark); color: {{ 'var(--highlight-color)' if current_lang == 'en' else 'white' }}; border: 1px solid var(--accent-color); padding: 5px 10px; cursor: pointer;">🇺🇸 EN</button>
        </div>
'''
if "class=\"lang-selector\"" not in content:
    content = content.replace('<div class="header-group">', lang_selector + '\n        <div class="header-group">')

# Insert JS translation helper
js_helper = '''
        const translations = {{ js_translations | tojson | safe }};
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
'''
if "function setLang(" not in content:
    content = content.replace('<script>', '<script>\n' + js_helper)

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Translations applied successfully.")
