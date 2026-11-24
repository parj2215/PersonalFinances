import calendar
import sqlite3
import secrets

from pathlib import Path
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    session,
    abort
)

from database import (
    delete_contract,
    initialize_database,
    get_accounts,
    add_account,
    get_account_balances,
    get_categories,
    add_category,
    get_transactions,
    save_transaction,
    delete_transaction,
    get_monthly_summary,
    get_cumulative_saldo,
    get_monthly_report,
    get_contracts,
    save_contract,
    cancel_contract,
    get_contract_schedule,
    confirm_contract_payment,
    update_account,
    delete_account,
    update_category,
    delete_category
)

# APPLICATION INITIALIZATION
app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent

secret_file = BASE_DIR / ".flask_secret"

if not secret_file.exists():
    secret_file.write_bytes(secrets.token_bytes(32))
    secret_file.chmod(0o600)

app.secret_key = secret_file.read_bytes()

initialize_database()

# CSRF PROTECTION
@app.context_processor
def inject_csrf_token():

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    return {"csrf_token": session["csrf_token"]}


@app.before_request
def check_csrf():

    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return

    expected = session.get("csrf_token", "")

    submitted = (
        request.headers.get("X-CSRF-Token")
        or request.form.get("csrf_token", "")
    )

    if not expected or not secrets.compare_digest(
        expected,
        submitted
    ):
        abort(403)

# FORMATTING
@app.template_filter("money")
def format_money(cents):

    value = Decimal(int(cents)) / 100

    sign = "-" if value < 0 else ""

    return f"{sign}€{abs(value):,.2f}"

# VALIDATION HELPERS
def parse_amount(value, allow_negative=False):

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError("Invalid monetary amount")

    if not amount.is_finite():
        raise ValueError("Amount must be finite")

    if not allow_negative and amount <= 0:
        raise ValueError("Amount must be positive")

    cents = amount * 100

    if cents != cents.to_integral_value():
        raise ValueError("Use at most two decimal places")

    return int(cents)


def parse_id(value, required=False):

    if value in (None, ""):
        if required:
            raise ValueError("A required selection is missing")
        return None

    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValueError("Invalid ID")

    if result <= 0:
        raise ValueError("Invalid ID")

    return result


def parse_date(value, required=True):

    if not value:
        if required:
            raise ValueError("Date is required")
        return None

    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        raise ValueError("Invalid date")


def parse_month(value):

    try:
        year, month = map(int, value.split("-"))

        if not 1 <= year <= 9999:
            raise ValueError

        if not 1 <= month <= 12:
            raise ValueError

        return f"{year:04d}-{month:02d}"

    except (AttributeError, TypeError, ValueError):
        return date.today().strftime("%Y-%m")


def month_cutoff(month):
    year, month_number = map(int, month.split("-"))
    last_day = calendar.monthrange(year, month_number)[1]
    month_end = date(year, month_number, last_day)

    return min(month_end, date.today()).isoformat()


def error_response(error):
    return jsonify({"error": str(error)}), 400

# DASHBOARD
@app.route("/")
def dashboard():

    selected_month = parse_month(
        request.args.get("month")
    )

    as_of_date = month_cutoff(selected_month)

    accounts = get_account_balances(as_of_date)

    monthly = get_monthly_summary(
        selected_month,
        as_of_date
    )

    total_balance = sum(
        account["balance_cents"]
        for account in accounts
    )

    monthly_income = monthly["income_cents"]
    monthly_expenses = monthly["expenses_cents"]

    monthly_saldo = monthly_income - monthly_expenses

    cumulative_saldo = get_cumulative_saldo(as_of_date)

    return render_template(
        "index.html",
        active_page="dashboard",
        accounts=accounts,
        total_balance=total_balance,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        monthly_saldo=monthly_saldo,
        cumulative_saldo=cumulative_saldo,
        selected_month=selected_month
    )

# TRANSACTIONS PAGE
@app.route("/transactions")
def transactions():

    selected_month = parse_month(
        request.args.get("month")
    )

    sort_by = request.args.get("sort", "date")
    order = request.args.get("order", "desc")

    transaction_list = get_transactions(
        month=selected_month,
        sort_by=sort_by,
        order=order
    )

    return render_template(
        "transactions.html",
        active_page="transactions",
        transactions=transaction_list,
        selected_month=selected_month,
        sort_by=sort_by,
        order=order
    )

# CONTRACTS PAGE
@app.route("/contracts")
def contracts():

    selected_month = parse_month(
        request.args.get("month")
    )

    sort_by = request.args.get("sort", "name")
    order = request.args.get("order", "asc")

    contract_list = get_contracts(sort_by, order)

    payment_schedule = get_contract_schedule(
        selected_month
    )

    payment_sort = request.args.get(
        "payment_sort", "date"
    )

    payment_order = request.args.get(
        "payment_order", "asc"
    )

    payment_columns = {
        "date": "due_date",
        "name": "name",
        "category": "category",
        "account": "account",
        "amount": "amount_cents",
        "status": "paid"
    }

    key = payment_columns.get(
        payment_sort, "due_date"
    )

    payment_schedule.sort(
        key=lambda item: item[key],
        reverse=payment_order == "desc"
    )

    return render_template(
        "contracts.html",
        active_page="contracts",
        contracts=contract_list,
        schedule=payment_schedule,
        selected_month=selected_month,
        sort_by=sort_by,
        order=order,
        payment_sort=payment_sort,
        payment_order=payment_order,
        today=date.today().isoformat()
    )

# ACCOUNTS PAGE
@app.route("/accounts")
def accounts():

    balances = get_account_balances(
        date.today().isoformat()
    )

    return render_template(
        "accounts.html",
        active_page="accounts",
        accounts=balances
    )

# REPORTS PAGE
@app.route("/reports")
def reports():

    sort_by = request.args.get("sort", "month")
    order = request.args.get("order", "desc")

    monthly_report = get_monthly_report(
        sort_by, order
    )

    return render_template(
        "reports.html",
        active_page="reports",
        monthly_report=monthly_report,
        sort_by=sort_by,
        order=order
    )

# SETTINGS PAGE
@app.route("/settings")
def settings():

    return render_template(
        "settings.html",
        active_page="settings",
        categories=get_categories()
    )

# ACCOUNT MANAGEMENT
@app.route("/accounts/add", methods=["POST"])
def create_account():

    try:
        name = request.form["name"].strip()

        if not name:
            raise ValueError("Account name is required")

        opening_balance = parse_amount(
            request.form["opening_balance"],
            allow_negative=True
        )

        add_account(name, opening_balance)

        flash("Account created successfully", "success")

    except (ValueError, KeyError, sqlite3.IntegrityError) as error:
        flash(str(error), "error")

    return redirect(url_for("accounts"))

# CATEGORY MANAGEMENT
@app.route("/categories/add", methods=["POST"])
def create_category():

    try:
        name = request.form["name"].strip()
        category_type = request.form["type"]

        if not name:
            raise ValueError("Category name is required")

        if category_type not in ("income", "expense"):
            raise ValueError("Invalid category type")

        add_category(name, category_type)

        flash("Category created successfully", "success")

    except (ValueError, KeyError, sqlite3.IntegrityError) as error:
        flash(str(error), "error")

    return redirect(url_for("settings"))

# FORM OPTIONS API
@app.route("/api/form-options")
def form_options():

    return jsonify({
        "accounts": [
            dict(row)
            for row in get_accounts(active_only=True)
        ],
        "categories": [
            dict(row)
            for row in get_categories()
        ]
    })

# TRANSACTION VALIDATION
def validate_transaction(data):

    transaction_date = parse_date(data.get("date"))

    description = str(
        data.get("description") or ""
    ).strip()

    transaction_type = data.get("type")

    amount_cents = parse_amount(data.get("amount"))

    category_id = parse_id(data.get("category_id"))
    from_account_id = parse_id(data.get("from_account_id"))
    to_account_id = parse_id(data.get("to_account_id"))

    if not description:
        raise ValueError("Description is required")

    if transaction_type not in (
        "income", "expense", "transfer"
    ):
        raise ValueError("Invalid transaction type")

    if transaction_type == "expense":
        to_account_id = None

        if category_id is None or from_account_id is None:
            raise ValueError(
                "Expense requires a category and source account"
            )

    elif transaction_type == "income":
        from_account_id = None

        if category_id is None or to_account_id is None:
            raise ValueError(
                "Income requires a category and destination account"
            )

    else:
        category_id = None

        if from_account_id is None or to_account_id is None:
            raise ValueError(
                "Transfer requires two accounts"
            )

        if from_account_id == to_account_id:
            raise ValueError(
                "Source and destination must differ"
            )

    if category_id is not None:
        category_lookup = {
            row["id"]: row["type"]
            for row in get_categories()
        }

        if category_lookup.get(category_id) != transaction_type:
            raise ValueError(
                "Category does not match transaction type"
            )

    return (
        transaction_date,
        description,
        transaction_type,
        amount_cents,
        category_id,
        from_account_id,
        to_account_id
    )

# TRANSACTIONS API
@app.route("/api/transactions", methods=["POST"])
def create_transaction():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        values = validate_transaction(data)

        transaction_id = save_transaction(*values)

        return jsonify({
            "success": True,
            "id": transaction_id
        }), 201

    except (ValueError, sqlite3.IntegrityError) as error:
        return error_response(error)

@app.route("/api/transactions/<int:transaction_id>", methods=["PUT"])
def update_transaction(transaction_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        values = validate_transaction(data)

        save_transaction(
            *values,
            transaction_id=transaction_id
        )

        return jsonify({"success": True})

    except (ValueError, sqlite3.IntegrityError) as error:
        return error_response(error)

@app.route("/api/transactions/<int:transaction_id>", methods=["DELETE"])
def remove_transaction(transaction_id):

    deleted = delete_transaction(transaction_id)

    if not deleted:
        return jsonify({"error": "Transaction not found"}), 404

    return jsonify({"success": True})

# CONTRACT VALIDATION
def validate_contract(data):

    name = str(data.get("name") or "").strip()

    contract_type = data.get("type")

    amount_cents = parse_amount(
        data.get("amount")
    )

    category_id = parse_id(
        data.get("category_id"),
        required=True
    )

    account_id = parse_id(
        data.get("account_id"),
        required=True
    )

    frequency = data.get("frequency")

    start_date = parse_date(
        data.get("start_date")
    )

    end_date = parse_date(
        data.get("end_date"),
        required=False
    )

    notes = str(data.get("notes") or "").strip()

    if not name:
        raise ValueError("Contract name is required")

    if contract_type not in ("income", "expense"):
        raise ValueError("Invalid contract type")

    if frequency not in (
        "weekly", "monthly", "quarterly", "yearly"
    ):
        raise ValueError("Invalid payment frequency")

    if end_date and end_date < start_date:
        raise ValueError(
            "End date cannot precede start date"
        )

    category_lookup = {
        row["id"]: row["type"]
        for row in get_categories()
    }

    if category_lookup.get(category_id) != contract_type:
        raise ValueError(
            "Category does not match contract type"
        )

    return (
        name,
        contract_type,
        amount_cents,
        category_id,
        account_id,
        frequency,
        start_date,
        end_date,
        notes
    )

# CONTRACTS API
@app.route("/api/contracts", methods=["POST"])
def create_contract():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        values = validate_contract(data)

        contract_id = save_contract(*values)

        return jsonify({
            "success": True,
            "id": contract_id
        }), 201

    except (ValueError, sqlite3.IntegrityError) as error:
        return error_response(error)

@app.route("/api/contracts/<int:contract_id>", methods=["PUT"])
def update_contract(contract_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        values = validate_contract(data)

        save_contract(
            *values,
            contract_id=contract_id
        )

        return jsonify({"success": True})

    except (ValueError, sqlite3.IntegrityError) as error:
        return error_response(error)

@app.route("/api/contracts/<int:contract_id>/cancel", methods=["POST"])
def end_contract(contract_id):

    cancelled = cancel_contract(
        contract_id,
        date.today().isoformat()
    )

    if not cancelled:
        return jsonify({
            "error": "Contract not found or already cancelled"
        }), 400

    return jsonify({"success": True})

@app.route("/api/contracts/<int:contract_id>/payments", methods=["POST"])
def record_contract_payment(contract_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        due_date = parse_date(
            data.get("due_date")
        )

        if due_date > date.today().isoformat():
            raise ValueError(
                "Future payments cannot be confirmed yet"
            )

        transaction_id = confirm_contract_payment(
            contract_id,
            due_date
        )

        return jsonify({
            "success": True,
            "transaction_id": transaction_id
        }), 201

    except (ValueError, sqlite3.IntegrityError) as error:
        return error_response(error)

@app.route("/api/accounts/<int:account_id>", methods=["PUT"])
def edit_account(account_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request"}), 400

    try:
        name = str(data.get("name") or "").strip()

        if not name:
            raise ValueError("Account name is required")

        opening_balance = parse_amount(
            data.get("opening_balance"),
            allow_negative=True
        )

        updated = update_account(
            account_id,
            name,
            opening_balance
        )

        if not updated:
            return jsonify({"error": "Account not found"}), 404

        return jsonify({"success": True})

    except (ValueError, sqlite3.IntegrityError) as error:
        return error_response(error)

@app.route("/api/accounts/<int:account_id>", methods=["DELETE"])
def remove_account(account_id):

    try:
        deleted = delete_account(account_id)

        if not deleted:
            return jsonify({
                "error": "Account cannot be deleted. "
                         "It may still contain transactions or contracts."
            }), 409

        return jsonify({"success": True})

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "Account is referenced by another record"
        }), 409

@app.route("/api/categories/<int:category_id>", methods=["PUT"])
def edit_category(category_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request"}), 400

    try:
        name = str(data.get("name") or "").strip()
        category_type = data.get("type")

        if not name:
            raise ValueError("Category name is required")

        if category_type not in ("income", "expense"):
            raise ValueError("Invalid category type")

        updated = update_category(
            category_id,
            name,
            category_type
        )

        if not updated:
            return jsonify({"error": "Category not found"}), 404

        return jsonify({"success": True})

    except (ValueError, sqlite3.IntegrityError) as error:
        return error_response(error)

@app.route("/api/categories/<int:category_id>", methods=["DELETE"])
def remove_category(category_id):

    try:
        deleted = delete_category(category_id)

        if not deleted:
            return jsonify({
                "error": "Category cannot be deleted. "
                         "It may still be used by transactions or contracts."
            }), 409

        return jsonify({"success": True})

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "Category is referenced by another record"
        }), 409

@app.route("/api/contracts/<int:contract_id>", methods=["DELETE"])
def remove_contract(contract_id):

    deleted = delete_contract(contract_id)

    if not deleted:
        return jsonify({
            "error": "Contract not found"
        }), 404

    return jsonify({"success": True})

# START APPLICATION
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )