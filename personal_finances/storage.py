"""Ubuntu/XDG application paths with an override for tests and portable setups."""
import os
from pathlib import Path
import sqlite3

APP_DATA_DIR = Path(os.environ.get("PERSONAL_FINANCES_DATA_DIR") or (Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "personal-finances")).expanduser().resolve()
DATABASE_PATH = APP_DATA_DIR / "finances.db"
BACKUP_DIR = APP_DATA_DIR / "backups"
SECRET_PATH = APP_DATA_DIR / ".flask_secret"

def prepare_storage() -> None:
    APP_DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)

    legacy = Path(__file__).resolve().parent.parent / "finances.db"                 # One-time relocation from the original source directory.

    if legacy.is_file() and not DATABASE_PATH.exists():
        with sqlite3.connect(legacy) as source, sqlite3.connect(DATABASE_PATH) as target:
            source.backup(target)

    DATABASE_PATH.touch(mode=0o600, exist_ok=True)
    DATABASE_PATH.chmod(0o600)
