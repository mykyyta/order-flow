document.addEventListener("DOMContentLoaded", function () {
    const usernameInput = document.getElementById("username");
    const saveButton = document.getElementById("saveButton");
    const profileForm = document.getElementById("profileForm");

    if (!usernameInput || !saveButton || !profileForm) return;

    const initialUsername = usernameInput.value;

    usernameInput.addEventListener("input", function () {
        if (usernameInput.value.trim() && usernameInput.value !== initialUsername) {
            saveButton.disabled = false;
        } else {
            saveButton.disabled = true;
        }
    });

    profileForm.addEventListener("submit", function () {
        saveButton.disabled = true;
        saveButton.textContent = "Оновлення...";
    });
});
