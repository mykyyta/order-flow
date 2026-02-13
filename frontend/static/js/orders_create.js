document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");
    if (!form) return;
    const submitButton = form.querySelector('button[type="submit"]');
    if (!submitButton) return;

    const productSelect = document.querySelector("#id_product");
    if (productSelect) {
        productSelect.addEventListener("change", function () {
            const value = (productSelect.value || "").trim();
            const url = new URL(window.location.href);
            if (value) {
                url.searchParams.set("product", value);
            } else {
                url.searchParams.delete("product");
            }
            window.location.href = url.toString();
        });
    }

    form.addEventListener("submit", function (event) {
        if (submitButton.disabled) {
            event.preventDefault();
            return;
        }
        submitButton.disabled = true;
        submitButton.textContent = "Опрацьовується...";
    });
});
