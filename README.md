# Personal Finances

A self-hosted, offline personal finance management application built with **Python, Flask, SQLite, HTML, CSS, and JavaScript**.

Personal Finances provides a simple way to manage income, expenses, bank accounts, recurring contracts, and financial reports through a clean, dark-mode web interface.

The application runs entirely on your local computer. No cloud services, external databases, subscriptions, or internet connection are required for normal operation.

## Features

### Dashboard

The dashboard provides an overview of your financial situation for a selected month.

- **Total Balance:** Combined balance of all accounts.
- **Monthly Income:** Total income recorded during the selected month.
- **Monthly Expenses:** Total expenses recorded during the selected month.
- **Monthly Saldo:** Monthly income minus monthly expenses.
- **Cumulative Saldo:** Running total of recorded income minus expenses.
- **Account Overview:** Individual balances of all accounts.
- **Quick Actions:** Buttons for adding transactions and contracts.

The selected month can be changed using the month selector.

Account balances are calculated from their opening balances and recorded transactions.

### Transaction Management

Create, view, edit, and delete financial transactions.

Three transaction types are supported:

| Type | Description |
|---|---|
| Income | Money received into an account |
| Expense | Money spent from an account |
| Transfer | Money transferred between two accounts |

Each transaction includes:

- Date
- Description
- Transaction type
- Amount
- Category
- Source account and/or destination account

Transactions can be filtered by month and sorted by date, description, type, category, account, or amount.

Income is displayed in green, expenses in red, and transfers in a neutral color.

**Transfers do not affect total income, expenses, or cumulative saldo.** They only change the balances of the involved accounts.

### Contract Management

Manage recurring income and expenses, such as rent, salaries, subscriptions, insurance, and other regular payments.

Supported payment frequencies:

- Weekly
- Monthly
- Quarterly
- Yearly

Each contract contains:

- Contract name
- Income or expense type
- Amount
- Category
- Account
- Payment frequency
- First payment date
- Optional end date
- Notes

Contracts can be edited or cancelled.

Contracts can also be permanently deleted, while preserving their previously confirmed financial transactions.

#### Payment Tracking

The application calculates scheduled payments for each month.

Payments can have the following statuses:

| Status | Meaning |
|---|---|
| Upcoming | Payment date is in the future |
| Pending | Payment date has arrived but has not been confirmed |
| Paid | Payment has been confirmed and recorded as a transaction |

Confirming a contract payment creates a financial transaction.

**Scheduled payments do not automatically affect account balances.** Only recorded transactions are included in financial calculations.

This prevents future payments from being counted as money already received or spent.

### Account Management

Manage multiple financial accounts, including:

- Bank accounts
- Credit card accounts
- PayPal
- Cash
- Other financial accounts

Each account has an opening balance.

Its calculated balance is:

```text
Current Balance =
    Opening Balance
    + Income
    - Expenses
    + Incoming Transfers
    - Outgoing Transfers
```

Accounts can be renamed, and their opening balances can be modified.

Unused accounts can be deleted. Accounts referenced by transactions or contracts cannot be deleted until those dependencies are resolved.

### Category Management

Create and manage custom income and expense categories.

Examples include:

**Income categories**
- Salary
- Refunds
- Gifts
- Other Income

**Expense categories**
- Rent
- Groceries
- Shopping
- Transportation
- Entertainment
- Insurance
- Subscriptions
- Other Expenses

Categories can be renamed or deleted when they are not referenced by existing financial records.

The type of a category cannot be changed while it is used by transactions or contracts.

### Financial Reports

The Reports page provides a monthly financial summary.

| Month | Income | Expenses | Monthly Saldo | Cumulative Saldo |
|---|---:|---:|---:|---:|
| September | €1,000 | €1,200 | -€200 | -€200 |
| October | €1,500 | €1,000 | +€500 | +€300 |
| November | €1,200 | €1,400 | -€200 | +€100 |

*The values above are illustrative.*

The report supports sorting by month, income, expenses, monthly saldo, and cumulative saldo.

Cumulative saldo is calculated chronologically, regardless of the displayed sorting order.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3 |
| Web framework | Flask |
| Database | SQLite |
| Frontend | HTML5 |
| Styling | CSS3 |
| Interactivity | JavaScript |
| Template engine | Jinja2 |
| Operating system | Ubuntu / Linux |
| Deployment | Localhost |

The application does not require Node.js, npm, Docker, or an external database server.

## Project Structure

```text
PersonalFinances/
│
├── app.py
├── database.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── transactions.html
│   ├── contracts.html
│   ├── accounts.html
│   ├── reports.html
│   ├── settings.html
│   │
│   └── components/
│       ├── transaction_modal.html
│       └── contract_modal.html
│
├── static/
│   ├── style.css
│   └── main.js
│
├── finances.db              # Generated locally, ignored by Git
├── .flask_secret             # Generated locally, ignored by Git
└── .venv/                    # Local Python environment, ignored by Git
```

## Installation

### 1. Requirements

The following software must be installed:

- Python 3
- Python virtual environment support
- pip
- A modern web browser

On Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### 2. Clone the Repository

```bash
git clone https://github.com/parj2215/PersonalFinances.git
cd PersonalFinances
```

### 3. Create a Virtual Environment

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Initialize the Database

```bash
python database.py
```

This creates the local SQLite database and initializes the required tables.

The database starts empty.

### 6. Start the Application

```bash
python app.py
```

Open the following address in your browser:

```text
http://127.0.0.1:5000
```

The application is now ready to use.

**Note:** Flask's built-in development server is intended for local development. The application should remain bound to `127.0.0.1` and must not be exposed directly to the internet.

## Usage

### Initial Setup

After installing the application:

1. Open the **Accounts** page and create your financial accounts.
2. Enter the opening balance of each account.
3. Open **Settings** and create your income and expense categories.
4. Add transactions through the Dashboard or Transactions page.
5. Add recurring contracts through the Dashboard or Contracts page.

The dashboard and reports automatically calculate financial totals from recorded transactions.

### Adding a Transaction

Click **+ Add Transaction**.

Select the transaction type and enter the required information.

The form automatically adjusts its account and category fields according to the selected type.

Click **Save Transaction** to store the transaction in SQLite.

### Adding a Contract

Click **+ Add Contract**.

Enter the contract details, including payment frequency and first payment date.

The application calculates scheduled payment dates.

When a payment occurs, open the Contracts page and confirm the corresponding payment.

This records the payment as a transaction.

### Editing and Deleting Records

Transactions, accounts, categories, and contracts provide management actions where supported.

Some deletion operations are restricted to preserve database integrity.

For example, an account cannot be deleted while it is referenced by transactions or contracts.

## Database Architecture

The application uses SQLite as its local relational database.

The main tables are:

| Table | Description |
|---|---|
| `accounts` | Financial accounts and opening balances |
| `categories` | Income and expense categories |
| `transactions` | Individual financial transactions |
| `contracts` | Recurring income and expense definitions |
| `contract_payments` | Links confirmed scheduled payments to transactions |

### Database Relationships

```text
accounts
   │
   ├─────────────┐
   │             │
   ▼             ▼
transactions   contracts
   ▲             │
   │             ▼
   │       contract_payments
   │             │
   └─────────────┘

categories
   │
   ├── transactions
   └── contracts
```

Foreign key constraints are used to maintain relationships between financial records.

### Monetary Values

Monetary amounts are stored as **integer cents**, rather than floating-point euro values.

For example:

| Amount | Stored value |
|---|---:|
| €0.01 | 1 |
| €10.00 | 1000 |
| €25.99 | 2599 |
| €100.50 | 10050 |

This avoids floating-point rounding errors during financial calculations.

### Transaction Dates

Dates are stored in ISO 8601 format:

```text
YYYY-MM-DD
```

Example:

```text
2026-11-24
```

This format allows chronological sorting and straightforward monthly filtering.

## Financial Calculations

### Monthly Saldo

```text
Monthly Saldo = Monthly Income - Monthly Expenses
```

Each month's saldo is calculated independently.

### Cumulative Saldo

```text
Cumulative Saldo =
    Sum of all recorded income
    - Sum of all recorded expenses
```

The cumulative saldo is calculated up to the selected reporting date.

Account opening balances are not included.

### Total Balance

```text
Total Balance =
    Sum of the calculated balances
    of all accounts
```

Unlike cumulative saldo, total balance includes account opening balances.

Consequently, total balance and cumulative saldo may differ.

### Transfers

Transfers move money between accounts without changing the combined total balance.

Transfers are excluded from income and expense calculations.

## Data Storage and Privacy

The application is designed to operate entirely offline.

All financial information is stored locally in:

```text
finances.db
```

No cloud account or subscription is required.

The application does not automatically upload financial records to external services.

### Important Security Notes

- The application does not currently provide user authentication.
- The SQLite database is not encrypted by the application.
- Anyone with sufficient access to the local database file may be able to read its contents.
- The application should only be run on a trusted computer.
- Flask's development server should not be exposed to external networks.
- Full-disk encryption and normal operating-system access controls are recommended for protecting locally stored data.

## Database Backup

Financial information is stored in the SQLite database.

Create backups regularly.

Stop the application before using the following simple backup procedure:

```bash
mkdir -p backups
```

```bash
cp finances.db "backups/finances_$(date +%Y-%m-%d_%H-%M-%S).db"
```

This creates a timestamped backup.

For example:

```text
backups/
├── finances_2026-11-24_14-00-00.db
└── finances_2026-11-25_18-30-00.db
```

For additional protection, backups should also be stored on another device.

### Restoring a Backup

Stop the application.

Replace the current database with a backup:

```bash
cp backups/finances_YYYY-MM-DD_HH-MM-SS.db finances.db
```

Restart the application.

**Warning:** Restoring a backup replaces the current database contents.

## Resetting the Application

To permanently delete all financial records and start with an empty database:

**1. Stop the application.**

Press `Ctrl+C` in the terminal running Flask.

**2. Remove the database and associated SQLite files.**

```bash
rm -f finances.db finances.db-wal finances.db-shm
```

**3. Reinitialize the database.**

```bash
python database.py
```

**4. Restart the application.**

```bash
python app.py
```

This removes all accounts, categories, transactions, contracts, and confirmed payments.

The application source code and configuration remain unchanged.

**Warning:** This operation permanently deletes the local financial records unless a backup exists.

## Git and Data Protection

The repository is intended to contain application source code only.

The `.gitignore` file excludes:

- SQLite databases
- Database backups
- Python virtual environments
- Python cache files
- Local secrets
- Environment variables
- Personal spreadsheet files
- Exported financial data

Before committing, verify the staged files:

```bash
git status
```

You can also inspect tracked files:

```bash
git ls-files
```

Personal financial records should never be committed to the repository.

## Current Limitations

The application currently has several limitations:

1. **Single-user application:** No multi-user authentication or permissions system.
2. **Offline only:** No automatic synchronization between computers.
3. **Manual payment confirmation:** Recurring payments must be confirmed before being recorded.
4. **No bank integration:** Transactions are entered manually.
5. **No automatic backups:** Backups must be created separately.
6. **No application-level encryption:** SQLite data is stored without encryption.
7. **Limited contract history management:** Changes to a contract's recurrence settings may affect the representation of previously scheduled payments.
8. **No automatic duplicate detection:** Manually entered transactions may duplicate confirmed contract payments.
9. **Calendar-based reporting:** Monthly saldo currently uses transaction dates rather than a separate accounting-period field.

## Planned Improvements

Potential future developments include:

- [ ] Import transactions and contracts from ODS spreadsheets
- [ ] CSV and ODS export
- [ ] Advanced transaction search and filtering
- [ ] Spending charts and category breakdowns
- [ ] Monthly budget limits
- [ ] Recurring payment reminders
- [ ] Improved contract payment reconciliation
- [ ] Automatic database backups
- [ ] Account and category editing dialogs
- [ ] Separate transaction dates and accounting periods
- [ ] Database migration system
- [ ] Automated tests
- [ ] Ubuntu desktop launcher
- [ ] Optional encrypted data storage
- [ ] Optional synchronization between devices

## Development

The application is developed using Python and Flask.

To start a development session:

```bash
cd PersonalFinances
source .venv/bin/activate
python app.py
```

During development, Flask's debug mode can be enabled locally to automatically reload the application after Python code changes.

Debug mode must be disabled for normal use.

### Main Source Files

**`app.py`**

Contains Flask routes, API endpoints, request validation, and application initialization.

**`database.py`**

Contains SQLite queries, database initialization, account balance calculations, transaction management, contract management, and financial reporting logic.

**`templates/`**

Contains Jinja2 templates for the different application pages.

**`static/style.css`**

Defines the dark-mode theme, responsive layout, tables, forms, dialogs, and other visual elements.

**`static/main.js`**

Handles frontend interactions, modal dialogs, asynchronous API requests, and record-management actions.

## License

No license has been specified for this repository.

Unless a license is added, the source code remains subject to the copyright holder's default rights.

---

**Personal Finances** — A local, privacy-focused personal finance manager built with Python, Flask, and SQLite.
