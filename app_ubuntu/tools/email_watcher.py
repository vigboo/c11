#!/usr/bin/env python3
import email
import imaplib
import os
import re
import sys
import subprocess
from pathlib import Path

IMAP_HOST = os.getenv("MAIL_IMAP_HOST", "192.168.0.20")
IMAP_PORT = int(os.getenv("MAIL_IMAP_PORT", "143"))
MAIL_USER = os.getenv("MAIL_USER", "b.anna@darkstore.local")

MAIL_PASS = os.getenv("B_ANNA_PASSWORD")

HOME = Path(os.environ.get("HOME", f"/home/{MAIL_USER.split('@')[0]}"))
DOWNLOAD_DIR = HOME  # save to home per requirement
LOG = Path("/var/log/email_watcher.log")

ARCHIVE_EXTS = {".zip", ".7z"}
ARCHIVE_MIMES = {
    "application/zip",
    "application/x-zip-compressed",
    "application/x-7z-compressed",
}

def log(msg: str):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8", errors="ignore") as fh:
            fh.write(msg + "\n")
    except Exception:
        pass


def find_password(text: str) -> str | None:
    # Look for 'пароль: <value>' till EOL, case-insensitive, allow spaces
    m = re.search(r"пароль\s*:\s*(.+)", text, flags=re.IGNORECASE)
    if m:
        # strip trailing whitespace
        return m.group(1).strip()
    return None


def extract_all_text(msg: email.message.Message) -> str:
    parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype in ("text/plain", "text/html"):
                try:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    parts.append(payload.decode(charset, errors="ignore"))
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True) or b""
            charset = msg.get_content_charset() or "utf-8"
            parts.append(payload.decode(charset, errors="ignore"))
        except Exception:
            pass
    return "\n".join(parts)


def is_archive_part(part: email.message.Message, filename: str | None) -> bool:
    if not filename:
        return False
    name = filename.lower()
    if any(name.endswith(ext) for ext in ARCHIVE_EXTS):
        return True
    ctype = (part.get_content_type() or "").lower()
    if ctype in ARCHIVE_MIMES:
        return True
    return False


def save_part_to_file(part: email.message.Message, path: Path) -> None:
    data = part.get_payload(decode=True) or b""
    path.write_bytes(data)


def extract_with_7z(archive: Path, password: str, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "7z",
        "x",
        "-y",
        f"-p{password}",
        f"-o{str(outdir)}",
        str(archive),
    ]
    # hide password from env
    env = os.environ.copy()
    env.pop("B_ANNA_PASSWORD", None)
    env.pop("B.ANNA_PASSWORD", None)
    env.pop("APP_UBUNTU_PASSWORD", None)
    subprocess.run(cmd, check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def find_agent_py(base: Path) -> Path | None:
    for p in base.rglob("agent.py"):
        return p
    return None


def run_agent_background(agent_path: Path) -> None:
    try:
        subprocess.Popen(
            ["python3", str(agent_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        log(f"Failed to start agent.py: {e}")


def main() -> int:
    pw = MAIL_PASS
    if not pw:
        # Try password file in home
        pw_file = HOME / ".imap_pass"
        try:
            pw = pw_file.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            pw = None
    if not pw:
        log("No mailbox password available (env or ~/.imap_pass)")
        return 1
    try:
        imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        imap.login(MAIL_USER, pw)
        imap.select("INBOX")
        typ, data = imap.search(None, "UNSEEN")
        if typ != "OK":
            log(f"IMAP search failed: {typ}")
            return 1
        ids = data[0].split()
        if not ids:
            return 0
        for msg_id in ids:
            try:
                t, d = imap.fetch(msg_id, "(RFC822)")
                if t != "OK":
                    continue
                raw = d[0][1]
                msg = email.message_from_bytes(raw)
                text = extract_all_text(msg)
                pwd = find_password(text) or ""
                saved = []
                for part in msg.walk():
                    fname = part.get_filename()
                    if is_archive_part(part, fname):
                        name = fname or "archive.bin"
                        dst = DOWNLOAD_DIR / name
                        save_part_to_file(part, dst)
                        saved.append(dst)
                # Try to extract each saved archive
                for arch in saved:
                    try:
                        outdir = DOWNLOAD_DIR / (arch.stem + "_extracted")
                        extract_with_7z(arch, pwd, outdir)
                        agent = find_agent_py(outdir)
                        if agent:
                            run_agent_background(agent)
                            log(f"Started agent from {agent}")
                    except subprocess.CalledProcessError:
                        log(f"Extraction failed for {arch}")
                # mark as seen
                imap.store(msg_id, '+FLAGS', '\\Seen')
            except Exception as e:
                log(f"Process message error: {e}")
                continue
        imap.logout()
        return 0
    except Exception as e:
        log(f"IMAP error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
