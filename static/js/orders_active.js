(function () {
    const transitionDataEl = document.getElementById("transition-map-data");
    const bulkStatusForm = document.getElementById("bulk-status-form");
    const selectAllCheckbox = document.getElementById("select-all-orders");
    const clearSelectionButton = document.getElementById("clear-selection-btn");
    const select = document.getElementById("new_status");
    const hint = document.getElementById("status-transition-hint");
    const applyStatusButton = document.getElementById("apply-status-btn");
    const checkboxes = Array.from(document.querySelectorAll(".js-order-checkbox"));
    let selectedLength = 0;

    if (!transitionDataEl || !bulkStatusForm || !select || !applyStatusButton || !clearSelectionButton) {
        return;
    }

    const transitionMap = JSON.parse(transitionDataEl.textContent);
    const options = Array.from(select.options);
    const initialOptions = options.map((option) => option.value);

    function intersectSets(statuses) {
        if (statuses.length === 0) {
            return new Set(initialOptions);
        }

        let allowed = null;
        statuses.forEach((status) => {
            const currentAllowed = new Set(transitionMap[status] || []);
            if (allowed === null) {
                allowed = currentAllowed;
                return;
            }
            allowed = new Set([...allowed].filter((value) => currentAllowed.has(value)));
        });
        return allowed || new Set();
    }

    function updateAllowedTransitions() {
        const selectedStatuses = checkboxes
            .filter((checkbox) => checkbox.checked)
            .map((checkbox) => checkbox.dataset.currentStatus);
        const allowed = intersectSets(selectedStatuses);
        selectedLength = selectedStatuses.length;

        options.forEach((option) => {
            option.disabled = !allowed.has(option.value);
        });

        applyStatusButton.disabled = selectedLength === 0;
        clearSelectionButton.disabled = selectedLength === 0;
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = selectedLength > 0 && selectedLength === checkboxes.length;
            selectAllCheckbox.indeterminate = selectedLength > 0 && selectedLength < checkboxes.length;
        }

        if (options.every((option) => option.disabled)) {
            hint.textContent = "Немає спільного дозволеного переходу для обраних замовлень.";
            return;
        }

        hint.textContent = "";
        if (select.selectedOptions.length === 0 || select.selectedOptions[0].disabled) {
            const firstEnabled = options.find((option) => !option.disabled);
            if (firstEnabled) {
                select.value = firstEnabled.value;
            }
        }
    }

    checkboxes.forEach((checkbox) => {
        checkbox.addEventListener("change", updateAllowedTransitions);
    });
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener("change", function () {
            checkboxes.forEach((checkbox) => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateAllowedTransitions();
        });
    }
    clearSelectionButton.addEventListener("click", function () {
        checkboxes.forEach((checkbox) => {
            checkbox.checked = false;
        });
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        }
        updateAllowedTransitions();
    });
    bulkStatusForm.addEventListener("submit", function (event) {
        if (selectedLength === 0) {
            event.preventDefault();
            return;
        }
        const selectedStatusLabel = select.selectedOptions[0]
            ? select.selectedOptions[0].textContent.trim()
            : "";
        const confirmed = window.confirm(
            `Змінити статус на "${selectedStatusLabel}" для ${selectedLength} замовлень?`
        );
        if (!confirmed) {
            event.preventDefault();
        }
    });

    updateAllowedTransitions();
})();
