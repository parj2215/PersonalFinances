document.addEventListener("DOMContentLoaded", () => {

    // --------------------------------------------------
    // SHARED ELEMENTS
    // --------------------------------------------------

    const transactionModal = document.getElementById(
        "transaction-modal"
    );

    const contractModal = document.getElementById(
        "contract-modal"
    );

    const transactionForm = document.getElementById(
        "transaction-form"
    );

    const contractForm = document.getElementById(
        "contract-form"
    );

    const csrfToken = document.querySelector(
        'meta[name="csrf-token"]'
    ).content;

    let categories = [];


    // --------------------------------------------------
    // HELPERS
    // --------------------------------------------------

    function localDateString() {

        const now = new Date();

        const year = now.getFullYear();

        const month = String(
            now.getMonth() + 1
        ).padStart(2, "0");

        const day = String(
            now.getDate()
        ).padStart(2, "0");

        return `${year}-${month}-${day}`;
    }


    function centsToEuros(cents) {
        return (cents / 100).toFixed(2);
    }


    function populateSelect(select, items, placeholder) {

        select.replaceChildren(
            new Option(placeholder, "")
        );

        items.forEach(item => {

            select.add(
                new Option(item.name, item.id)
            );

        });
    }


    function showError(elementId, message) {

        const element = document.getElementById(elementId);

        if (!element) {
            return;
        }

        element.textContent = message;
        element.hidden = !message;
    }


    async function apiRequest(url, method = "GET", data = null) {

        const options = {
            method,
            headers: {
                "X-CSRF-Token": csrfToken
            }
        };

        if (data !== null) {

            options.headers["Content-Type"] = "application/json";

            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.error || "Request failed"
            );
        }

        return result;
    }


    async function loadFormOptions() {

        const response = await fetch("/api/form-options");

        if (!response.ok) {
            throw new Error("Could not load accounts and categories");
        }

        const data = await response.json();

        categories = data.categories;

        const accountSelects = [
            document.getElementById("from-account"),
            document.getElementById("to-account"),
            document.getElementById("contract-account")
        ];

        accountSelects.forEach(select => {

            populateSelect(
                select,
                data.accounts,
                "Select account"
            );

        });
    }


    // --------------------------------------------------
    // TRANSACTION FORM
    // --------------------------------------------------

    const transactionType = document.getElementById(
        "transaction-type"
    );

    const transactionCategory = document.getElementById(
        "transaction-category"
    );

    const fromAccount = document.getElementById(
        "from-account"
    );

    const toAccount = document.getElementById(
        "to-account"
    );


    function updateTransactionFields() {

        const type = transactionType.value;

        const categoryGroup = document.getElementById(
            "category-group"
        );

        const fromGroup = document.getElementById(
            "from-account-group"
        );

        const toGroup = document.getElementById(
            "to-account-group"
        );

        categoryGroup.hidden = type === "transfer";

        fromGroup.hidden = type === "income";

        toGroup.hidden = type === "expense";

        transactionCategory.required = type !== "transfer";

        fromAccount.required = type !== "income";

        toAccount.required = type !== "expense";

        const matchingCategories = categories.filter(
            category => category.type === type
        );

        populateSelect(
            transactionCategory,
            matchingCategories,
            "Select category"
        );
    }


    transactionType.addEventListener(
        "change",
        updateTransactionFields
    );


    // --------------------------------------------------
    // OPEN TRANSACTION MODAL
    // --------------------------------------------------

    async function openTransactionModal(record = null) {

        try {
            await loadFormOptions();

            transactionForm.reset();

            delete transactionForm.dataset.editId;

            document.getElementById(
                "transaction-date"
            ).value = localDateString();

            showError("transaction-error", "");

            if (record) {

                transactionForm.dataset.editId = record.id;

                document.getElementById(
                    "transaction-modal-title"
                ).textContent = "Edit Transaction";

                transactionForm.elements["date"].value =
                    record.date;

                transactionForm.elements["description"].value =
                    record.description;

                transactionType.value = record.type;

                transactionForm.elements["amount"].value =
                    centsToEuros(record.amount_cents);

                updateTransactionFields();

                transactionCategory.value =
                    record.category_id ?? "";

                fromAccount.value =
                    record.from_account_id ?? "";

                toAccount.value =
                    record.to_account_id ?? "";

            } else {

                document.getElementById(
                    "transaction-modal-title"
                ).textContent = "Add Transaction";

                transactionType.value = "expense";

                updateTransactionFields();
            }

            transactionModal.showModal();

        } catch (error) {
            alert(error.message);
        }
    }


    document.querySelectorAll(
        ".open-transaction-modal"
    ).forEach(button => {

        button.addEventListener("click", () => {
            openTransactionModal();
        });

    });


    document.querySelectorAll(
        ".edit-transaction"
    ).forEach(button => {

        button.addEventListener("click", () => {

            const record = JSON.parse(
                button.dataset.record
            );

            openTransactionModal(record);
        });

    });


    // --------------------------------------------------
    // SAVE TRANSACTION
    // --------------------------------------------------

    transactionForm.addEventListener(
        "submit",
        async event => {

            event.preventDefault();

            showError("transaction-error", "");

            const data = Object.fromEntries(
                new FormData(transactionForm).entries()
            );

            const editId = transactionForm.dataset.editId;

            const url = editId
                ? `/api/transactions/${editId}`
                : "/api/transactions";

            const method = editId ? "PUT" : "POST";

            const submitButton = transactionForm.querySelector(
                'button[type="submit"]'
            );

            submitButton.disabled = true;

            try {

                await apiRequest(url, method, data);

                transactionModal.close();

                window.location.reload();

            } catch (error) {

                showError(
                    "transaction-error",
                    error.message
                );

            } finally {

                submitButton.disabled = false;
            }

        }
    );


    // --------------------------------------------------
    // DELETE TRANSACTION
    // --------------------------------------------------

    document.querySelectorAll(
        ".delete-transaction"
    ).forEach(button => {

        button.addEventListener("click", async () => {

            const id = button.dataset.id;

            if (!confirm("Delete this transaction?")) {
                return;
            }

            try {

                await apiRequest(
                    `/api/transactions/${id}`,
                    "DELETE"
                );

                window.location.reload();

            } catch (error) {
                alert(error.message);
            }

        });

    });


    // --------------------------------------------------
    // CONTRACT FORM
    // --------------------------------------------------

    const contractType = document.getElementById(
        "contract-type"
    );

    const contractCategory = document.getElementById(
        "contract-category"
    );


    function updateContractCategories() {

        const matchingCategories = categories.filter(
            category => category.type === contractType.value
        );

        populateSelect(
            contractCategory,
            matchingCategories,
            "Select category"
        );
    }


    contractType.addEventListener(
        "change",
        updateContractCategories
    );


    // --------------------------------------------------
    // OPEN CONTRACT MODAL
    // --------------------------------------------------

    async function openContractModal(record = null) {

        try {

            await loadFormOptions();

            contractForm.reset();

            delete contractForm.dataset.editId;

            showError("contract-error", "");

            contractForm.elements["start_date"].value =
                localDateString();

            if (record) {

                contractForm.dataset.editId = record.id;

                document.getElementById(
                    "contract-modal-title"
                ).textContent = "Edit Contract";

                contractForm.elements["name"].value =
                    record.name;

                contractType.value = record.type;

                contractForm.elements["amount"].value =
                    centsToEuros(record.amount_cents);

                contractForm.elements["frequency"].value =
                    record.frequency;

                contractForm.elements["start_date"].value =
                    record.start_date;

                contractForm.elements["end_date"].value =
                    record.end_date ?? "";

                contractForm.elements["notes"].value =
                    record.notes ?? "";

                updateContractCategories();

                contractCategory.value =
                    record.category_id;

                contractForm.elements["account_id"].value =
                    record.account_id;

            } else {

                document.getElementById(
                    "contract-modal-title"
                ).textContent = "Add Contract";

                contractType.value = "expense";

                updateContractCategories();
            }

            contractModal.showModal();

        } catch (error) {
            alert(error.message);
        }
    }


    document.querySelectorAll(
        ".open-contract-modal"
    ).forEach(button => {

        button.addEventListener("click", () => {
            openContractModal();
        });

    });


    document.querySelectorAll(
        ".edit-contract"
    ).forEach(button => {

        button.addEventListener("click", () => {

            const record = JSON.parse(
                button.dataset.record
            );

            openContractModal(record);
        });

    });


    // --------------------------------------------------
    // SAVE CONTRACT
    // --------------------------------------------------

    contractForm.addEventListener(
        "submit",
        async event => {

            event.preventDefault();

            showError("contract-error", "");

            const data = Object.fromEntries(
                new FormData(contractForm).entries()
            );

            const editId = contractForm.dataset.editId;

            const url = editId
                ? `/api/contracts/${editId}`
                : "/api/contracts";

            const method = editId ? "PUT" : "POST";

            const submitButton = contractForm.querySelector(
                'button[type="submit"]'
            );

            submitButton.disabled = true;

            try {

                await apiRequest(url, method, data);

                contractModal.close();

                window.location.reload();

            } catch (error) {

                showError(
                    "contract-error",
                    error.message
                );

            } finally {

                submitButton.disabled = false;
            }

        }
    );


    // --------------------------------------------------
    // CANCEL CONTRACT
    // --------------------------------------------------

    document.querySelectorAll(
        ".cancel-contract"
    ).forEach(button => {

        button.addEventListener("click", async () => {

            const id = button.dataset.id;

            if (!confirm("Cancel this contract?")) {
                return;
            }

            try {

                await apiRequest(
                    `/api/contracts/${id}/cancel`,
                    "POST"
                );

                window.location.reload();

            } catch (error) {
                alert(error.message);
            }

        });

    });


    // --------------------------------------------------
    // CONFIRM CONTRACT PAYMENT
    // --------------------------------------------------

    document.querySelectorAll(
        ".confirm-payment"
    ).forEach(button => {

        button.addEventListener("click", async () => {

            const contractId = button.dataset.contractId;

            const dueDate = button.dataset.date;

            if (!confirm(
                `Confirm payment scheduled for ${dueDate}?`
            )) {
                return;
            }

            try {

                await apiRequest(
                    `/api/contracts/${contractId}/payments`,
                    "POST",
                    {
                        due_date: dueDate
                    }
                );

                window.location.reload();

            } catch (error) {
                alert(error.message);
            }

        });

    });

    // --------------------------------------------------
    // EDIT ACCOUNT
    // --------------------------------------------------

    document.querySelectorAll(".edit-account").forEach(button => {

        button.addEventListener("click", async () => {

            const id = button.dataset.id;

            const name = prompt(
                "Account name:",
                button.dataset.name
            );

            if (name === null) return;

            const balance = prompt(
                "Opening balance (€):",
                centsToEuros(Number(button.dataset.balance))
            );

            if (balance === null) return;

            try {

                await apiRequest(
                    `/api/accounts/${id}`,
                    "PUT",
                    {
                        name: name.trim(),
                        opening_balance: balance
                    }
                );

                window.location.reload();

            } catch (error) {
                alert(error.message);
            }

        });

    });

    // --------------------------------------------------
    // DELETE ACCOUNT
    // --------------------------------------------------

    document.querySelectorAll(".delete-account").forEach(button => {

        button.addEventListener("click", async () => {

            const id = button.dataset.id;

            if (!confirm("Permanently delete this account?")) {
                return;
            }

            try {

                await apiRequest(
                    `/api/accounts/${id}`,
                    "DELETE"
                );

                window.location.reload();

            } catch (error) {
                alert(error.message);
            }

        });

    });

    // --------------------------------------------------
    // EDIT CATEGORY
    // --------------------------------------------------

    document.querySelectorAll(".edit-category").forEach(button => {

        button.addEventListener("click", async () => {

            const id = button.dataset.id;

            const name = prompt(
                "Category name:",
                button.dataset.name
            );

            if (name === null) return;

            const type = prompt(
                "Category type (income / expense):",
                button.dataset.type
            );

            if (type === null) return;

            try {

                await apiRequest(
                    `/api/categories/${id}`,
                    "PUT",
                    {
                        name: name.trim(),
                        type: type.trim().toLowerCase()
                    }
                );

                window.location.reload();

            } catch (error) {
                alert(error.message);
            }

        });

    });

    // --------------------------------------------------
    // DELETE CATEGORY
    // --------------------------------------------------

    document.querySelectorAll(".delete-category").forEach(button => {

        button.addEventListener("click", async () => {

            const id = button.dataset.id;

            if (!confirm("Permanently delete this category?")) {
                return;
            }

            try {

                await apiRequest(
                    `/api/categories/${id}`,
                    "DELETE"
                );

                window.location.reload();

            } catch (error) {
                alert(error.message);
            }

        });

    });

    // --------------------------------------------------
    // DELETE CONTRACT
    // --------------------------------------------------

    document.querySelectorAll(".delete-contract").forEach(button => {

        button.addEventListener("click", async () => {

            const id = button.dataset.id;

            const confirmed = confirm(
                "Permanently delete this contract?\n\n" +
                "Previously confirmed transactions will be preserved."
            );

            if (!confirmed) return;

            try {

                await apiRequest(
                    `/api/contracts/${id}`,
                    "DELETE"
                );

                window.location.reload();

            } catch (error) {
                alert(error.message);
            }

        });

    });

    // --------------------------------------------------
    // CLOSE MODALS
    // --------------------------------------------------

    document.querySelectorAll(
        "[data-close-dialog]"
    ).forEach(button => {

        button.addEventListener("click", () => {

            button.closest("dialog").close();

        });

    });


    // --------------------------------------------------
    // INITIAL STATE
    // --------------------------------------------------

    updateTransactionFields();
    updateContractCategories();

});