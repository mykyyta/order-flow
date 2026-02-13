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

    const clearBtn = document.querySelector("[data-clear-colors]");
    if (clearBtn) {
        clearBtn.addEventListener("click", function () {
            const selects = form.querySelectorAll(
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

    form.addEventListener("submit", function (event) {
        if (submitButton.disabled) {
            event.preventDefault();
            return;
        }
        submitButton.disabled = true;
        submitButton.textContent = "Опрацьовується...";
    });
});
