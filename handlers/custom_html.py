import html

def handle_generate_dorks(target, data):
    if not target or target == 'none':
        return "<p style='color: red;'>Error: Target is required for Google Dorks.</p>"
        
    target_escaped = html.escape(str(target))
    dorks = [
        f"site:{target_escaped}",
        f"site:{target_escaped} inurl:admin",
        f"site:{target_escaped} inurl:login",
        f"site:{target_escaped} intitle:index of",
        f"site:{target_escaped} filetype:pdf",
        f"site:{target_escaped} filetype:sql",
        f"site:{target_escaped} inurl:wp-config.bak",
        f"site:{target_escaped} intext:'sql syntax near'",
        f"site:{target_escaped} inurl:dashboard"
    ]
    html_out = "<div style='display:flex; flex-wrap:wrap; gap:10px;'>"
    for d in dorks:
        url = f"https://www.google.com/search?q={d.replace(' ', '+')}"
        html_out += f"<a href='{url}' target='_blank' style='background:#333; padding:10px; color:#88c0d0; text-decoration:none; border:1px solid #4c566a;'>{d}</a>"
    html_out += "</div>"
    return html_out

def handle_wayback(target, data):
    if not target or target == 'none':
        return "Error: Target is required."
    target_escaped = html.escape(str(target))
    return f"Wayback Machine Link: https://web.archive.org/web/*/{target_escaped}"
