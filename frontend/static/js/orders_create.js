document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");
    if (!form) return;
    const submitButton = form.querySelector('button[type="submit"]');
    if (!submitButton) return;

    form.addEventListener("submit", function (event) {
        if (submitButton.disabled) {
            event.preventDefault();
            return;
        }
        submitButton.disabled = true;
        submitButton.textContent = "Опрацьовується...";
    });
});
