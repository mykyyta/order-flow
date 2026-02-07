document.addEventListener("DOMContentLoaded", function () {
  // Theme preview: set ?theme=dune_lite (or theme=default to clear).
  // Persists in localStorage to make iteration easy without refactoring templates.
  (function () {
    var params = new URLSearchParams(window.location.search);
    var themeParam = params.get("theme");
    var stored = null;
    try {
      stored = window.localStorage.getItem("theme");
    } catch (_err) {
      stored = null;
    }

    var theme = themeParam || stored;
    if (!theme) return;

    if (theme === "default" || theme === "none") {
      document.documentElement.removeAttribute("data-theme");
      try {
        window.localStorage.removeItem("theme");
      } catch (_err) {}
      return;
    }

    document.documentElement.setAttribute("data-theme", theme);
    if (themeParam) {
      try {
        window.localStorage.setItem("theme", themeParam);
      } catch (_err) {}
    }
  })();

  var toggle = document.getElementById("nav-toggle");
  var menu = document.getElementById("nav-menu");
  var iconMenu = document.getElementById("icon-menu");
  var iconClose = document.getElementById("icon-close");

  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
      menu.classList.toggle("hidden");
      if (iconMenu && iconClose) {
        iconMenu.classList.toggle("hidden");
        iconClose.classList.toggle("hidden");
      }
    });
  }

  /* Custom dropdown for .form-select — styled options list */
  function enhanceFormSelect(select) {
    if (select.closest(".form-select-wrap")) return;
    var wrap = document.createElement("div");
    wrap.className = "form-select-wrap";
    select.classList.add("form-select-native");
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);

    var trigger = document.createElement("div");
    trigger.className = "form-select-trigger";
    trigger.setAttribute("role", "button");
    trigger.setAttribute("tabindex", "0");
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    var selectedOption = select.options[select.selectedIndex];
    trigger.textContent = selectedOption ? selectedOption.textContent.trim() : "";

    var dropdown = document.createElement("div");
    dropdown.className = "form-select-dropdown hidden";
    dropdown.setAttribute("role", "listbox");
    dropdown.setAttribute("aria-hidden", "true");
    for (var i = 0; i < select.options.length; i++) {
      var opt = select.options[i];
      var div = document.createElement("div");
      div.className = "form-select-option";
      div.setAttribute("role", "option");
      div.setAttribute("data-value", opt.value);
      div.textContent = opt.textContent.trim();
      if (opt.selected) div.setAttribute("aria-selected", "true");
      if (opt.disabled) div.classList.add("disabled");
      dropdown.appendChild(div);
    }

    wrap.appendChild(trigger);
    wrap.appendChild(dropdown);

    function syncDisabled() {
      for (var i = 0; i < select.options.length; i++) {
        var opt = select.options[i];
        var el = dropdown.querySelector(".form-select-option[data-value=\"" + opt.value + "\"]");
        if (el) {
          if (opt.disabled) el.classList.add("disabled");
          else el.classList.remove("disabled");
        }
      }
    }
    function open() {
      syncDisabled();
      dropdown.classList.remove("hidden");
      dropdown.setAttribute("aria-hidden", "false");
      trigger.setAttribute("aria-expanded", "true");
      document.addEventListener("click", closeOnOutside);
    }
    function close() {
      dropdown.classList.add("hidden");
      dropdown.setAttribute("aria-hidden", "true");
      trigger.setAttribute("aria-expanded", "false");
      document.removeEventListener("click", closeOnOutside);
    }
    function closeOnOutside(e) {
      if (!wrap.contains(e.target)) close();
    }
    function choose(optionEl) {
      if (optionEl.classList.contains("disabled")) return;
      var val = optionEl.getAttribute("data-value");
      select.value = val;
      trigger.textContent = optionEl.textContent.trim();
      dropdown.querySelectorAll(".form-select-option").forEach(function (o) {
        o.removeAttribute("aria-selected");
        if (o.getAttribute("data-value") === val) o.setAttribute("aria-selected", "true");
      });
      close();
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }

    trigger.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (trigger.getAttribute("aria-expanded") === "true") close();
      else open();
    });
    trigger.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        trigger.click();
      }
      if (e.key === "Escape") close();
    });
    dropdown.querySelectorAll(".form-select-option").forEach(function (optionEl) {
      optionEl.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        choose(optionEl);
      });
    });

    select.addEventListener("change", function () {
      var selectedOption = select.options[select.selectedIndex];
      trigger.textContent = selectedOption ? selectedOption.textContent.trim() : "";
      dropdown.querySelectorAll(".form-select-option").forEach(function (o) {
        o.removeAttribute("aria-selected");
        if (o.getAttribute("data-value") === select.value) o.setAttribute("aria-selected", "true");
      });
    });
  }

  document.querySelectorAll("select.form-select").forEach(enhanceFormSelect);
});
