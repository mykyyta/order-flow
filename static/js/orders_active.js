(function () {
    var transitionDataEl = document.getElementById("transition-map-data");
    var bulkStatusForm = document.getElementById("bulk-status-form");
    var clearSelectionButton = document.getElementById("clear-selection-btn");
    var select = document.getElementById("new_status");
    var hint = document.getElementById("status-transition-hint");
    var applyStatusButton = document.getElementById("apply-status-btn");
    var checkboxes = Array.from(document.querySelectorAll(".js-order-checkbox"));
    var selectAllCheckboxes = [
        document.getElementById("select-all-orders"),
        document.getElementById("select-all-orders-mobile"),
    ].filter(Boolean);
    var selectedLength = 0;

    if (!transitionDataEl || !bulkStatusForm || !select || !applyStatusButton || !clearSelectionButton) {
        return;
    }

    var transitionMap = JSON.parse(transitionDataEl.textContent);
    var options = Array.from(select.options);
    var initialOptions = options.map(function (option) { return option.value; }).filter(function (v) { return v !== ""; });
    var bulkActionBar = document.getElementById("bulk-action-bar");

    function intersectSets(statuses) {
        if (statuses.length === 0) {
            return new Set(initialOptions);
        }
        var allowed = null;
        statuses.forEach(function (status) {
            var currentAllowed = new Set(transitionMap[status] || []);
            if (allowed === null) {
                allowed = currentAllowed;
                return;
            }
            allowed = new Set([].concat(Array.from(allowed)).filter(function (v) { return currentAllowed.has(v); }));
        });
        return allowed || new Set();
    }

    function syncSelectAll() {
        selectAllCheckboxes.forEach(function (cb) {
            cb.checked = selectedLength > 0 && selectedLength === checkboxes.length;
            cb.indeterminate = selectedLength > 0 && selectedLength < checkboxes.length;
        });
    }

    function updateAllowedTransitions() {
        var selectedStatuses = checkboxes
            .filter(function (cb) { return cb.checked; })
            .map(function (cb) { return cb.dataset.currentStatus; });
        var allowed = intersectSets(selectedStatuses);
        selectedLength = selectedStatuses.length;

        if (bulkActionBar) {
            bulkActionBar.classList.toggle("hidden", selectedLength === 0);
        }
        select.disabled = selectedLength === 0;

        options.forEach(function (option) {
            if (option.value === "") return;
            option.disabled = !allowed.has(option.value);
        });

        applyStatusButton.disabled = selectedLength === 0 || select.value === "";
        clearSelectionButton.disabled = selectedLength === 0;
        syncSelectAll();

        if (selectedLength > 0 && options.filter(function (o) { return o.value !== ""; }).every(function (option) { return option.disabled; })) {
            hint.textContent = "Для обраних замовлень немає спільного наступного статусу.";
        } else {
            hint.textContent = "";
        }
    }

    select.addEventListener("change", function () {
        applyStatusButton.disabled = selectedLength === 0 || select.value === "";
    });

    checkboxes.forEach(function (checkbox) {
        checkbox.addEventListener("change", updateAllowedTransitions);
    });

    selectAllCheckboxes.forEach(function (selectAllCb) {
        selectAllCb.addEventListener("change", function () {
            var checked = selectAllCb.checked;
            checkboxes.forEach(function (cb) { cb.checked = checked; });
            selectAllCheckboxes.forEach(function (cb) { cb.checked = checked; cb.indeterminate = false; });
            updateAllowedTransitions();
        });
    });

    clearSelectionButton.addEventListener("click", function () {
        checkboxes.forEach(function (cb) { cb.checked = false; });
        selectAllCheckboxes.forEach(function (cb) { cb.checked = false; cb.indeterminate = false; });
        updateAllowedTransitions();
    });

    var modal = document.getElementById("bulk-status-confirm-modal");
    var modalMessage = modal ? document.getElementById("bulk-status-confirm-modal-message") : null;
    var modalConfirm = modal ? modal.querySelector(".js-modal-confirm") : null;
    var modalCancel = modal ? modal.querySelector(".js-modal-cancel") : null;
    var pendingSubmit = false;

    function closeModal() {
        if (modal) {
            modal.setAttribute("aria-hidden", "true");
            modal.classList.add("hidden");
        }
    }
    function openModal(message) {
        if (modal && modalMessage) {
            modalMessage.textContent = message;
            modal.setAttribute("aria-hidden", "false");
            modal.classList.remove("hidden");
        }
    }

    if (modal) {
        modal.addEventListener("click", function (e) {
            if (e.target === modal) closeModal();
        });
        if (modalCancel) modalCancel.addEventListener("click", closeModal);
        if (modalConfirm) {
            modalConfirm.addEventListener("click", function () {
                pendingSubmit = true;
                closeModal();
                bulkStatusForm.submit();
            });
        }
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && modal.getAttribute("aria-hidden") === "false") closeModal();
        });
    }

    bulkStatusForm.addEventListener("submit", function (event) {
        if (selectedLength === 0 || select.value === "") {
            event.preventDefault();
            return;
        }
        if (pendingSubmit) {
            pendingSubmit = false;
            return;
        }
        event.preventDefault();
        var selectedStatusLabel = select.selectedOptions[0]
            ? select.selectedOptions[0].textContent.trim()
            : "";
        var message = 'Міняємо статус на "' + selectedStatusLabel + '" для ' + selectedLength + " замовлень?";
        openModal(message);
    });

    updateAllowedTransitions();
})();
