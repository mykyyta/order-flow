function parseRgb(value) {
  if (!value) return null;
  var m = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
  if (!m) return null;
  return { r: Number(m[1]), g: Number(m[2]), b: Number(m[3]) };
}

function rgbToHex(rgb) {
  function toHex(n) {
    var h = Math.max(0, Math.min(255, Math.round(n))).toString(16);
    return h.length === 1 ? "0" + h : h;
  }
  return "#" + toHex(rgb.r) + toHex(rgb.g) + toHex(rgb.b);
}

function hexToRgb(hex) {
  if (!hex) return null;
  var h = String(hex).trim();
  if (!/^#?[0-9a-f]{6}$/i.test(h)) return null;
  if (h[0] !== "#") h = "#" + h;
  return {
    r: parseInt(h.slice(1, 3), 16),
    g: parseInt(h.slice(3, 5), 16),
    b: parseInt(h.slice(5, 7), 16),
  };
}

function relativeLuminance(rgb) {
  function toLinear(c) {
    var v = c / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  }
  var r = toLinear(rgb.r);
  var g = toLinear(rgb.g);
  var b = toLinear(rgb.b);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(fgRgb, bgRgb) {
  var L1 = relativeLuminance(fgRgb);
  var L2 = relativeLuminance(bgRgb);
  var lighter = Math.max(L1, L2);
  var darker = Math.min(L1, L2);
  return (lighter + 0.05) / (darker + 0.05);
}

function closestSolidBackground(el) {
  var current = el;
  while (current && current !== document.documentElement) {
    var bg = window.getComputedStyle(current).backgroundColor;
    if (bg && !bg.includes("rgba(0, 0, 0, 0)") && bg !== "transparent") return bg;
    current = current.parentElement;
  }
  return window.getComputedStyle(document.body).backgroundColor || "rgb(255,255,255)";
}

function updateContrastReadouts() {
  document.querySelectorAll("[data-contrast]").forEach(function (el) {
    var fg = window.getComputedStyle(el).color;
    var bg = closestSolidBackground(el);
    var fgRgb = parseRgb(fg);
    var bgRgb = parseRgb(bg);
    if (!fgRgb || !bgRgb) return;

    var ratio = contrastRatio(fgRgb, bgRgb);
    var out = el.parentElement ? el.parentElement.querySelector("[data-contrast-out]") : null;
    if (!out) return;

    var ok = ratio >= 4.5;
    out.textContent = "contrast " + ratio.toFixed(2) + ":1 " + (ok ? "✓ AA" : "✕");
    out.className = ok ? "text-xs text-emerald-700" : "text-xs text-rose-700";
  });
}

function getCssVar(name) {
  return window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function setInlineVar(name, value) {
  document.documentElement.style.setProperty(name, value);
}

function clearInlineVar(name) {
  document.documentElement.style.removeProperty(name);
}

function loadOverrides() {
  try {
    var raw = window.localStorage.getItem("palette_overrides");
    if (!raw) return null;
    var parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    return parsed;
  } catch (_err) {
    return null;
  }
}

function saveOverrides(overrides) {
  try {
    window.localStorage.setItem("palette_overrides", JSON.stringify(overrides));
  } catch (_err) {}
}

function deleteOverrides() {
  try {
    window.localStorage.removeItem("palette_overrides");
  } catch (_err) {}
}

function currentTheme() {
  return document.documentElement.getAttribute("data-theme") || "default";
}

function initPaletteEditor() {
  var theme = currentTheme();
  var hint = document.getElementById("overrides-hint");

  var controls = [
    { id: "pick-brand", varName: "--of-brand" },
    { id: "pick-info", varName: "--of-info" },
    { id: "pick-success", varName: "--of-success" },
    { id: "pick-warning", varName: "--of-warning" },
    { id: "pick-danger", varName: "--of-danger" },
  ];

  function setHint(text) {
    if (!hint) return;
    hint.textContent = text || "";
  }

  function applyOverridesForTheme(overrides, themeName) {
    if (!overrides || !overrides[themeName]) return;
    var themeOverrides = overrides[themeName];
    controls.forEach(function (c) {
      if (typeof themeOverrides[c.varName] === "string") {
        setInlineVar(c.varName, themeOverrides[c.varName]);
      }
    });
  }

  function refreshPickersFromComputed() {
    controls.forEach(function (c) {
      var input = document.getElementById(c.id);
      if (!input) return;
      var computed = getCssVar(c.varName);
      if (!computed) return;

      if (/^#([0-9a-f]{6})$/i.test(computed)) {
        input.value = computed;
        return;
      }
      var rgb = parseRgb(computed);
      if (rgb) input.value = rgbToHex(rgb);
    });
  }

  if (theme !== "soft_indigo" && theme !== "soft_warm") {
    setHint("Увімкни ?theme=soft_indigo або ?theme=soft_warm, щоб редагувати базові кольори.");
    refreshPickersFromComputed();
    return;
  }

  var overrides = loadOverrides() || {};
  applyOverridesForTheme(overrides, theme);
  refreshPickersFromComputed();

  controls.forEach(function (c) {
    var input = document.getElementById(c.id);
    if (!input) return;

    input.addEventListener("input", function () {
      var value = input.value;
      var rgb = hexToRgb(value);
      if (!rgb) return;

      setInlineVar(c.varName, value);
      overrides[theme] = overrides[theme] || {};
      overrides[theme][c.varName] = value;
      saveOverrides(overrides);
      setHint("Збережено для теми: " + theme);
      updateContrastReadouts();
    });
  });

  var resetBtn = document.getElementById("btn-reset-overrides");
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      controls.forEach(function (c) {
        clearInlineVar(c.varName);
      });
      deleteOverrides();
      setHint("Reset: очищено overrides (localStorage).");
      refreshPickersFromComputed();
      updateContrastReadouts();
    });
  }
}

document.addEventListener("DOMContentLoaded", function () {
  initPaletteEditor();
  updateContrastReadouts();

  // Re-check contrast after a theme change via ?theme=...
  setTimeout(updateContrastReadouts, 50);
});

