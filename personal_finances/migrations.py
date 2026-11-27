"""Versioned, transactional migrations for the existing Personal Finances schema."""
import sqlite3

SCHEMA_VERSION = 2

def migrate(connection: sqlite3.Connection) -> None:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise RuntimeError(f"Database version {version} is newer than this application")
    if version == SCHEMA_VERSION:
        return
    # SQLite DDL is transactional. The existing v0.1 database may have
    # user_version=0, so CREATE IF NOT EXISTS preserves its data.
    with connection:
        if version < 1:
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
                                    'half-yearly',
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
                connection.execute("PRAGMA user_version = 1")
        if version < 2:
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
                connection.execute("PRAGMA user_version = 2")
