document.addEventListener("DOMContentLoaded", () => {

    // Shared elements

    const transactionModal = document.getElementById("transaction-modal");
    const contractModal = document.getElementById("contract-modal");
    const priceModal = document.getElementById("price-modal");
    const transactionForm = document.getElementById("transaction-form");
    const contractForm = document.getElementById("contract-form");
    const priceForm = document.getElementById("price-form");
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
    let categories = [];

    // Dark confirmation dialog, accessible from existing async handlers.
    function uiConfirm(message) {
        const dialog = document.getElementById("confirm-dialog");
        const yes = document.getElementById("confirm-yes");
        const no = document.getElementById("confirm-no");
        document.getElementById("confirm-dialog-text").textContent = message;
        return new Promise(resolve => {
            let settled = false;
            function finish(value) {
                if (settled) return;
                settled = true;
                dialog.close();
                resolve(value);
            }
            yes.onclick = () => finish(true);
            no.onclick = () => finish(false);
            dialog.addEventListener("close", () => finish(false), { once: true });
            dialog.showModal();
        });
    }
    function uiNotify(message, kind = "error") {
        const region = document.getElementById("toast-region");
        const toast = document.createElement("div");
        toast.className = `toast ${kind}`;
        toast.textContent = message;
        region.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }

    // Helpers

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
        return (
            Number(cents) / 100
        ).toFixed(2);
    }
    function populateSelect(
        select,
        items,
        placeholder
    ) {
        select.replaceChildren(
            new Option(placeholder, "")
        );
        items.forEach(item => {
            select.add(
                new Option(
                    item.name,
                    item.id
                )
            );
        });
    }
    function showError(
        elementId,
        message
    ) {
        const element = document.getElementById(elementId);
        if (!element) {
            return;
        }
        element.textContent = message;
        element.hidden = !message;
    }
    async function apiRequest(
        url,
        method = "GET",
        data = null
    ) {
        const options = {
            method,
            headers: {
                "X-CSRF-Token": csrfToken
            }
        };
        if (data !== null) {
            options.headers["Content-Type"] =
                "application/json";
            options.body = JSON.stringify(data);
        }
        const response = await fetch(
            url,
            options
        );
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || "Request failed");
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

    // Transaction form

    const transactionType = document.getElementById("transaction-type");
    const transactionCategory = document.getElementById("transaction-category");
    const fromAccount = document.getElementById("from-account");
    const toAccount = document.getElementById("to-account");
    function updateTransactionFields() {
        const type = transactionType.value;
        const categoryGroup = document.getElementById("category-group");
        const fromGroup = document.getElementById("from-account-group");
        const toGroup = document.getElementById("to-account-group");
        categoryGroup.hidden = type === "transfer";
        fromGroup.hidden = type === "income";
        toGroup.hidden = type === "expense";
        transactionCategory.required =
            type !== "transfer";
        fromAccount.required =
            type !== "income";
        toAccount.required =
            type !== "expense";
        const matchingCategories = categories.filter(category => category.type === type);
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

    // Open transaction modal

    async function openTransactionModal(record = null) {
        try {
            await loadFormOptions();
            transactionForm.reset();
            delete transactionForm.dataset.editId;
            document.getElementById("transaction-date").value = localDateString();
            showError(
                "transaction-error",
                ""
            );
            if (record) {
                transactionForm.dataset.editId =
                    record.id;
                document.getElementById("transaction-modal-title").textContent = "Edit Transaction";
                transactionForm.elements["date"].value =
                    record.date;
                transactionForm.elements["description"].value =
                    record.description;
                transactionType.value =
                    record.type;
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
                document.getElementById("transaction-modal-title").textContent = "Add Transaction";
                transactionType.value = "expense";
                updateTransactionFields();
            }
            transactionModal.showModal();
        } catch (error) {
            uiNotify(error.message);
        }
    }
    document.querySelectorAll(".open-transaction-modal").forEach(button => {
        button.addEventListener("click", () => {
            openTransactionModal();
        });
    });
    document.querySelectorAll(".edit-transaction").forEach(button => {
        button.addEventListener("click", () => {
            const record = JSON.parse(button.dataset.record);
            openTransactionModal(record);
        });
    });

    // Save transaction

    transactionForm.addEventListener(
        "submit",
        async event => {
            event.preventDefault();
            showError(
                "transaction-error",
                ""
            );
            const data = Object.fromEntries(
                new FormData(transactionForm).entries()
            );
            const editId =
                transactionForm.dataset.editId;
            const url = editId
                ? `/api/transactions/${editId}`
                : "/api/transactions";
            const method = editId
                ? "PUT"
                : "POST";
            const submitButton =
                transactionForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            try {
                await apiRequest(
                    url,
                    method,
                    data
                );
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

    // Delete transaction

    document.querySelectorAll(".delete-transaction").forEach(button => {
        button.addEventListener(
            "click",
            async () => {
                const id = button.dataset.id;
                if (!await uiConfirm("Delete this transaction?")) {
                    return;
                }
                try {
                    await apiRequest(
                        `/api/transactions/${id}`,
                        "DELETE"
                    );
                    window.location.reload();
                } catch (error) {
                    uiNotify(error.message);
                }
            }
        );
    });

    // Contract form

    const contractType = document.getElementById("contract-type");
    const contractCategory = document.getElementById("contract-category");
    const contractAmount = document.getElementById("contract-amount");
    function updateContractCategories() {
        const matchingCategories = categories.filter(
            category => (
                category.type === contractType.value
            )
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

    // Open contract modal

    async function openContractModal(record = null) {
        try {
            await loadFormOptions();
            contractForm.reset();
            delete contractForm.dataset.editId;
            showError(
                "contract-error",
                ""
            );
            contractForm.elements["start_date"].value =
                localDateString();

            // Amount can be entered for new contracts.
            //
            // Existing contract prices are managed
            // through the Change Price popup.

            contractAmount.readOnly = false;
            contractAmount.title = "";
            if (record) {
                contractForm.dataset.editId =
                    record.id;
                document.getElementById("contract-modal-title").textContent = "Edit Contract";
                contractForm.elements["name"].value =
                    record.name;
                contractType.value =
                    record.type;
                contractAmount.value = centsToEuros(record.current_amount_cents);
                contractAmount.readOnly = true;
                contractAmount.title =
                    "Use Change Price to modify contract prices";
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
                document.getElementById("contract-modal-title").textContent = "Add Contract";
                contractType.value = "expense";
                updateContractCategories();
            }
            contractModal.showModal();
        } catch (error) {
            uiNotify(error.message);
        }
    }
    document.querySelectorAll(".open-contract-modal").forEach(button => {
        button.addEventListener("click", () => {
            openContractModal();
        });
    });
    document.querySelectorAll(".edit-contract").forEach(button => {
        button.addEventListener("click", () => {
            const record = JSON.parse(button.dataset.record);
            openContractModal(record);
        });
    });

    // Save contract

    contractForm.addEventListener(
        "submit",
        async event => {
            event.preventDefault();
            showError(
                "contract-error",
                ""
            );
            const data = Object.fromEntries(
                new FormData(contractForm).entries()
            );
            const editId =
                contractForm.dataset.editId;
            const url = editId
                ? `/api/contracts/${editId}`
                : "/api/contracts";
            const method = editId
                ? "PUT"
                : "POST";
            const submitButton =
                contractForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            try {
                await apiRequest(
                    url,
                    method,
                    data
                );
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

    // Delete contract

    document.querySelectorAll(".delete-contract").forEach(button => {
        button.addEventListener(
            "click",
            async () => {
                const id = button.dataset.id;
                const confirmed = await uiConfirm(
                    "Permanently delete this contract?\n\n" +
                    "Previously confirmed transactions " +
                    "will be preserved."
                );
                if (!confirmed) {
                    return;
                }
                try {
                    await apiRequest(
                        `/api/contracts/${id}`,
                        "DELETE"
                    );
                    window.location.reload();
                } catch (error) {
                    uiNotify(error.message);
                }
            }
        );
    });

    // Contract price history

    const priceHistoryBody = document.getElementById("price-history-body");
    function renderPriceHistory(prices) {
        priceHistoryBody.replaceChildren();
        if (prices.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 2;
            cell.className = "empty-message";
            cell.textContent =
                "No price history available.";
            row.appendChild(cell);
            priceHistoryBody.appendChild(row);
            return;
        }
        prices.forEach(price => {
            const row = document.createElement("tr");
            const dateCell = document.createElement("td");
            const amountCell = document.createElement("td");
            dateCell.textContent =
                price.valid_from;
            amountCell.textContent =
                `€${centsToEuros(price.amount_cents)}`;
            row.appendChild(dateCell);
            row.appendChild(amountCell);
            priceHistoryBody.appendChild(row);
        });
    }
    async function loadPriceHistory(contractId) {
        const result = await apiRequest(
            `/api/contracts/${contractId}/prices`
        );
        renderPriceHistory(result.prices);
    }

    // Open change price modal

    document.querySelectorAll(".change-contract-price").forEach(button => {
        button.addEventListener(
            "click",
            async () => {
                const contractId =
                    button.dataset.id;
                const contractName =
                    button.dataset.name;
                const currentAmount =
                    Number(button.dataset.amount);
                priceForm.reset();
                priceForm.dataset.contractId =
                    contractId;
                document.getElementById("price-contract-name").textContent = contractName;
                document.getElementById("new-contract-price").value = centsToEuros(currentAmount);
                document.getElementById("price-valid-from").value = localDateString();
                showError(
                    "price-error",
                    ""
                );
                priceHistoryBody.replaceChildren();
                priceModal.showModal();
                try {
                    await loadPriceHistory(contractId);
                } catch (error) {
                    showError(
                        "price-error",
                        error.message
                    );
                }
            }
        );
    });

    // Save contract price

    priceForm.addEventListener(
        "submit",
        async event => {
            event.preventDefault();
            showError(
                "price-error",
                ""
            );
            const contractId =
                priceForm.dataset.contractId;
            const data = Object.fromEntries(
                new FormData(priceForm).entries()
            );
            const submitButton =
                priceForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            try {
                await apiRequest(
                    `/api/contracts/${contractId}/prices`,
                    "POST",
                    data
                );
                await loadPriceHistory(contractId);
                priceModal.close();
                window.location.reload();
            } catch (error) {
                showError(
                    "price-error",
                    error.message
                );
            } finally {
                submitButton.disabled = false;
            }
        }
    );

    // Edit account / edit category / confirm payment

    function bindEditDialog(selector, dialogId, formId, errorId, urlBase, fields) {
        const dialog = document.getElementById(dialogId);
        const form = document.getElementById(formId);
        document.querySelectorAll(selector).forEach(button => {
            button.addEventListener("click", () => {
                showError(errorId, "");
                form.elements.id.value = button.dataset.id;
                fields.forEach(([name, dataName, transform]) => {
                    form.elements[name].value = transform ? transform(button.dataset[dataName]) : button.dataset[dataName];
                });
                dialog.showModal();
            });
        });
        form.addEventListener("submit", async event => {
            event.preventDefault();
            const submit = form.querySelector('[type="submit"]');
            submit.disabled = true;
            try {
                const data = Object.fromEntries(new FormData(form).entries());
                await apiRequest(`${urlBase}/${data.id}`, "PUT", data);
                dialog.close();
                window.location.reload();
            } catch (error) {
                showError(errorId, error.message);
            } finally {
                submit.disabled = false;
            }
        });
    }
    bindEditDialog(".edit-account", "account-edit-dialog", "account-edit-form",
        "account-edit-error", "/api/accounts", [
            ["name", "name"],
            ["opening_balance", "balance", value => centsToEuros(Number(value))]
        ]);
    bindEditDialog(".edit-category", "category-edit-dialog", "category-edit-form",
        "category-edit-error", "/api/categories", [
            ["name", "name"], ["type", "type"]
        ]);
    const paymentDialog = document.getElementById("payment-dialog");
    const paymentForm = document.getElementById("payment-form");
    let selectedPayment = null;
    document.querySelectorAll(".confirm-payment").forEach(button => {
        button.addEventListener("click", () => {
            selectedPayment = { contractId: button.dataset.contractId, dueDate: button.dataset.date };
            document.getElementById("payment-due-label").textContent =
                `Payment due on ${selectedPayment.dueDate}`;
            paymentForm.elements.amount.value = centsToEuros(Number(button.dataset.amount));
            showError("payment-error", "");
            paymentDialog.showModal();
        });
    });
    paymentForm.addEventListener("submit", async event => {
        event.preventDefault();
        if (!selectedPayment) return;
        const submit = paymentForm.querySelector('[type="submit"]');
        submit.disabled = true;
        try {
            await apiRequest(`/api/contracts/${selectedPayment.contractId}/payments`, "POST", {
                due_date: selectedPayment.dueDate,
                override_amount: paymentForm.elements.amount.value
            });
            paymentDialog.close();
            window.location.reload();
        } catch (error) {
            showError("payment-error", error.message);
        } finally { submit.disabled = false; }
    });

    // Delete account

    document.querySelectorAll(".delete-account").forEach(button => {
        button.addEventListener(
            "click",
            async () => {
                const id = button.dataset.id;
                if (!await uiConfirm("Permanently delete this account?")) {
                    return;
                }
                try {
                    await apiRequest(
                        `/api/accounts/${id}`,
                        "DELETE"
                    );
                    window.location.reload();
                } catch (error) {
                    uiNotify(error.message);
                }
            }
        );
    });

    // Delete category

    document.querySelectorAll(".delete-category").forEach(button => {
        button.addEventListener(
            "click",
            async () => {
                const id = button.dataset.id;
                if (!await uiConfirm("Permanently delete this category?")) {
                    return;
                }
                try {
                    await apiRequest(
                        `/api/categories/${id}`,
                        "DELETE"
                    );
                    window.location.reload();
                } catch (error) {
                    uiNotify(error.message);
                }
            }
        );
    });

    // Backups
    document.getElementById("create-backup")?.addEventListener("click", async event => {
        const button = event.currentTarget;
        button.disabled = true;
        try {
            await apiRequest("/api/backups", "POST");
            window.location.reload();
        } catch (error) { uiNotify(error.message); }
        finally { button.disabled = false; }
    });
    document.querySelectorAll(".delete-backup").forEach(button => {
        button.addEventListener("click", async () => {
            if (!await uiConfirm(`Delete backup ${button.dataset.name}? This cannot be undone.`)) return;
            try {
                await apiRequest(`/api/backups/${encodeURIComponent(button.dataset.name)}`, "DELETE");
                window.location.reload();
            } catch (error) { uiNotify(error.message); }
        });
    });

    // Close dialogs

    document.querySelectorAll("[data-close-dialog]").forEach(button => {
        button.addEventListener("click", () => {
            button.closest("dialog").close();
        });
    });

    // Initial state

    updateTransactionFields();
    updateContractCategories();

});
