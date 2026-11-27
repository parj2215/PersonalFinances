"""Consistent SQLite backups, with independent fortnightly and manual copies."""
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from .storage import BACKUP_DIR, DATABASE_PATH, prepare_storage

BACKUP_INTERVAL = timedelta(days=14)
NAME_PATTERN = re.compile(r"^(auto|manual)-\d{8}T\d{6}Z-[a-f0-9]{8}\.db$")

def list_backups():
    prepare_storage()
    result = []
    for path in BACKUP_DIR.iterdir():
        if path.is_file() and NAME_PATTERN.fullmatch(path.name):
            stat = path.stat()
            result.append({"name": path.name, "kind": path.name.split("-", 1)[0], "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "mtime": stat.st_mtime,})
    return sorted(result, key=lambda item: item["mtime"], reverse=True)

def create_backup(kind="manual"):
    if kind not in ("manual", "auto"):
        raise ValueError("Invalid backup type")
    prepare_storage()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{kind}-{timestamp}-{uuid4().hex[:8]}.db"
    destination = BACKUP_DIR / filename
    try:
        with sqlite3.connect(DATABASE_PATH, timeout=10) as source:
            with sqlite3.connect(destination) as target:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup integrity check failed")
        destination.chmod(0o600)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return filename

def maybe_create_automatic_backup():
    previous = [backup for backup in list_backups() if backup["kind"] == "auto"]
    last = datetime.fromtimestamp(previous[0]["mtime"], timezone.utc) if previous else None
    if last is None or datetime.now(timezone.utc) - last >= BACKUP_INTERVAL:
        return create_backup("auto")
    return None

def get_backup_path(filename):
    if not NAME_PATTERN.fullmatch(filename):
        raise ValueError("Invalid backup filename")
    path = BACKUP_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(filename)
    return path

def delete_backup(filename):
    get_backup_path(filename).unlink()
