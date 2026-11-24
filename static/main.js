document.addEventListener("DOMContentLoaded", () => {

    // ==================================================
    // SHARED ELEMENTS
    // ==================================================

    const transactionModal = document.getElementById(
        "transaction-modal"
    );

    const contractModal = document.getElementById(
        "contract-modal"
    );

    const priceModal = document.getElementById(
        "price-modal"
    );

    const transactionForm = document.getElementById(
        "transaction-form"
    );

    const contractForm = document.getElementById(
        "contract-form"
    );

    const priceForm = document.getElementById(
        "price-form"
    );

    const csrfToken = document.querySelector(
        'meta[name="csrf-token"]'
    ).content;

    let categories = [];


    // ==================================================
    // HELPERS
    // ==================================================

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

        const element = document.getElementById(
            elementId
        );

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

            throw new Error(
                result.error || "Request failed"
            );
        }

        return result;
    }


    async function loadFormOptions() {

        const response = await fetch(
            "/api/form-options"
        );

        if (!response.ok) {

            throw new Error(
                "Could not load accounts and categories"
            );
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


    // ==================================================
    // TRANSACTION FORM
    // ==================================================

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

        transactionCategory.required =
            type !== "transfer";

        fromAccount.required =
            type !== "income";

        toAccount.required =
            type !== "expense";

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


    // ==================================================
    // OPEN TRANSACTION MODAL
    // ==================================================

    async function openTransactionModal(
        record = null
    ) {

        try {

            await loadFormOptions();

            transactionForm.reset();

            delete transactionForm.dataset.editId;

            document.getElementById(
                "transaction-date"
            ).value = localDateString();

            showError(
                "transaction-error",
                ""
            );

            if (record) {

                transactionForm.dataset.editId =
                    record.id;

                document.getElementById(
                    "transaction-modal-title"
                ).textContent = "Edit Transaction";

                transactionForm.elements["date"].value =
                    record.date;

                transactionForm.elements["description"].value =
                    record.description;

                transactionType.value =
                    record.type;

                transactionForm.elements["amount"].value =
                    centsToEuros(
                        record.amount_cents
                    );

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


    // ==================================================
    // SAVE TRANSACTION
    // ==================================================

    transactionForm.addEventListener(
        "submit",
        async event => {

            event.preventDefault();

            showError(
                "transaction-error",
                ""
            );

            const data = Object.fromEntries(
                new FormData(
                    transactionForm
                ).entries()
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
                transactionForm.querySelector(
                    'button[type="submit"]'
                );

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


    // ==================================================
    // DELETE TRANSACTION
    // ==================================================

    document.querySelectorAll(
        ".delete-transaction"
    ).forEach(button => {

        button.addEventListener(
            "click",
            async () => {

                const id = button.dataset.id;

                if (!confirm(
                    "Delete this transaction?"
                )) {
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

            }
        );

    });


    // ==================================================
    // CONTRACT FORM
    // ==================================================

    const contractType = document.getElementById(
        "contract-type"
    );

    const contractCategory = document.getElementById(
        "contract-category"
    );

    const contractAmount = document.getElementById(
        "contract-amount"
    );


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


    // ==================================================
    // OPEN CONTRACT MODAL
    // ==================================================

    async function openContractModal(
        record = null
    ) {

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

                document.getElementById(
                    "contract-modal-title"
                ).textContent = "Edit Contract";

                contractForm.elements["name"].value =
                    record.name;

                contractType.value =
                    record.type;

                contractAmount.value = centsToEuros(
                    record.current_amount_cents
                );

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


    // ==================================================
    // SAVE CONTRACT
    // ==================================================

    contractForm.addEventListener(
        "submit",
        async event => {

            event.preventDefault();

            showError(
                "contract-error",
                ""
            );

            const data = Object.fromEntries(
                new FormData(
                    contractForm
                ).entries()
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
                contractForm.querySelector(
                    'button[type="submit"]'
                );

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


    // ==================================================
    // CANCEL CONTRACT
    // ==================================================

    document.querySelectorAll(
        ".cancel-contract"
    ).forEach(button => {

        button.addEventListener(
            "click",
            async () => {

                const id = button.dataset.id;

                if (!confirm(
                    "Cancel this contract?"
                )) {
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

            }
        );

    });


    // ==================================================
    // DELETE CONTRACT
    // ==================================================

    document.querySelectorAll(
        ".delete-contract"
    ).forEach(button => {

        button.addEventListener(
            "click",
            async () => {

                const id = button.dataset.id;

                const confirmed = confirm(
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

                    alert(error.message);
                }

            }
        );

    });


    // ==================================================
    // CONTRACT PRICE HISTORY
    // ==================================================

    const priceHistoryBody = document.getElementById(
        "price-history-body"
    );


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

        renderPriceHistory(
            result.prices
        );
    }


    // ==================================================
    // OPEN CHANGE PRICE MODAL
    // ==================================================

    document.querySelectorAll(
        ".change-contract-price"
    ).forEach(button => {

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

                document.getElementById(
                    "price-contract-name"
                ).textContent = contractName;

                document.getElementById(
                    "new-contract-price"
                ).value = centsToEuros(
                    currentAmount
                );

                document.getElementById(
                    "price-valid-from"
                ).value = localDateString();

                showError(
                    "price-error",
                    ""
                );

                priceHistoryBody.replaceChildren();

                priceModal.showModal();

                try {

                    await loadPriceHistory(
                        contractId
                    );

                } catch (error) {

                    showError(
                        "price-error",
                        error.message
                    );
                }

            }
        );

    });


    // ==================================================
    // SAVE CONTRACT PRICE
    // ==================================================

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
                new FormData(
                    priceForm
                ).entries()
            );

            const submitButton =
                priceForm.querySelector(
                    'button[type="submit"]'
                );

            submitButton.disabled = true;

            try {

                await apiRequest(
                    `/api/contracts/${contractId}/prices`,
                    "POST",
                    data
                );

                await loadPriceHistory(
                    contractId
                );

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


    // ==================================================
    // CONFIRM CONTRACT PAYMENT
    // ==================================================

    document.querySelectorAll(
        ".confirm-payment"
    ).forEach(button => {

        button.addEventListener(
            "click",
            async () => {

                const contractId =
                    button.dataset.contractId;

                const dueDate =
                    button.dataset.date;

                const scheduledAmount =
                    Number(button.dataset.amount);

                // Default to the historical price
                // applicable on the scheduled date.
                //
                // The user may enter a different amount
                // for this payment only.

                const amountInput = prompt(
                    `Confirm payment for ${dueDate}.\n\n` +
                    "Enter the actual amount (€):",
                    centsToEuros(scheduledAmount)
                );

                if (amountInput === null) {
                    return;
                }

                const amount = amountInput.trim();

                if (!amount) {

                    alert(
                        "Payment amount cannot be empty."
                    );

                    return;
                }

                const confirmed = confirm(
                    `Record payment of €${amount} ` +
                    `for ${dueDate}?`
                );

                if (!confirmed) {
                    return;
                }

                try {

                    await apiRequest(
                        `/api/contracts/${contractId}/payments`,
                        "POST",
                        {
                            due_date: dueDate,
                            override_amount: amount
                        }
                    );

                    window.location.reload();

                } catch (error) {

                    alert(error.message);
                }

            }
        );

    });


    // ==================================================
    // EDIT ACCOUNT
    // ==================================================

    document.querySelectorAll(
        ".edit-account"
    ).forEach(button => {

        button.addEventListener(
            "click",
            async () => {

                const id = button.dataset.id;

                const name = prompt(
                    "Account name:",
                    button.dataset.name
                );

                if (name === null) {
                    return;
                }

                const balance = prompt(
                    "Opening balance (€):",
                    centsToEuros(
                        Number(button.dataset.balance)
                    )
                );

                if (balance === null) {
                    return;
                }

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

            }
        );

    });


    // ==================================================
    // DELETE ACCOUNT
    // ==================================================

    document.querySelectorAll(
        ".delete-account"
    ).forEach(button => {

        button.addEventListener(
            "click",
            async () => {

                const id = button.dataset.id;

                if (!confirm(
                    "Permanently delete this account?"
                )) {
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

            }
        );

    });


    // ==================================================
    // EDIT CATEGORY
    // ==================================================

    document.querySelectorAll(
        ".edit-category"
    ).forEach(button => {

        button.addEventListener(
            "click",
            async () => {

                const id = button.dataset.id;

                const name = prompt(
                    "Category name:",
                    button.dataset.name
                );

                if (name === null) {
                    return;
                }

                const type = prompt(
                    "Category type (income / expense):",
                    button.dataset.type
                );

                if (type === null) {
                    return;
                }

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

            }
        );

    });


    // ==================================================
    // DELETE CATEGORY
    // ==================================================

    document.querySelectorAll(
        ".delete-category"
    ).forEach(button => {

        button.addEventListener(
            "click",
            async () => {

                const id = button.dataset.id;

                if (!confirm(
                    "Permanently delete this category?"
                )) {
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

            }
        );

    });


    // ==================================================
    // CLOSE DIALOGS
    // ==================================================

    document.querySelectorAll(
        "[data-close-dialog]"
    ).forEach(button => {

        button.addEventListener("click", () => {

            button.closest("dialog").close();

        });

    });


    // ==================================================
    // INITIAL STATE
    // ==================================================

    updateTransactionFields();

    updateContractCategories();

});