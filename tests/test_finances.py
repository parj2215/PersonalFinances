"""Run with: python -m unittest discover -s tests -v"""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

# Set an isolated data dir before importing any application modules.
_TMP = tempfile.TemporaryDirectory(prefix="finances-tests-")
os.environ["PERSONAL_FINANCES_DATA_DIR"] = _TMP.name

from personal_finances import database as db
from personal_finances import backups
from personal_finances.migrations import migrate
from personal_finances.storage import DATABASE_PATH

class FinanceTests(unittest.TestCase):
    def setUp(self):
        db.initialize_database()

        with db.get_connection() as conn:
            conn.execute("DELETE FROM contract_payments")
            conn.execute("DELETE FROM contracts")
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM categories")
            conn.execute("DELETE FROM accounts")

        db.add_account("Checking", 10000)
        db.add_account("Savings", 0)
        db.add_category("Salary", "income")
        db.add_category("Rent", "expense")

        with db.get_connection() as conn:
            self.account = conn.execute("SELECT id FROM accounts WHERE name='Checking'").fetchone()[0]
            self.savings = conn.execute("SELECT id FROM accounts WHERE name='Savings'").fetchone()[0]
            self.income = conn.execute("SELECT id FROM categories WHERE name='Salary'").fetchone()[0]
            self.expense = conn.execute("SELECT id FROM categories WHERE name='Rent'").fetchone()[0]

    def test_balances_monthly_and_cumulative(self):
        db.save_transaction("2026-11-01", "Salary", "income", 200000, self.income, None, self.account)
        db.save_transaction("2026-11-02", "Rent", "expense", 80000, self.expense, self.account, None)
        db.save_transaction("2026-11-03", "Transfer", "transfer", 15000, None, self.account, self.savings)

        self.assertEqual(db.get_cumulative_saldo("2026-11-30"), 120000)
        summary = db.get_monthly_summary("2026-11", "2026-11-30")
        self.assertEqual((summary["income_cents"], summary["expenses_cents"]), (200000, 80000))
        balances = {r["name"]: r["balance_cents"] for r in db.get_account_balances("2026-11-30")}
        self.assertEqual(balances, {"Checking": 115000, "Savings": 15000})
        self.assertEqual(db.get_monthly_summary("2026-12", "2026-12-31")["income_cents"], 0)

    def test_half_yearly_end_date_and_price_override(self):
        contract = db.save_contract("Insurance", "expense", 12000, self.expense, self.account, "half-yearly", "2026-01-31", "2027-01-31", "")

        db.set_contract_price(contract, 15000, "2026-07-01")

        self.assertEqual([r["due_date"] for r in db.get_contract_schedule("2026-07")], ["2026-07-31"])
        due = db.get_contract_schedule("2026-07")[0]
        self.assertEqual(due["scheduled_amount_cents"], 15000)
        txid = db.confirm_contract_payment(contract, "2026-07-31", 14750)
        self.assertIsInstance(txid, int)
        paid = db.get_contract_schedule("2026-07")[0]
        self.assertEqual(paid["amount_cents"], 14750)
        self.assertEqual(paid["scheduled_amount_cents"], 15000)
        self.assertEqual(db.get_price_for_date(contract, "2027-01-31"), 15000)

        with self.assertRaises(ValueError):
            db.confirm_contract_payment(contract, "2026-07-31")
        db.save_contract("Insurance", "expense", 12000, self.expense, self.account, "half-yearly", "2026-01-31", "2026-08-01", "", contract_id=contract)

        self.assertEqual(db.get_contract_schedule("2027-01"), [])
        self.assertEqual(db.get_contract_schedule("2026-07")[0]["amount_cents"], 14750)

    def test_new_database_schema_version_and_backup_roundtrip(self):
        with db.get_connection() as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)

        filename = backups.create_backup()
        self.assertIn(filename, [r["name"] for r in backups.list_backups()])

        with sqlite3.connect(backups.get_backup_path(filename)) as conn:
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertGreaterEqual(conn.execute("SELECT count(*) FROM accounts").fetchone()[0], 2)

        backups.delete_backup(filename)
        self.assertFalse((backups.BACKUP_DIR / filename).exists())

        with self.assertRaises(ValueError):
            backups.get_backup_path("../../finances.db")

    def test_old_database_migration_preserves_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.db"

            with sqlite3.connect(path) as conn:
                from personal_finances.migrations import migrate
                conn.execute("PRAGMA user_version = 0")
                migrate(conn)

                conn.execute("INSERT INTO accounts (id,name,opening_balance_cents) VALUES (42,'Legacy',1234)")
                conn.execute("INSERT INTO categories (id,name,type) VALUES (42,'Legacy expense','expense')")
                conn.execute("INSERT INTO contracts (id,name,type,amount_cents,category_id,account_id,frequency,start_date) " "VALUES (42,'Legacy contract','expense',500,42,42,'monthly','2026-01-01')")
                conn.execute("DELETE FROM contract_prices")
                conn.execute("PRAGMA user_version = 1")

            with sqlite3.connect(path) as conn:
                migrate(conn)

                self.assertEqual(conn.execute("SELECT opening_balance_cents FROM accounts WHERE id=42").fetchone()[0], 1234)
                self.assertEqual(conn.execute("SELECT amount_cents FROM contract_prices WHERE contract_id=42").fetchone()[0], 500)
                self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)

                migrate(conn)
                
                self.assertEqual(conn.execute("SELECT count(*) FROM contract_prices WHERE contract_id=42").fetchone()[0], 1)

if __name__ == "__main__":
    unittest.main()
