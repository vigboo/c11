#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def load_dotenv(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip()
        # Drop surrounding quotes if present
        if len(val) >= 2 and ((val[0] == val[-1]) and val[0] in ('"', "'")):
            val = val[1:-1]
        env[key] = val
    return env


def sha512_crypt_hash(password: str, rounds: int = 656000) -> str:
    """
    Returns a string like "$6$rounds=656000$<salt>$<hash>" using SHA512-CRYPT.
    Prefixed with {SHA512-CRYPT} by caller when writing to postfix file.
    Tries passlib first, then Python's crypt on Unix.
    """
    # Try passlib if available
    try:
        from passlib.hash import sha512_crypt as _sha512_crypt

        return _sha512_crypt.using(rounds=rounds).hash(password)
    except Exception:
        pass

    # Fallback to crypt (Linux/Unix). Not available on Windows.
    try:
        import crypt  # type: ignore

        # crypt.mksalt supports rounds for METHOD_SHA512
        try:
            salt = crypt.mksalt(crypt.METHOD_SHA512, rounds=rounds)  # type: ignore[arg-type]
        except TypeError:
            # Older Python: no rounds param
            salt = crypt.mksalt(crypt.METHOD_SHA512)
        return crypt.crypt(password, salt)
    except Exception as e:
        raise RuntimeError(
            "Unable to generate SHA512-CRYPT hash. Install 'passlib' or run on Linux with 'crypt' module."
        ) from e


def parse_accounts(lines: List[str]) -> List[Tuple[str, str]]:
    """Parse lines of postfix-accounts.cf into (email, rest_of_line) tuples.
    rest_of_line contains everything after the first '|', unchanged (may be empty)."""
    out: List[Tuple[str, str]] = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            out.append(("", ln))  # keep as-is (comments/empty)
            continue
        # expected format: email|password_hash[|...]
        if "|" not in s:
            out.append(("", ln))
            continue
        email, rest = s.split("|", 1)
        out.append((email.strip(), rest.strip()))
    return out


def env_key_for_email(email: str) -> str:
    local = email.split("@", 1)[0]
    norm = re.sub(r"[^A-Za-z0-9]", "_", local).upper()
    return f"{norm}_PASSWORD"


def main() -> int:
    here = Path(__file__).resolve().parent
    dotenv_path = here / ".env"
    postfix_path = here / "srv_mailcow" / "config" / "postfix-accounts.cf"

    env = load_dotenv(dotenv_path)
    if not env:
        print(f"Warning: .env not found or empty at {dotenv_path}", file=sys.stderr)

    if not postfix_path.exists():
        print(f"Error: postfix accounts file not found: {postfix_path}", file=sys.stderr)
        return 1

    orig_lines = postfix_path.read_text(encoding="utf-8", errors="replace").splitlines()
    parsed = parse_accounts(orig_lines)

    new_lines: List[str] = []
    changed = 0
    total_accounts = 0

    for email, rest in parsed:
        if not email:
            # passthrough (comments/empty or malformed line)
            new_lines.append(rest if rest.endswith("\n") else rest)
            continue

        total_accounts += 1
        key = env_key_for_email(email)
        pw = env.get(key)
        if pw is None or pw == "":
            # Keep existing line as-is
            new_lines.append(f"{email}|{rest}")
            continue

        # Generate new hash
        hashed = sha512_crypt_hash(pw)
        new_line = f"{email}|{{SHA512-CRYPT}}{hashed}"
        if new_line != f"{email}|{rest}":
            changed += 1
        new_lines.append(new_line)

    postfix_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    print(
        f"Synced passwords for {changed} of {total_accounts} account(s). Output: {postfix_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

