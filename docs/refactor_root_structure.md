# Рефакторинг структури кореневої папки

У корені зараз багато елементів: Django-проєкт (config, apps, templates, static, assets), інфра (infra/), CI (.github/), скрипти (scripts/), документація (docs/), Docker, makefile тощо. Нижче — варіанти, як це згрупувати.

---

## Поточний стан (корінь)

```
pult/
├── .github/workflows/
├── accounts/          # Django app
├── assets/tailwind/   # CSS sources
├── catalog/           # Django app
├── config/            # Django project
├── docs/
├── infra/             # Terraform
├── orders/            # Django app
├── scripts/
├── static/
├── templates/
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── makefile
├── pyproject.toml
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── .dockerignore
├── .pre-commit-config.yaml
└── ...
```

---

## Варіант A: «Django у `app/`» (найбільш чистий корінь)

Вся Django-частина переїжджає в одну папку `app/`. У корені лишаються тільки інфра, CI, доки, скрипти та конфіги.

**Після:**

```
pult/
├── app/                    # весь Django-проєкт
│   ├── config/
│   ├── accounts/
│   ├── catalog/
│   ├── orders/
│   ├── templates/
│   ├── static/
│   ├── assets/
│   ├── manage.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pyproject.toml
├── .github/
├── docs/
├── infra/
├── scripts/
├── docker-compose.yml
├── Dockerfile
├── makefile
├── README.md
├── .env.example
├── .gitignore
└── ...
```

**Плюси:** у корені одразу видно «додаток vs інфра vs доки»; зручно, якщо з’являться інші сервіси (наприклад окремий frontend).  
**Мінуси:** треба оновити шляхи в Django (BASE_DIR), Dockerfile, docker-compose, makefile, CI, можливо pre-commit.

**Що міняти:**
- `config/settings/base.py`: `BASE_DIR = Path(__file__).resolve().parent.parent.parent` → `parent.parent` (корінь = `app/`).
- `Dockerfile`: `WORKDIR /app`, далі `COPY app/ ./` або окремо копіювати вміст `app/` у `/app` (щоб у контейнері було `manage.py`, `config/` тощо в корені робочої директорії).
- `docker-compose`: `volumes: - .:/app` → монтувати підпапку, напр. `.:/app` з контекстом, що код тепер у `app/` (або змінити `WORKDIR` і монтувати `./app:/app`).
- Makefile: команди з `manage.py` — шлях `app/manage.py` або `cd app && python manage.py`.
- CI (`.github/workflows`): якщо там є `python manage.py` / `pytest` — вказати робочу директорію `app/`.
- Pre-commit / Ruff: якщо шляхи до коду захардкодені — замінити на `app/`.

---

## Варіант B: Залишити Django в корені, згрупувати «операційне»

Не чіпаємо Django і `manage.py`, лише збираємо все «не-додаток» в одну-дві папки.

**Приклад 1 — одна папка `ops/` (або `devops/`):**

```
pult/
├── infra/       # залишається окремо (Terraform часто дивляться саме infra/)
├── ops/         # CI, скрипти, можливо частина доків
│   ├── .github/   → або залишити .github у корені (GitHub очікує .github)
│   ├── scripts/
│   └── ...
```

**Увага:** `.github` зазвичай лишають у корені репо, бо GitHub шукає workflow’и саме там. Тому реально «згрупувати» виходить тільки `scripts/` (наприклад у `ops/scripts` або залишити як є).

**Приклад 2 — тільки перейменування / переміщення дрібниць:**

- `assets/` → залишити (або перемістити в `static/sources/` / `frontend/` якщо хочете підкреслити, що це «сирці фронту»).
- Скрипти: `scripts/` → `scripts/` або `tooling/`, без зміни структури Django.

**Плюси:** мінімум змін, все продовжує працювати.  
**Мінуси:** у корені лишається багато папок (config, accounts, catalog, orders, templates, static, docs, infra, scripts).

---

## Варіант C: Групувати тільки фронт-активи

Зменшити кількість папок у корені за рахунок об’єднання `templates/`, `static/`, `assets/` під однією назвою (наприклад `frontend/` або залишити як є, але `assets` перемістити всередину `static/`).

**Приклад:**

```
pult/
├── frontend/           # або залишити templates + static окремо
│   ├── templates/
│   ├── static/
│   └── sources/       # було assets/tailwind
├── config/
├── accounts/
├── catalog/
├── orders/
...
```

**Що міняти:** Django `TEMPLATES['DIRS']`, `STATICFILES_DIRS`, шляхи в Tailwind (input/output), CI, якщо збирають CSS.  
**Плюси:** логічно для тих, хто вважає «фронт» одним модулем.  
**Мінуси:** Django за замовчуванням очікує `templates` і `static` у певних місцях — треба перевірити collectstatic, тести, посилання в конфігах.

---

## Варіант D: Мінімальні зміни — лише порядок у корені

Нічого не переміщувати, тільки документувати в README або в цьому файлі «зони» кореня:

- **Додаток:** `config/`, `accounts/`, `catalog/`, `orders/`, `templates/`, `static/`, `assets/`, `manage.py`, `requirements*.txt`, `pyproject.toml`
- **Інфра:** `infra/`, `Dockerfile`, `docker-compose.yml`
- **CI/CD:** `.github/`
- **Доки та інструменти:** `docs/`, `scripts/`, `makefile`

Це не змінює файлову систему, але дає чітку «карту» для наступних рефакторингів.

---

## Рекомендація

- Якщо хочете **максимально чистий корінь** і готові один раз пройтися по шляхах і CI — варіант **A** (`app/`).
- Якщо хочете **мало змін** — варіант **B** (хіба що перейменувати/згрупувати `scripts/`) або **D** (тільки документувати).
- Варіант **C** має сенс, якщо плануєте окремий frontend (наприклад SPA) і хочете вже зараз виділити «фронт» в одну папку.

Якщо оберете варіант A, можна далі розписати покроковий чекліст (по одному пункту: BASE_DIR, Docker, makefile, CI, тести).
