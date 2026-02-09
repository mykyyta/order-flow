document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("profileForm");
    const usernameInput = document.getElementById("username");
    const themeSelect = document.getElementById("theme");
    const saveButton = document.getElementById("saveButton");
    const notifyOrderCreated = document.getElementById("notify_order_created");
    const notifyOrderCreatedPause = document.getElementById("notify_order_created_pause");
    const notifyOrderFinished = document.getElementById("notify_order_finished");

    if (!form || !usernameInput || !saveButton) return;

    const initialUsername = usernameInput.value;
    const initialTheme = themeSelect ? themeSelect.value : null;
    const initialNotifyCreated = notifyOrderCreated ? notifyOrderCreated.checked : false;
    const initialNotifyPause = notifyOrderCreatedPause ? notifyOrderCreatedPause.checked : false;
    const initialNotifyFinished = notifyOrderFinished ? notifyOrderFinished.checked : false;

    function hasChanges() {
        const usernameChanged = usernameInput.value.trim() && usernameInput.value !== initialUsername;
        const themeChanged = themeSelect && themeSelect.value !== initialTheme;
        const notifyChanged =
            (notifyOrderCreated && notifyOrderCreated.checked !== initialNotifyCreated) ||
            (notifyOrderCreatedPause && notifyOrderCreatedPause.checked !== initialNotifyPause) ||
            (notifyOrderFinished && notifyOrderFinished.checked !== initialNotifyFinished);
        return usernameChanged || themeChanged || notifyChanged;
    }

    function updateSaveButton() {
        saveButton.disabled = !hasChanges();
    }

    usernameInput.addEventListener("input", updateSaveButton);

    if (themeSelect) {
        themeSelect.addEventListener("change", function () {
            const theme = themeSelect.value;
            if (theme) {
                document.documentElement.setAttribute("data-theme", theme);
            } else {
                document.documentElement.removeAttribute("data-theme");
            }
            updateSaveButton();
        });
    }

    [notifyOrderCreated, notifyOrderCreatedPause, notifyOrderFinished].forEach(function (el) {
        if (el) el.addEventListener("change", updateSaveButton);
    });

    form.addEventListener("submit", function () {
        saveButton.disabled = true;
        saveButton.textContent = "Оновлення...";
    });
});
