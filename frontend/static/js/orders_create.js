document.addEventListener("DOMContentLoaded", function () {
    const productSelect = document.querySelector("#id_product");
    const orderForm = document.querySelector("form[data-order-create-form]");

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

    if (productSelect) {
        let lastProductValue = (productSelect.value || "").trim();
        productSelect.addEventListener("change", function () {
            const nextValue = (productSelect.value || "").trim();
            if (orderForm && isFormDirty(orderForm)) {
                const ok = window.confirm("Введені дані буде втрачено. Продовжити?");
                if (!ok) {
                    productSelect.value = lastProductValue;
                    return;
                }
            }

            const url = new URL(window.location.href);
            if (nextValue) {
                url.searchParams.set("product", nextValue);
            } else {
                url.searchParams.delete("product");
            }
            window.location.href = url.toString();
            lastProductValue = nextValue;
        });
    }

    const clearBtn = document.querySelector("[data-clear-colors]");
    if (clearBtn && orderForm) {
        clearBtn.addEventListener("click", function () {
            const selects = orderForm.querySelectorAll(
                'select[name="primary_material_color"],' +
                    'select[name="secondary_material_color"],' +
                    'select[name$="_primary_material_color"],' +
                    'select[name$="_secondary_material_color"]'
            );
            selects.forEach(function (sel) {
                sel.value = "";
                sel.dispatchEvent(new Event("change", { bubbles: true }));
            });
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
