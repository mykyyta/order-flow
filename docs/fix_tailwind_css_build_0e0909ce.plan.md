---
name: Fix Tailwind CSS build
overview: The overall refactoring implementation (templates, views, URLs, forms, JS, Docker) is correct and consistent. The single root cause of "no styles" is a Tailwind v3/v4 syntax mismatch -- the project uses Tailwind v4.1.18 CLI but v3-era configuration syntax, resulting in a ~5.8KB CSS file that's missing most utility classes.
todos:
  - id: fix-input-css
    content: Update static/css/input.css from v3 @tailwind directives to v4 @import syntax with @theme block
    status: pending
  - id: rebuild-css
    content: Run make tw-build to regenerate app.css with all utility classes
    status: pending
  - id: cleanup-config
    content: Delete tailwind.config.js (no longer needed with v4 CSS-based config)
    status: pending
  - id: verify-docker
    content: Restart Docker container and verify styles render correctly
    status: pending
isProject: false
---

# Fix Tailwind CSS v3/v4 Syntax Mismatch

## Diagnosis

**Root cause:** The project downloads Tailwind **v4.1.18** standalone CLI, but both the input CSS and config file use **v3 syntax** that v4 does not fully support.

- [static/css/input.css](static/css/input.css) uses deprecated v3 directives:
  ```css
  @tailwind base;
  @tailwind components;
  @tailwind utilities;
  ```
- [tailwind.config.js](tailwind.config.js) uses v3-era `module.exports = { content, theme }` format, which v4 **does not read** unless explicitly referenced via `@config`.

**Result:** The generated [static/css/app.css](static/css/app.css) is only **5,867 bytes** and contains only a small subset of structural utilities (`.flex`, `.hidden`, `.grid`, etc.). All of the following are **completely missing**:

- Color classes: `bg-slate-50`, `text-slate-900`, `bg-white`, `text-teal-700`, `bg-emerald-100`, etc.
- Spacing classes: `px-4`, `py-2`, `p-2`, `m-0`, `gap-1`, `gap-3`, etc.
- Typography: `text-sm`, `text-lg`, `font-medium`, `font-sans`
- Sizing: `h-14`, `h-4`, `w-4`, `w-6`, `h-6`, `max-w-7xl`
- Border radius: `rounded-md`, `rounded-lg`, `rounded-full` (partial)
- Shadows: `shadow-sm`, `shadow-md`
- Responsive variants: `sm:px-6`, `md:flex`, `md:hidden`, `lg:px-8`, `md:grid-cols-6`

This explains why the page renders with no visible design.

## Implementation Audit (Everything Else is Correct)

The full codebase audit shows the refactoring is otherwise solid:

- **Templates** (16 files): All properly extend `base.html`, use consistent Tailwind classes, include partials correctly, load page-specific JS via `extra_js` block.
- **Views/URLs**: All `template_name` references match actual files; all `redirect()`/`reverse()` calls use valid URL names.
- **Old templates**: All cleaned up (only `base.html` remains at root `templates/` level).
- **Forms**: Tailwind widget classes applied in all 4 form classes.
- **Template tags**: `status_badge_class` and `message_alert_class` return full Tailwind utility strings.
- **JS**: 4 page-specific files extracted (`app.js`, `orders_active.js`, `orders_create.js`, `profile.js`).
- **Docker**: `collectstatic` runs before `runserver` in `docker-compose.yml` -- static files are served correctly at HTTP 200.

## Fix

Update [static/css/input.css](static/css/input.css) to Tailwind v4 syntax and embed theme customization directly in CSS (v4 approach), replacing the need for `tailwind.config.js`:

```css
@import "tailwindcss";

@theme {
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --color-primary: #0F766E;
  --color-accent: #F59E0B;
  --color-background: #F8FAFC;
  --color-surface: #ffffff;
}

.order-link {
  text-decoration: none;
  color: #64748b;
}
.order-link:hover {
  color: #334155;
}
```

Then:

1. Rebuild CSS: `make tw-build`
2. Delete the now-unnecessary [tailwind.config.js](tailwind.config.js) (optional, but recommended to avoid confusion)
3. Re-run `collectstatic` in Docker (or restart container with `docker compose up --build`)

The v4 standalone CLI automatically detects content files in the project directory -- no explicit `content: [...]` configuration is needed.