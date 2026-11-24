import sqlite3
import calendar

from pathlib import Path
from datetime import date, timedelta
from contextlib import closing


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "finances.db"


# ==================================================
# DATABASE CONNECTION
# ==================================================

def get_connection():

    connection = sqlite3.connect(DATABASE_PATH)

    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row

    return connection


# ==================================================
# DATABASE INITIALIZATION
# ==================================================

def initialize_database():

    with closing(get_connection()) as connection:
        with connection:

            connection.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    opening_balance_cents INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1
                        CHECK (is_active IN (0, 1))
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL
                        CHECK (type IN ('income', 'expense'))
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,

                    date TEXT NOT NULL,
                    description TEXT NOT NULL,

                    type TEXT NOT NULL
                        CHECK (type IN ('income', 'expense', 'transfer')),

                    amount_cents INTEGER NOT NULL
                        CHECK (amount_cents > 0),

                    category_id INTEGER,
                    from_account_id INTEGER,
                    to_account_id INTEGER,

                    FOREIGN KEY (category_id)
                        REFERENCES categories(id),

                    FOREIGN KEY (from_account_id)
                        REFERENCES accounts(id),

                    FOREIGN KEY (to_account_id)
                        REFERENCES accounts(id),

                    CHECK (
                        (
                            type = 'income'
                            AND to_account_id IS NOT NULL
                            AND from_account_id IS NULL
                            AND category_id IS NOT NULL
                        )
                        OR
                        (
                            type = 'expense'
                            AND from_account_id IS NOT NULL
                            AND to_account_id IS NULL
                            AND category_id IS NOT NULL
                        )
                        OR
                        (
                            type = 'transfer'
                            AND from_account_id IS NOT NULL
                            AND to_account_id IS NOT NULL
                            AND from_account_id != to_account_id
                            AND category_id IS NULL
                        )
                    )
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS contracts (
                    id INTEGER PRIMARY KEY,

                    name TEXT NOT NULL,

                    type TEXT NOT NULL
                        CHECK (type IN ('income', 'expense')),

                    amount_cents INTEGER NOT NULL
                        CHECK (amount_cents > 0),

                    category_id INTEGER NOT NULL,
                    account_id INTEGER NOT NULL,

                    frequency TEXT NOT NULL
                        CHECK (
                            frequency IN (
                                'weekly',
                                'monthly',
                                'quarterly',
                                'yearly'
                            )
                        ),

                    start_date TEXT NOT NULL,
                    end_date TEXT,
                    cancelled_on TEXT,

                    notes TEXT NOT NULL DEFAULT '',

                    FOREIGN KEY (category_id)
                        REFERENCES categories(id),

                    FOREIGN KEY (account_id)
                        REFERENCES accounts(id),

                    CHECK (
                        end_date IS NULL
                        OR end_date >= start_date
                    )
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS contract_payments (
                    id INTEGER PRIMARY KEY,

                    contract_id INTEGER NOT NULL,
                    due_date TEXT NOT NULL,

                    transaction_id INTEGER NOT NULL UNIQUE,

                    FOREIGN KEY (contract_id)
                        REFERENCES contracts(id),

                    FOREIGN KEY (transaction_id)
                        REFERENCES transactions(id)
                        ON DELETE CASCADE,

                    UNIQUE (contract_id, due_date)
                )
            """)

            # NEW: Contract price history.
            #
            # Every row defines a price that becomes valid
            # on a particular date.
            #
            # Different contracts can have different
            # numbers of price changes.

            connection.execute("""
                CREATE TABLE IF NOT EXISTS contract_prices (
                    id INTEGER PRIMARY KEY,

                    contract_id INTEGER NOT NULL,

                    amount_cents INTEGER NOT NULL
                        CHECK (amount_cents > 0),

                    valid_from TEXT NOT NULL,

                    FOREIGN KEY (contract_id)
                        REFERENCES contracts(id)
                        ON DELETE CASCADE,

                    UNIQUE (contract_id, valid_from)
                )
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_contract_prices_lookup

                ON contract_prices (
                    contract_id,
                    valid_from
                )
            """)

            # Migration:
            #
            # Existing contracts already have an amount
            # in contracts.amount_cents.
            #
            # Add that amount as their initial historical
            # price only when no price history exists.
            #
            # This can safely run multiple times.

            connection.execute("""
                INSERT INTO contract_prices (
                    contract_id,
                    amount_cents,
                    valid_from
                )

                SELECT
                    c.id,
                    c.amount_cents,
                    c.start_date

                FROM contracts AS c

                WHERE NOT EXISTS (
                    SELECT 1
                    FROM contract_prices AS p
                    WHERE p.contract_id = c.id
                )
            """)


# ==================================================
# ACCOUNTS
# ==================================================

def get_accounts(active_only=False):

    query = """
        SELECT
            id,
            name,
            opening_balance_cents,
            is_active

        FROM accounts
    """

    if active_only:
        query += " WHERE is_active = 1"

    query += " ORDER BY name"

    with closing(get_connection()) as connection:
        return connection.execute(query).fetchall()


def add_account(name, opening_balance_cents):

    with closing(get_connection()) as connection:
        with connection:

            connection.execute("""
                INSERT INTO accounts (
                    name,
                    opening_balance_cents
                )
                VALUES (?, ?)
            """, (name, opening_balance_cents))


def update_account(
    account_id,
    name,
    opening_balance_cents
):

    with closing(get_connection()) as connection:
        with connection:

            cursor = connection.execute("""
                UPDATE accounts

                SET
                    name = ?,
                    opening_balance_cents = ?

                WHERE id = ?
            """, (
                name,
                opening_balance_cents,
                account_id
            ))

            return cursor.rowcount == 1


def delete_account(account_id):

    with closing(get_connection()) as connection:
        with connection:

            cursor = connection.execute("""
                DELETE FROM accounts

                WHERE id = ?

                  AND NOT EXISTS (
                      SELECT 1
                      FROM transactions
                      WHERE from_account_id = accounts.id
                         OR to_account_id = accounts.id
                  )

                  AND NOT EXISTS (
                      SELECT 1
                      FROM contracts
                      WHERE account_id = accounts.id
                  )
            """, (account_id,))

            return cursor.rowcount == 1


def get_account_balances(as_of_date):

    with closing(get_connection()) as connection:

        return connection.execute("""
            SELECT
                a.id,
                a.name,
                a.is_active,
                a.opening_balance_cents,

                a.opening_balance_cents
                + COALESCE(SUM(
                    CASE
                        WHEN t.to_account_id = a.id
                            THEN t.amount_cents

                        WHEN t.from_account_id = a.id
                            THEN -t.amount_cents

                        ELSE 0
                    END
                ), 0) AS balance_cents

            FROM accounts AS a

            LEFT JOIN transactions AS t

                ON (
                    t.from_account_id = a.id
                    OR t.to_account_id = a.id
                )

                AND t.date <= ?

            GROUP BY a.id

            ORDER BY a.name
        """, (as_of_date,)).fetchall()


# ==================================================
# CATEGORIES
# ==================================================

def get_categories():

    with closing(get_connection()) as connection:

        return connection.execute("""
            SELECT
                id,
                name,
                type

            FROM categories

            ORDER BY name
        """).fetchall()


def add_category(name, category_type):

    with closing(get_connection()) as connection:
        with connection:

            connection.execute("""
                INSERT INTO categories (
                    name,
                    type
                )
                VALUES (?, ?)
            """, (name, category_type))


def update_category(
    category_id,
    name,
    category_type
):

    with closing(get_connection()) as connection:
        with connection:

            existing = connection.execute("""
                SELECT type
                FROM categories
                WHERE id = ?
            """, (category_id,)).fetchone()

            if existing is None:
                return False

            if existing["type"] != category_type:

                used = connection.execute("""
                    SELECT
                        EXISTS (
                            SELECT 1
                            FROM transactions
                            WHERE category_id = ?
                        )
                        OR
                        EXISTS (
                            SELECT 1
                            FROM contracts
                            WHERE category_id = ?
                        ) AS is_used
                """, (
                    category_id,
                    category_id
                )).fetchone()

                if used["is_used"]:
                    raise ValueError(
                        "Cannot change the type of a "
                        "category already in use"
                    )

            cursor = connection.execute("""
                UPDATE categories

                SET
                    name = ?,
                    type = ?

                WHERE id = ?
            """, (
                name,
                category_type,
                category_id
            ))

            return cursor.rowcount == 1


def delete_category(category_id):

    with closing(get_connection()) as connection:
        with connection:

            cursor = connection.execute("""
                DELETE FROM categories

                WHERE id = ?

                  AND NOT EXISTS (
                      SELECT 1
                      FROM transactions
                      WHERE category_id = categories.id
                  )

                  AND NOT EXISTS (
                      SELECT 1
                      FROM contracts
                      WHERE category_id = categories.id
                  )
            """, (category_id,))

            return cursor.rowcount == 1


# ==================================================
# TRANSACTIONS
# ==================================================

def get_transactions(
    month=None,
    sort_by="date",
    order="desc"
):

    allowed_columns = {
        "date": "t.date",
        "description": "t.description",
        "category": "c.name",
        "account": "COALESCE(a.name, b.name)",
        "amount": "t.amount_cents",
        "type": "t.type"
    }

    column = allowed_columns.get(
        sort_by,
        "t.date"
    )

    direction = (
        "ASC" if order == "asc" else "DESC"
    )

    query = """
        SELECT
            t.id,
            t.date,
            t.description,
            t.type,
            t.amount_cents,

            t.category_id,
            t.from_account_id,
            t.to_account_id,

            c.name AS category,
            a.name AS from_account,
            b.name AS to_account

        FROM transactions AS t

        LEFT JOIN categories AS c
            ON t.category_id = c.id

        LEFT JOIN accounts AS a
            ON t.from_account_id = a.id

        LEFT JOIN accounts AS b
            ON t.to_account_id = b.id
    """

    parameters = []

    if month:

        query += """
            WHERE substr(t.date, 1, 7) = ?
        """

        parameters.append(month)

    query += (
        f" ORDER BY {column} {direction}, t.id DESC"
    )

    with closing(get_connection()) as connection:

        return connection.execute(
            query,
            parameters
        ).fetchall()


def save_transaction(
    transaction_date,
    description,
    transaction_type,
    amount_cents,
    category_id,
    from_account_id,
    to_account_id,
    transaction_id=None
):

    with closing(get_connection()) as connection:
        with connection:

            parameters = (
                transaction_date,
                description,
                transaction_type,
                amount_cents,
                category_id,
                from_account_id,
                to_account_id
            )

            if transaction_id is None:

                cursor = connection.execute("""
                    INSERT INTO transactions (
                        date,
                        description,
                        type,
                        amount_cents,
                        category_id,
                        from_account_id,
                        to_account_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, parameters)

                return cursor.lastrowid

            cursor = connection.execute("""
                UPDATE transactions

                SET
                    date = ?,
                    description = ?,
                    type = ?,
                    amount_cents = ?,
                    category_id = ?,
                    from_account_id = ?,
                    to_account_id = ?

                WHERE id = ?

                  AND id NOT IN (
                      SELECT transaction_id
                      FROM contract_payments
                  )
            """, (
                *parameters,
                transaction_id
            ))

            if cursor.rowcount != 1:
                raise ValueError(
                    "Transaction not found or linked "
                    "to a contract payment"
                )

            return transaction_id


def delete_transaction(transaction_id):

    with closing(get_connection()) as connection:
        with connection:

            connection.execute("""
                DELETE FROM contract_payments
                WHERE transaction_id = ?
            """, (transaction_id,))

            cursor = connection.execute("""
                DELETE FROM transactions
                WHERE id = ?
            """, (transaction_id,))

            return cursor.rowcount == 1


# ==================================================
# DASHBOARD CALCULATIONS
# ==================================================

def get_monthly_summary(month, as_of_date):

    with closing(get_connection()) as connection:

        return connection.execute("""
            SELECT

                COALESCE(SUM(
                    CASE
                        WHEN type = 'income'
                        THEN amount_cents
                        ELSE 0
                    END
                ), 0) AS income_cents,

                COALESCE(SUM(
                    CASE
                        WHEN type = 'expense'
                        THEN amount_cents
                        ELSE 0
                    END
                ), 0) AS expenses_cents

            FROM transactions

            WHERE substr(date, 1, 7) = ?
              AND date <= ?

        """, (
            month,
            as_of_date
        )).fetchone()


def get_cumulative_saldo(as_of_date):

    with closing(get_connection()) as connection:

        result = connection.execute("""
            SELECT COALESCE(SUM(

                CASE
                    WHEN type = 'income'
                        THEN amount_cents

                    WHEN type = 'expense'
                        THEN -amount_cents

                    ELSE 0
                END

            ), 0) AS cumulative_saldo

            FROM transactions

            WHERE date <= ?
        """, (as_of_date,)).fetchone()

        return result["cumulative_saldo"]


# ==================================================
# MONTHLY REPORT
# ==================================================

def get_monthly_report(
    sort_by="month",
    order="desc"
):

    allowed_columns = {
        "month": "month",
        "income": "income_cents",
        "expenses": "expenses_cents",
        "saldo": "saldo_cents",
        "cumulative": "cumulative_cents"
    }

    column = allowed_columns.get(
        sort_by,
        "month"
    )

    direction = (
        "ASC" if order == "asc" else "DESC"
    )

    query = f"""
        WITH monthly AS (

            SELECT
                substr(date, 1, 7) AS month,

                SUM(
                    CASE
                        WHEN type = 'income'
                        THEN amount_cents
                        ELSE 0
                    END
                ) AS income_cents,

                SUM(
                    CASE
                        WHEN type = 'expense'
                        THEN amount_cents
                        ELSE 0
                    END
                ) AS expenses_cents

            FROM transactions

            WHERE date <= date('now', 'localtime')

            GROUP BY substr(date, 1, 7)
        ),

        summary AS (

            SELECT
                month,
                income_cents,
                expenses_cents,

                income_cents - expenses_cents
                    AS saldo_cents

            FROM monthly
        ),

        report AS (

            SELECT
                *,

                SUM(saldo_cents) OVER (
                    ORDER BY month
                ) AS cumulative_cents

            FROM summary
        )

        SELECT *
        FROM report

        ORDER BY {column} {direction}, month DESC
    """

    with closing(get_connection()) as connection:

        return connection.execute(query).fetchall()


# ==================================================
# CONTRACTS
# ==================================================

def get_contracts(
    sort_by="name",
    order="asc"
):

    allowed_columns = {
        "name": "ct.name",
        "type": "ct.type",
        "amount": "current_amount_cents",
        "category": "cat.name",
        "account": "a.name",
        "frequency": "ct.frequency",
        "start": "ct.start_date",
        "end": "ct.end_date"
    }

    column = allowed_columns.get(
        sort_by,
        "ct.name"
    )

    direction = (
        "ASC" if order == "asc" else "DESC"
    )

    query = f"""
        SELECT
            ct.*,

            cat.name AS category,
            a.name AS account,

            COALESCE(
                (
                    SELECT p.amount_cents
                    FROM contract_prices AS p

                    WHERE p.contract_id = ct.id
                      AND p.valid_from <= date('now', 'localtime')

                    ORDER BY p.valid_from DESC
                    LIMIT 1
                ),

                ct.amount_cents
            ) AS current_amount_cents

        FROM contracts AS ct

        JOIN categories AS cat
            ON ct.category_id = cat.id

        JOIN accounts AS a
            ON ct.account_id = a.id

        ORDER BY {column} {direction}, ct.id DESC
    """

    with closing(get_connection()) as connection:

        return connection.execute(query).fetchall()


def get_contract(contract_id):

    with closing(get_connection()) as connection:

        return connection.execute("""
            SELECT *
            FROM contracts
            WHERE id = ?
        """, (contract_id,)).fetchone()


def save_contract(
    name,
    contract_type,
    amount_cents,
    category_id,
    account_id,
    frequency,
    start_date,
    end_date,
    notes,
    contract_id=None
):

    with closing(get_connection()) as connection:
        with connection:

            if contract_id is None:

                cursor = connection.execute("""
                    INSERT INTO contracts (
                        name,
                        type,
                        amount_cents,
                        category_id,
                        account_id,
                        frequency,
                        start_date,
                        end_date,
                        notes
                    )

                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    contract_type,
                    amount_cents,
                    category_id,
                    account_id,
                    frequency,
                    start_date,
                    end_date,
                    notes
                ))

                new_contract_id = cursor.lastrowid

                # Store the initial contract price.

                connection.execute("""
                    INSERT INTO contract_prices (
                        contract_id,
                        amount_cents,
                        valid_from
                    )

                    VALUES (?, ?, ?)
                """, (
                    new_contract_id,
                    amount_cents,
                    start_date
                ))

                return new_contract_id

            # Editing a contract does NOT change its price.
            #
            # Price changes are handled separately through
            # the contract_prices table.

            existing = connection.execute("""
                SELECT
                    id,
                    start_date

                FROM contracts

                WHERE id = ?
            """, (contract_id,)).fetchone()

            if existing is None:
                raise ValueError("Contract not found")

            # Existing confirmed payments must retain their
            # historical interpretation. For this version,
            # changing the initial date or frequency is
            # disallowed after a payment has been confirmed.

            payment_exists = connection.execute("""
                SELECT 1

                FROM contract_payments

                WHERE contract_id = ?

                LIMIT 1
            """, (contract_id,)).fetchone()

            if payment_exists:

                previous = connection.execute("""
                    SELECT
                        frequency,
                        start_date

                    FROM contracts

                    WHERE id = ?
                """, (contract_id,)).fetchone()

                if (
                    frequency != previous["frequency"]
                    or start_date != previous["start_date"]
                ):
                    raise ValueError(
                        "Cannot change the payment schedule "
                        "after payments have been confirmed"
                    )

            earliest_price = connection.execute("""
                SELECT MIN(valid_from) AS earliest

                FROM contract_prices

                WHERE contract_id = ?
            """, (contract_id,)).fetchone()

            if (
                earliest_price["earliest"] is not None
                and start_date > earliest_price["earliest"]
            ):
                raise ValueError(
                    "Start date cannot be later than "
                    "an existing price history entry"
                )

            cursor = connection.execute("""
                UPDATE contracts

                SET
                    name = ?,
                    type = ?,
                    category_id = ?,
                    account_id = ?,
                    frequency = ?,
                    start_date = ?,
                    end_date = ?,
                    notes = ?

                WHERE id = ?
            """, (
                name,
                contract_type,
                category_id,
                account_id,
                frequency,
                start_date,
                end_date,
                notes,
                contract_id
            ))

            return contract_id


def cancel_contract(
    contract_id,
    cancellation_date
):

    with closing(get_connection()) as connection:
        with connection:

            cursor = connection.execute("""
                UPDATE contracts

                SET cancelled_on = ?

                WHERE id = ?
                  AND cancelled_on IS NULL
            """, (
                cancellation_date,
                contract_id
            ))

            return cursor.rowcount == 1


def delete_contract(contract_id):

    with closing(get_connection()) as connection:
        with connection:

            # Remove links to confirmed transactions,
            # but preserve the transactions themselves.

            connection.execute("""
                DELETE FROM contract_payments
                WHERE contract_id = ?
            """, (contract_id,))

            # Price history is automatically removed
            # through ON DELETE CASCADE.

            cursor = connection.execute("""
                DELETE FROM contracts
                WHERE id = ?
            """, (contract_id,))

            return cursor.rowcount == 1


# ==================================================
# CONTRACT PRICE HISTORY
# ==================================================

def get_contract_prices(contract_id):

    with closing(get_connection()) as connection:

        return connection.execute("""
            SELECT
                id,
                contract_id,
                amount_cents,
                valid_from

            FROM contract_prices

            WHERE contract_id = ?

            ORDER BY valid_from ASC
        """, (contract_id,)).fetchall()


def get_price_for_date(
    contract_id,
    payment_date
):

    with closing(get_connection()) as connection:

        result = connection.execute("""
            SELECT amount_cents

            FROM contract_prices

            WHERE contract_id = ?
              AND valid_from <= ?

            ORDER BY valid_from DESC

            LIMIT 1
        """, (
            contract_id,
            payment_date
        )).fetchone()

        if result is None:
            raise ValueError(
                "No contract price defined for this date"
            )

        return result["amount_cents"]


def set_contract_price(
    contract_id,
    amount_cents,
    valid_from
):

    with closing(get_connection()) as connection:
        with connection:

            contract = connection.execute("""
                SELECT
                    id,
                    start_date,
                    cancelled_on

                FROM contracts

                WHERE id = ?
            """, (contract_id,)).fetchone()

            if contract is None:
                raise ValueError("Contract not found")

            if valid_from < contract["start_date"]:
                raise ValueError(
                    "Price effective date cannot be "
                    "before the contract start date"
                )

            if contract["cancelled_on"]:
                raise ValueError(
                    "Cannot change the price of "
                    "a cancelled contract"
                )

            # A price change on an existing effective date
            # updates that historical price entry.
            #
            # Confirmed transactions are NOT modified.

            connection.execute("""
                INSERT INTO contract_prices (
                    contract_id,
                    amount_cents,
                    valid_from
                )

                VALUES (?, ?, ?)

                ON CONFLICT(contract_id, valid_from)
                DO UPDATE SET
                    amount_cents = excluded.amount_cents
            """, (
                contract_id,
                amount_cents,
                valid_from
            ))

            return True


# ==================================================
# CONTRACT PAYMENT DATE CALCULATIONS
# ==================================================

def advance_payment_date(
    start_date,
    frequency,
    occurrence
):

    if frequency == "weekly":

        return start_date + timedelta(
            weeks=occurrence
        )

    months = {
        "monthly": 1,
        "quarterly": 3,
        "yearly": 12
    }[frequency]

    total_month = (
        start_date.year * 12
        + start_date.month - 1
        + occurrence * months
    )

    year, month_index = divmod(
        total_month,
        12
    )

    month = month_index + 1

    if not 1 <= year <= 9999:
        raise ValueError(
            "Payment date outside supported range"
        )

    day = min(
        start_date.day,
        calendar.monthrange(year, month)[1]
    )

    return date(
        year,
        month,
        day
    )


def get_due_dates(contract, month):

    year, month_number = map(
        int,
        month.split("-")
    )

    period_start = date(
        year,
        month_number,
        1
    )

    period_end = date(
        year,
        month_number,
        calendar.monthrange(
            year,
            month_number
        )[1]
    )

    start = date.fromisoformat(
        contract["start_date"]
    )

    if contract["end_date"]:

        period_end = min(
            period_end,
            date.fromisoformat(
                contract["end_date"]
            )
        )

    if contract["cancelled_on"]:

        period_end = min(
            period_end,
            date.fromisoformat(
                contract["cancelled_on"]
            ) - timedelta(days=1)
        )

    if (
        period_end < start
        or period_end < period_start
    ):
        return []

    due_dates = []

    occurrence = 0

    while occurrence < 20000:

        try:

            due_date = advance_payment_date(
                start,
                contract["frequency"],
                occurrence
            )

        except (ValueError, OverflowError):
            break

        if due_date > period_end:
            break

        if due_date >= period_start:
            due_dates.append(
                due_date.isoformat()
            )

        occurrence += 1

    return due_dates


# ==================================================
# CONTRACT PAYMENT SCHEDULE
# ==================================================

def get_contract_schedule(month):

    contracts = get_contracts()

    with closing(get_connection()) as connection:

        payments = connection.execute("""
            SELECT
                cp.contract_id,
                cp.due_date,
                cp.transaction_id,
                t.amount_cents AS paid_amount_cents

            FROM contract_payments AS cp

            JOIN transactions AS t
                ON t.id = cp.transaction_id

            WHERE substr(cp.due_date, 1, 7) = ?
        """, (month,)).fetchall()

        prices = connection.execute("""
            SELECT
                contract_id,
                amount_cents,
                valid_from

            FROM contract_prices

            ORDER BY
                contract_id,
                valid_from
        """).fetchall()

    paid_lookup = {
        (p["contract_id"], p["due_date"]): p
        for p in payments
    }

    price_lookup = {}

    for price in prices:

        price_lookup.setdefault(
            price["contract_id"],
            []
        ).append(price)

    schedule = []

    for contract in contracts:

        contract_prices = price_lookup.get(
            contract["id"],
            []
        )

        for due_date in get_due_dates(
            contract,
            month
        ):

            matching_prices = [
                price
                for price in contract_prices
                if price["valid_from"] <= due_date
            ]

            if matching_prices:

                scheduled_amount = matching_prices[-1][
                    "amount_cents"
                ]

            else:

                scheduled_amount = contract[
                    "amount_cents"
                ]

            payment = paid_lookup.get(
                (contract["id"], due_date)
            )

            paid = payment is not None

            # Once confirmed, display the actual recorded
            # amount rather than the scheduled price.

            displayed_amount = (
                payment["paid_amount_cents"]
                if paid
                else scheduled_amount
            )

            schedule.append({
                "contract_id": contract["id"],
                "name": contract["name"],
                "type": contract["type"],
                "category": contract["category"],
                "account": contract["account"],
                "due_date": due_date,
                "scheduled_amount_cents": scheduled_amount,
                "amount_cents": displayed_amount,
                "paid": paid,
                "transaction_id": (
                    payment["transaction_id"]
                    if paid
                    else None
                )
            })

    schedule.sort(
        key=lambda item: (
            item["due_date"],
            item["name"]
        )
    )

    return schedule


# ==================================================
# CONFIRM CONTRACT PAYMENT
# ==================================================

def confirm_contract_payment(
    contract_id,
    due_date,
    override_amount_cents=None
):

    with closing(get_connection()) as connection:
        with connection:

            contract = connection.execute("""
                SELECT *
                FROM contracts
                WHERE id = ?
            """, (contract_id,)).fetchone()

            if contract is None:
                raise ValueError(
                    "Contract not found"
                )

            valid_dates = get_due_dates(
                contract,
                due_date[:7]
            )

            if due_date not in valid_dates:
                raise ValueError(
                    "Invalid scheduled payment date"
                )

            existing = connection.execute("""
                SELECT id

                FROM contract_payments

                WHERE contract_id = ?
                  AND due_date = ?
            """, (
                contract_id,
                due_date
            )).fetchone()

            if existing:
                raise ValueError(
                    "Payment already confirmed"
                )

            # Determine the price effective on this
            # specific payment date.

            price = connection.execute("""
                SELECT amount_cents

                FROM contract_prices

                WHERE contract_id = ?
                  AND valid_from <= ?

                ORDER BY valid_from DESC

                LIMIT 1
            """, (
                contract_id,
                due_date
            )).fetchone()

            if price is None:

                amount_cents = contract[
                    "amount_cents"
                ]

            else:

                amount_cents = price[
                    "amount_cents"
                ]

            # Optional one-time override.
            #
            # This affects the confirmed transaction,
            # not the contract's price history.

            if override_amount_cents is not None:

                if override_amount_cents <= 0:
                    raise ValueError(
                        "Payment amount must be positive"
                    )

                amount_cents = override_amount_cents

            from_account_id = None
            to_account_id = None

            if contract["type"] == "expense":

                from_account_id = contract[
                    "account_id"
                ]

            else:

                to_account_id = contract[
                    "account_id"
                ]

            cursor = connection.execute("""
                INSERT INTO transactions (
                    date,
                    description,
                    type,
                    amount_cents,
                    category_id,
                    from_account_id,
                    to_account_id
                )

                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                due_date,
                contract["name"],
                contract["type"],
                amount_cents,
                contract["category_id"],
                from_account_id,
                to_account_id
            ))

            transaction_id = cursor.lastrowid

            connection.execute("""
                INSERT INTO contract_payments (
                    contract_id,
                    due_date,
                    transaction_id
                )

                VALUES (?, ?, ?)
            """, (
                contract_id,
                due_date,
                transaction_id
            ))

            return transaction_id


# ==================================================
# DIRECT EXECUTION
# ==================================================

if __name__ == "__main__":

    initialize_database()

    print(
        "Database initialized successfully."
    )