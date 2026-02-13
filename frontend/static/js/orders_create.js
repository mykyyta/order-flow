document.addEventListener("DOMContentLoaded", function () {
    const productSelect = document.querySelector("#id_product");
    const orderForm = document.querySelector("form[data-order-create-form]");
    const productSelectForm = document.querySelector("form[data-product-select-form]");
    const productSubmit = document.querySelector("[data-product-select-submit]");
    const changeProductLink = document.querySelector("[data-change-product]");

    function isFormDirty(formEl) {
        if (!formEl) return false;
        const els = Array.from(formEl.elements || []);
        for (let i = 0; i < els.length; i++) {
            const el = els[i];
            if (!el || !el.name) continue;
            if (el.name === "csrfmiddlewaretoken") continue;
            if (el.disabled) continue;
            if (el.tagName === "SELECT") {
                if ((el.value || "").trim() !== "") return true;
                continue;
            }
            if (el.type === "checkbox") {
                if (el.checked) return true;
                continue;
            }
            if (el.tagName === "TEXTAREA" || el.type === "text" || el.type === "number") {
                if ((el.value || "").trim() !== "") return true;
            }
        }
        return false;
    }

    if (changeProductLink && orderForm) {
        changeProductLink.addEventListener("click", function (event) {
            if (!isFormDirty(orderForm)) return;
            const ok = window.confirm("Введені дані буде втрачено. Продовжити?");
            if (!ok) event.preventDefault();
        });
    }

    if (productSubmit && productSelect) {
        productSubmit.disabled = !(productSelect.value || "").trim();
        productSelect.addEventListener("change", function () {
            productSubmit.disabled = !(productSelect.value || "").trim();
        });
    }

    if (orderForm) {
        const submitButton = orderForm.querySelector('button[type="submit"]');
        if (submitButton) {
            orderForm.addEventListener("submit", function (event) {
                if (submitButton.disabled) {
                    event.preventDefault();
                    return;
                }
                submitButton.disabled = true;
                submitButton.textContent = "Опрацьовується...";
            });
        }
    }
});
