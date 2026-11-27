# Personal Finances

A local-first personal finance manager for Linux, built with Python, Flask, SQLite and a dark-themed web interface. Use it in your browser or in an optional Ubuntu desktop window. Your transactions and account data stay on your machine; no cloud account or external database is required.

## Features

- **Dashboard:** Choose a calendar month to see income, expenses, that month's saldo, cumulative saldo, and account balances.
- **Transactions:** Record, edit and delete income, expenses and transfers. Sort and filter records by month.
- **Accounts:** Create and manage accounts, opening balances and account status. Transfers change account balances without counting as income or expenses.
- **Categories:** Manage income and expense categories. Referenced categories and accounts have deletion restrictions.
- **Recurring contracts:** Schedule weekly, monthly, quarterly, half-yearly and yearly income or expense payments, optionally with an end date. Confirm a due payment to create its transaction; record price changes with effective dates and optionally override the amount actually paid.
- **Reports:** View monthly totals and chronological cumulative saldo with sorting options.
- **Backup management:** Create, download and delete consistent SQLite backups from Settings. An automatic backup is taken at launch when the previous automatic backup is at least 14 days old, or if none exists.
- **Local privacy:** SQLite files and the Flask session secret live outside the Git repository, in the user's application-data directory.

## Project layout

```text
Personal_finances/
├── app.py                         # Browser entry point
├── desktop.py                     # Optional native Ubuntu window
├── install_launcher.sh            # Installs a per-user .desktop launcher
├── personal_finances/             # Application package
│   ├── __init__.py
│   ├── app.py                     # Flask routes, forms, validation and API
│   ├── database.py                # Account, transaction, report and contract queries
│   ├── migrations.py              # SQLite schema and migration steps
│   ├── storage.py                 # Local data paths and legacy DB import
│   ├── backups.py                 # SQLite backup management
│   ├── templates/                 # Jinja pages and reusable dialogs
│   │   └── components/
│   └── static/
│       ├── main.js                # Forms, dialogs and API interactions
│       └── style.css              # UI theme and layout
├── tests/
│   └── test_finances.py           # Isolated finance/migration/backup tests
├── requirements.txt
├── .gitignore
├── LICENSE                       # Apache License 2.0
└── README.md
```

The repository intentionally contains **no** user database, backups, environment files, compiled Python files or virtual environment.

## Installation (Ubuntu/Linux)

Python 3 with `venv` and `pip` is required. For browser-only use, a GTK installation is not needed, although `requirements.txt` includes the optional `pywebview` package.

```bash
git clone <your-repository-url>
cd Personal_finances
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000**. Start the server only on localhost. `app.py` runs with Flask debug mode disabled.

To use the optional Ubuntu desktop window, install GTK/WebKit dependencies (package names may depend on the Ubuntu release):

```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
```

If `gi` is installed through Ubuntu system packages, recreate the virtual environment with `python3 -m venv --system-site-packages .venv` before installing requirements. Then start the app:

```bash
python desktop.py
```

For an application-menu launcher:

```bash
chmod +x install_launcher.sh
./install_launcher.sh
```

The launcher points to your current project directory and its `.venv`; reinstall it if you move the checkout.

## First use

1. Create your accounts and enter their opening balances under **Accounts**.
2. Add income and expense categories under **Settings**.
3. Record income, expenses and transfers under **Transactions**.
4. Add recurring payments under **Contracts**; confirm payments as they occur.
5. Use **Dashboard** and **Reports** for monthly figures and **Settings** for backups.

All amounts are stored as integer cents to avoid floating-point rounding in financial records.

### How the balances work

| Metric | Definition |
| --- | --- |
| Monthly income | Income transactions dated within the selected month |
| Monthly expenses | Expense transactions dated within the selected month |
| Monthly saldo | Monthly income minus monthly expenses; calculated independently for each month |
| Cumulative saldo | Total recorded income minus expenses up to the report cutoff, across months |
| Account balance | Account opening balance plus incoming transactions/transfers minus outgoing transactions/transfers |

Transfers are excluded from income, expenses and saldo. Monthly reporting uses **transaction dates**, not a separately configurable accounting month. A salary or rent transaction entered on the 26th belongs to the calendar month containing that date, even if it is intended for the following month. Account opening balances are not added to cumulative saldo.

## Data, migrations and backups

By default, the application stores private files here:

```text
~/.local/share/personal-finances/
├── finances.db
├── .flask_secret
└── backups/
    ├── auto-...db
    └── manual-...db
```

`XDG_DATA_HOME` can change the parent location. Set `PERSONAL_FINANCES_DATA_DIR` to use a specific directory, for example for a portable setup or tests:

```bash
PERSONAL_FINANCES_DATA_DIR=/path/to/private-data python app.py
```

On startup, the app initializes or migrates the database using SQLite's `user_version` (currently schema version 2). If an older `finances.db` is found next to the repository's `app.py`, it is copied **once** into the application-data directory when no destination database exists; the original is preserved. Back up your data before changing versions.

Backups use SQLite's backup API and are validated for integrity. Automatic backups are checked at launch, not by a constantly running scheduler; they are not a replacement for off-device backups. Deleting a backup in Settings removes that backup file. The SQLite database is **not encrypted**.

## Development and tests

Run tests from the repository root:

```bash
python -m unittest discover -s tests -v
python -m compileall -q personal_finances app.py desktop.py tests
node --check personal_finances/static/main.js  # Optional: requires Node.js
```

The Python tests use a temporary data directory and cover account/report arithmetic, scheduled payments, migration compatibility and backup operations. They do not yet cover the full Flask UI or a real Ubuntu desktop session.

### Git workflow

```bash
git init                           # Only if this isn't already a Git repository
git add .
git status                         # Confirm no financial data is being staged
git commit -m "Organize finance manager and document current features"
```

`.gitignore` excludes local databases and secret files. A file already committed to Git remains tracked even if added to `.gitignore`; remove it from the index with `git rm --cached <path>` without deleting the local copy. Never commit actual financial records, backups or session secrets.

## Current limitations

- Single-user local application; no multi-device sync or bank integration.
- Transactions are entered manually; recurring payments require confirmation.
- Calendar-month reporting; no separate accounting-period assignment.
- No built-in database encryption, duplicate detection or advanced budgeting charts.
- Desktop view requires a supported Linux graphical session and GTK/WebKit integration.

## License

Apache License 2.0; see [LICENSE](LICENSE).
