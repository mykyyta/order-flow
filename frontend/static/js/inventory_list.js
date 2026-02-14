(function () {
    var toggles = Array.from(document.querySelectorAll("[data-toggle-inventory-meta]"));
    if (!toggles.length) return;

    var storageKey = "pult_inventory_meta_visible";
    var metaEls = Array.from(document.querySelectorAll(".js-inv-meta"));

    if (!metaEls.length) {
        toggles.forEach(function (toggle) {
            toggle.checked = false;
            toggle.disabled = true;
        });
        return;
    }

    function setMetaVisible(isVisible) {
        metaEls.forEach(function (el) {
            el.classList.toggle("hidden", !isVisible);
        });
    }

    function syncToggles(isOn) {
        toggles.forEach(function (toggle) {
            toggle.checked = isOn;
        });
    }

    function persist(isOn) {
        try {
            window.localStorage.setItem(storageKey, isOn ? "1" : "0");
        } catch (e) {
            // ignore
        }
    }

    function loadPersisted() {
        try {
            var raw = window.localStorage.getItem(storageKey);
            if (raw === "1") return true;
            if (raw === "0") return false;
        } catch (e) {
            // ignore
        }
        return null;
    }

    function apply(isOn) {
        syncToggles(isOn);
        setMetaVisible(isOn);
        persist(isOn);
    }

    var persisted = loadPersisted();
    var initial = persisted !== null ? persisted : toggles.some(function (t) { return t.checked; });
    apply(initial);

    toggles.forEach(function (toggle) {
        toggle.addEventListener("change", function () {
            apply(toggle.checked);
        });
    });
})();
