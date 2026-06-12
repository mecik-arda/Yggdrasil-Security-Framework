import os

index_path = r'C:\Users\ardam\Desktop\Yggdrasil-Security-Framework\templates\index.html'

with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    # HTML Modal Replacements
    "Select missing dependencies to install. OS specific logic will be applied.": "{{ t('dep_desc') }}",
    "<th style=\"padding: 10px;\">Tool</th>": "<th style=\"padding: 10px;\">{{ t('dep_col_tool') }}</th>",
    "<th style=\"padding: 10px;\">Used For</th>": "<th style=\"padding: 10px;\">{{ t('dep_col_used_for') }}</th>",
    "<th style=\"padding: 10px;\">Status</th>": "<th style=\"padding: 10px;\">{{ t('dep_col_status') }}</th>",
    "<th style=\"padding: 10px;\">OS Support</th>": "<th style=\"padding: 10px;\">{{ t('dep_col_os') }}</th>",
    "INSTALL SELECTED": "{{ t('dep_install_selected') }}",
    "CLOSE</button>": "{{ t('dep_close') }}</button>",
    
    # JavaScript Replacements
    "btn.innerText = tool.name;": "btn.innerText = t(tool.name);",
    "Fetching dependencies...": "' + t('dep_fetching') + '",
    "Failed to fetch dependencies.": "' + t('dep_fetch_fail') + '",
    "'INSTALLED' : 'MISSING'": "t('dep_installed') : t('dep_missing')",
    "'NATIVE' : 'MANUAL/WSL'": "t('dep_native') : t('dep_manual')",
    "alert(\"Please select at least one missing dependency to install.\");": "alert(t('dep_err_select'));",
    "`INSTALLING: ${tool.toUpperCase()}`": "t('dep_installing') + tool.toUpperCase()",
    "`[SYSTEM] Requesting installation sequence for ${tool}...\\n`": "t('dep_req_seq') + tool + '...\\n'",
    "`\\n[SUCCESS] Sequence completed.\\n\\n${msg}`": "'\\n' + t('dep_success') + '\\n\\n' + msg",
    "`\\n[ERROR] Sequence failed.\\n\\n${msg}`": "'\\n' + t('dep_err_seq') + '\\n\\n' + msg",
    "`\\n[SYSTEM ERROR] Failed to connect: ${error}`": "'\\n' + t('dep_sys_err') + error",
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Dependency Manager translations applied successfully.")
