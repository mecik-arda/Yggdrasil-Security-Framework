#!/usr/bin/env python3
"""
Generate standalone ``pyproject.toml`` files for each Runes sub-project.

Run this from the repository root:
    python Runes/generate_packages.py

Each sub-project gets a minimal ``pyproject.toml`` that allows it to be
installed via ``pip install -e Runes/<project-name>`` or built as a wheel.
"""
import os
import json

RUNES_ROOT = os.path.dirname(os.path.abspath(__file__))

# Map each Rune directory to its metadata
# Add new sub-projects here as they are created
RUNE_PACKAGES = {
    "Advanced-SYN-Scanner": {
        "description": "Advanced SYN port scanner with evasion capabilities",
        "version": "0.1.0",
        "entry_point": "adv_syn_cli",
        "module": "adv_syn",
        "requires": ["scapy>=2.5.0"],
    },
    "bifrost-gateway": {
        "description": "Multi-protocol C2 gateway bridge",
        "version": "0.1.0",
        "entry_point": "bifrost",
        "module": "bifrost",
        "requires": [],
    },
    "erebus-scanner": {
        "description": "Dark-web oriented vulnerability scanner",
        "version": "0.1.0",
        "entry_point": "erebus",
        "module": "erebus_scanner",
        "requires": ["requests>=2.28", "beautifulsoup4>=4.11"],
    },
    "fenrir-hash-cracker": {
        "description": "GPU-accelerated hash cracker (CUDA/OpenCL fallback)",
        "version": "0.1.0",
        "entry_point": "fenrir",
        "module": "fenrir",
        "requires": [],
    },
    "Huginn-SecureTransfer": {
        "description": "Encrypted file transfer agent",
        "version": "0.1.0",
        "entry_point": "huginn",
        "module": "huginn",
        "requires": ["cryptography>=40.0"],
    },
    "Kali-Ghost-Scripts": {
        "description": "Ghost-mode operational scripts for Kali Linux",
        "version": "0.1.0",
        "requires": [],
    },
    "mimir-scanner": {
        "description": "Intelligence-gathering web reconnaissance scanner",
        "version": "0.1.0",
        "entry_point": "mimir",
        "module": "mimir_scanner",
        "requires": ["requests>=2.28", "dnspython>=2.3"],
    },
    "muninn-scanner": {
        "description": "Memory-based artifact collector and forensics scanner",
        "version": "0.1.0",
        "entry_point": "muninn",
        "module": "muninn_scanner",
        "requires": [],
    },
    "Network-Sniffer-Scanner-Java": {
        "description": "Java-based network packet sniffer and analyzer",
        "version": "0.1.0",
        "language": "java",
        "requires": [],
    },
    "packet-injector": {
        "description": "Low-level packet injection and crafting tool",
        "version": "0.1.0",
        "entry_point": "packet_injector_cli",
        "module": "packet_injector",
        "requires": ["scapy>=2.5.0"],
    },
    "sleipnir-scanner": {
        "description": "High-speed multi-threaded port and service scanner",
        "version": "0.1.0",
        "entry_point": "sleipnir",
        "module": "sleipnir_scanner",
        "requires": [],
    },
    "SnoopDork_V3": {
        "description": "Google dorking automation tool v3",
        "version": "3.0.0",
        "entry_point": "snoopdork",
        "module": "snoopdork",
        "requires": ["requests>=2.28"],
    },
}


def _generate_toml(name, meta):
    """Return the content of a pyproject.toml as a string."""
    requires = meta.get("requires", [])
    requires_str = json.dumps(requires) if requires else "[]"

    lines = [
        "[build-system]",
        'requires = ["setuptools>=64.0", "wheel"]',
        'build-backend = "setuptools.build_meta"',
        "",
        "[project]",
        f'name = "yggdrasil-{name.lower().replace(" ", "-")}"',
        f'version = "{meta["version"]}"',
        f'description = "{meta["description"]}"',
        'readme = "README.md"',
        "license = {text = \"MIT\"}",
        f"requires-python = \">=3.8\"",
        f'dependencies = {requires_str}',
        "",
    ]

    if meta.get("entry_point"):
        lines += [
            "[project.scripts]",
            f'{meta["entry_point"]} = "{meta["module"]}.__main__:main"',
            "",
        ]

    # Python package discovery
    lines += [
        "[tool.setuptools]",
        'packages = ["."]',
    ]

    return "\n".join(lines) + "\n"


def main():
    generated = 0
    skipped = 0

    for dir_name, meta in RUNE_PACKAGES.items():
        dir_path = os.path.join(RUNES_ROOT, dir_name)
        toml_path = os.path.join(dir_path, "pyproject.toml")

        if not os.path.isdir(dir_path):
            print(f"[SKIP] {dir_name} — directory not found")
            skipped += 1
            continue

        content = _generate_toml(dir_name, meta)
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Also ensure a minimal __init__.py exists
        init_path = os.path.join(dir_path, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w", encoding="utf-8") as f:
                f.write(f'"""{meta["description"]}"""\n')

        print(f"[OK]   {dir_name} → pyproject.toml (v{meta['version']})")
        generated += 1

    print(f"\nDone: {generated} generated, {skipped} skipped.")


if __name__ == "__main__":
    main()