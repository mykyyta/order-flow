document.addEventListener("DOMContentLoaded", function () {
  function $(selector, root) {
    return (root || document).querySelector(selector);
  }

  /* Modal confirmation (global) */
  var confirmModal = document.getElementById("global-confirm-modal");
  var confirmTitle = confirmModal ? $("#global-confirm-modal-title", confirmModal) : null;
  var confirmMessage = confirmModal ? $("#global-confirm-modal-message", confirmModal) : null;
  var confirmButton = confirmModal ? $(".js-modal-confirm", confirmModal) : null;
  var cancelButton = confirmModal ? $(".js-modal-cancel", confirmModal) : null;

  var confirmDefaults = {
    title: confirmTitle ? confirmTitle.textContent : "",
    confirmLabel: confirmButton ? confirmButton.textContent : "",
    cancelLabel: cancelButton ? cancelButton.textContent : "",
  };
  var pendingConfirmAction = null;
  var pendingCancelAction = null;
  var pendingFocusRestore = null;

  /* Show loading overlay on same-origin navigation (links and forms) so user gets immediate feedback on tap */
  function isSameOrigin(url) {
    if (!url || url.startsWith("#")) return false;
    try {
      var a = document.createElement("a");
      a.href = url;
      return a.hostname === window.location.hostname && a.protocol === window.location.protocol;
    } catch (_) {
      return false;
    }
  }
  function showNavLoading() {
    if (document.querySelector(".modal-overlay:not(.hidden)")) return;
    document.body.classList.add("navigating");
    var overlay = document.getElementById("nav-loading-overlay");
    if (overlay) overlay.setAttribute("aria-hidden", "false");
  }
  function hideNavLoading() {
    document.body.classList.remove("navigating");
    var overlay = document.getElementById("nav-loading-overlay");
    if (overlay) overlay.setAttribute("aria-hidden", "true");
  }
  window.hideNavLoading = hideNavLoading;
  window.showNavLoading = showNavLoading;

  function closeConfirmModal() {
    if (!confirmModal) return;
    confirmModal.setAttribute("aria-hidden", "true");
    confirmModal.classList.add("hidden");
    pendingConfirmAction = null;
    pendingCancelAction = null;
    if (confirmTitle) confirmTitle.textContent = confirmDefaults.title;
    if (confirmButton) confirmButton.textContent = confirmDefaults.confirmLabel;
    if (cancelButton) cancelButton.textContent = confirmDefaults.cancelLabel;
    if (pendingFocusRestore && typeof pendingFocusRestore.focus === "function") {
      pendingFocusRestore.focus();
    }
    pendingFocusRestore = null;
  }

  function openConfirmModal(opts) {
    if (!confirmModal || !confirmMessage) return;
    if (typeof window.hideNavLoading === "function") window.hideNavLoading();

    confirmMessage.textContent = (opts && opts.message) || "";
    if (confirmTitle) confirmTitle.textContent = (opts && opts.title) || confirmDefaults.title;
    if (confirmButton) {
      confirmButton.textContent =
        (opts && opts.confirmLabel) || confirmDefaults.confirmLabel || "Так";
    }
    if (cancelButton) {
      cancelButton.textContent =
        (opts && opts.cancelLabel) || confirmDefaults.cancelLabel || "Скасувати";
    }

    confirmModal.setAttribute("aria-hidden", "false");
    confirmModal.classList.remove("hidden");
    if (confirmButton) confirmButton.focus();
  }

  // Promise API for custom scripts (e.g. create order dirty form warning).
  window.pultConfirm = function (opts) {
    return new Promise(function (resolve) {
      if (!confirmModal) {
        resolve(window.confirm((opts && opts.message) || "Продовжити?"));
        return;
      }
      pendingFocusRestore = document.activeElement;
      pendingConfirmAction = function () {
        resolve(true);
      };
      pendingCancelAction = function () {
        resolve(false);
      };
      openConfirmModal(opts);
    });
  };

  if (confirmModal) {
    confirmModal.addEventListener("click", function (e) {
      if (e.target !== confirmModal) return;
      var onCancel = pendingCancelAction;
      closeConfirmModal();
      if (typeof onCancel === "function") onCancel();
    });
    if (cancelButton) {
      cancelButton.addEventListener("click", function () {
        var onCancel = pendingCancelAction;
        closeConfirmModal();
        if (typeof onCancel === "function") onCancel();
      });
    }
    if (confirmButton) {
      confirmButton.addEventListener("click", function () {
        var action = pendingConfirmAction;
        closeConfirmModal();
        if (typeof action === "function") action();
      });
    }
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && confirmModal.getAttribute("aria-hidden") === "false") {
        var onCancel = pendingCancelAction;
        closeConfirmModal();
        if (typeof onCancel === "function") onCancel();
      }
    });
  }

  // Capture phase to prevent nav-loading from showing before we open the modal.
  document.addEventListener(
    "click",
    function (e) {
      if (!confirmModal) return;
      if (e.button !== 0) return;
      var el = e.target.closest("[data-confirm]");
      if (!el) return;
      if (el.closest(".modal-overlay")) return;

      var message = (el.getAttribute("data-confirm") || "").trim();
      if (!message) return;

      e.preventDefault();
      e.stopImmediatePropagation();

      var title = el.getAttribute("data-confirm-title") || confirmDefaults.title;
      var confirmLabel = el.getAttribute("data-confirm-confirm-label") || confirmDefaults.confirmLabel;
      var cancelLabel = el.getAttribute("data-confirm-cancel-label") || confirmDefaults.cancelLabel;

      pendingFocusRestore = el;
      pendingConfirmAction = function () {
        // If inside a form button, submit that form.
        var form = el.closest("form");
        if (form) {
          var action = (form.getAttribute("action") || "").trim();
          if (!action || action === "#") action = window.location.href;
          if (isSameOrigin(action)) showNavLoading();
          form.submit();
          return;
        }
        // Otherwise navigate if it's a link.
        if (el.tagName === "A" && el.href) {
          if (isSameOrigin(el.href)) showNavLoading();
          window.location.href = el.href;
        }
      };
      pendingCancelAction = function () {};
      openConfirmModal({ message: message, title: title, confirmLabel: confirmLabel, cancelLabel: cancelLabel });
    },
    true
  );

  document.addEventListener("click", function (e) {
    var link = e.target.closest("a[href]");
    if (!link) return;
    if (link.target === "_blank" || link.hasAttribute("download")) return;
    if (link.getAttribute("href") && link.getAttribute("href").startsWith("#")) return;
    if (link.closest("[data-no-nav-loading]")) return;
    if (isSameOrigin(link.href)) showNavLoading();
  }, true);
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form || form.tagName !== "FORM") return;
    if (form.closest("[data-no-nav-loading]")) return;
    var action = (form.getAttribute("action") || "").trim();
    if (!action || action === "#") action = window.location.href;
    if (isSameOrigin(action)) showNavLoading();
  }, true);

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

  /* Custom dropdown for .form-select — positioned fixed to avoid overflow clipping */
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

    function positionDropdown() {
      var rect = trigger.getBoundingClientRect();
      var maxHeight = 240;
      var spaceBelow = window.innerHeight - rect.bottom;
      var spaceAbove = rect.top;
      var openUp = spaceBelow < maxHeight && spaceAbove > spaceBelow;
      if (openUp) {
        dropdown.style.top = (rect.top - maxHeight - 4) + "px";
        dropdown.style.maxHeight = maxHeight + "px";
        dropdown.classList.add("form-select-dropdown--up");
      } else {
        dropdown.style.top = (rect.bottom + 4) + "px";
        dropdown.style.maxHeight = "";
        dropdown.classList.remove("form-select-dropdown--up");
      }
      dropdown.style.left = rect.left + "px";
      dropdown.style.width = rect.width + "px";
    }

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
      document.body.appendChild(dropdown);
      positionDropdown();
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
      wrap.appendChild(dropdown);
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
