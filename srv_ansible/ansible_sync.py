#!/usr/bin/env python3
import os
import sys
import logging
import pathlib
import shutil
import subprocess


def setup_logger(log_file: str, name: str = "ansible_sync") -> logging.Logger:
    pathlib.Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # Avoid duplicate handlers if script is re-imported
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        fh = logging.FileHandler(log_file)
        fh.setFormatter(fmt)
        logger.addHandler(sh)
        logger.addHandler(fh)
    return logger


def wipe_directory(path: pathlib.Path, logger: logging.Logger) -> None:
    # Safety guard: never allow removing root or empty path
    resolved = path.resolve()
    if str(resolved) in ("/", ""):
        raise RuntimeError(f"Refusing to wipe unsafe path: {resolved}")
    if path.exists():
        logger.info("Wiping local path: %s", str(path))
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def main() -> int:
    # Env and defaults
    sync_log_file = os.environ.get("LOG_FILE", "/var/log/get_ansible_workspace.log")
    logger = setup_logger(sync_log_file, name="ansible_sync")
    # Avoid issues if workspace gets wiped while this runs
    try:
        os.chdir("/")
    except Exception:
        pass

    samba_server = os.environ.get("SAMBA_SERVER", "192.168.0.22")
    samba_share = os.environ.get("SAMBA_SHARE_NAME", "Share")
    workgroup = os.environ.get("WORKGROUP", "WORKGROUP")
    remote_path = os.environ.get("REMOTE_PATH", "it")
    local_path = pathlib.Path(os.environ.get("LOCAL_PATH", "/workspace"))

    samba_user = os.environ.get("SAMBA_USER", "")
    samba_password = os.environ.get("SAMBA_PASSWORD", "")
    smb_debug = os.environ.get("SMB_DEBUGLEVEL", "2")
    smb_protocol = os.environ.get("SMB_PROTOCOL", "SMB3")

    # Always wipe local workspace before syncing
    try:
        wipe_directory(local_path, logger)
    except Exception as e:
        logger.error("Failed to wipe local path %s: %s", str(local_path), e)
        return 1

    logger.info(
        "Syncing //%s/%s/%s -> %s", samba_server, samba_share, remote_path, str(local_path)
    )
    # Directory already recreated by wipe

    # smbclient command script: use '; ' separator for -c
    # smbclient expects multiple commands in a single string separated by ';'
    # Newlines are not reliably parsed when passed via -c
    cmd_list = [
        "pwd",
        "ls",
        f"cd \"{remote_path}\"",
        "prompt OFF",
        "recurse ON",
        f"lcd \"{local_path}\"",
        "mget *",
    ]
    cmds = "; ".join(cmd_list)

    if not samba_user or not samba_password:
        logger.warning(
            "Warning: SAMBA_USER/PASSWORD not set; trying anonymous if allowed"
        )

    logger.info(
        "smbclient connecting to //%s/%s as %s",
        samba_server,
        samba_share,
        samba_user if samba_user else "<anon>",
    )
    logger.info("smbclient commands: %s", cmds)

    cmd = [
        "smbclient",
        f"//{samba_server}/{samba_share}",
        "-d",
        str(smb_debug),
        "-k",
        "no",
        "-W",
        workgroup,
        "-m",
        smb_protocol,
    ]
    if samba_user or samba_password:
        cmd += ["-U", f"{samba_user}%{samba_password}"]
    else:
        cmd += ["-N"]
    cmd += ["-c", cmds]

    # Stream output to both stdout and log via logger
    def run_smbclient(args):
        try:
            p = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            logger.error("smbclient not found. Install smbclient in the image.")
            return 127
        assert p.stdout is not None
        for line in p.stdout:
            logger.info(line.rstrip("\n"))
        p.wait()
        return p.returncode

    rc = run_smbclient(cmd)
    logger.info("smbclient exit code: %s", rc)
    if rc != 0 and (samba_user or samba_password):
        logger.warning("Auth failed with provided credentials; retrying anonymously (-N) if share allows guests")
        cmd_noauth = [
            # keep anonymous attempt minimal; some servers behave differently
            "smbclient",
            f"//{samba_server}/{samba_share}",
            "-N",
            "-c",
            cmds,
        ]
        rc = run_smbclient(cmd_noauth)
        logger.info("smbclient (anonymous) exit code: %s", rc)
        if rc != 0:
            logger.warning("Anonymous auth failed; retrying as explicit guest user")
            cmd_guest = [
                "smbclient",
                f"//{samba_server}/{samba_share}",
                "-U",
                "guest%",
                "-c",
                cmds,
            ]
            rc = run_smbclient(cmd_guest)
            logger.info("smbclient (guest) exit code: %s", rc)
    if rc != 0:
        return rc
    logger.info("Done (via smbclient). Files are in %s", str(local_path))

    # After successful sync, run ansible playbooks and log to separate file
    ansible_log_file = os.environ.get("ANSIBLE_LOG_FILE", "/var/log/ansible_runner.log")
    runner = setup_logger(ansible_log_file, name="ansible_runner")

    inventory = local_path / "ansible" / "inventory" / "hosts.ini"
    playbook_dir = local_path / "ansible" / "playbooks"

    if not inventory.is_file():
        runner.info("Inventory not found at %s; skipping playbooks", str(inventory))
        return 0

    env = os.environ.copy()
    env.setdefault("HOME", "/root")
    env.setdefault("ANSIBLE_HOST_KEY_CHECKING", "False")

    ansible_password = os.environ.get("ANSIBLE_PASSWORD", "")

    def run_playbook(pb: pathlib.Path) -> int:
        if not pb.is_file():
            runner.info("Playbook not found: %s (skip)", str(pb))
            return 0
        cmd_pb = [
            "ansible-playbook",
            "-i",
            str(inventory),
            str(pb),
            "-u",
            "root",
        ]
        if ansible_password:
            cmd_pb += ["--extra-vars", f"ansible_password={ansible_password}"]
        try:
            p = subprocess.Popen(
                cmd_pb,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                cwd="/",
            )
        except FileNotFoundError:
            runner.error("ansible-playbook not found. Install ansible in the image.")
            return 127
        assert p.stdout is not None
        for line in p.stdout:
            runner.info(line.rstrip("\n"))
        p.wait()
        rc_pb = p.returncode
        runner.info("ansible-playbook %s exit code: %s", pb.name, rc_pb)
        return rc_pb

    # Execute healthcheck and stub sequentially; don't fail the whole run
    run_playbook(playbook_dir / "healthcheck.yml")
    run_playbook(playbook_dir / "stub.yml")

    return 0


if __name__ == "__main__":
    sys.exit(main())
