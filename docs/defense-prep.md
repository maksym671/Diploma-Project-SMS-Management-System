# Защита SMS — шпаргалка и вопросы комиссии

Печать этого файла или держать его на втором экране. Слайды — на проекторе, этот лист — себе.

Live: https://diploma-project-sms-management-system.onrender.com

---

## 1. Логины

| Роль | Где | Username | Password | Что показывать |
|------|-----|----------|----------|----------------|
| Преподаватель (основной) | **прод** | `prof.martinez` | `demo1234` | Elena Martinez, математика |
| Второй преподаватель | **прод** | `prof.chen` | `demo1234` | изоляция данных |
| Администратор | **локально** | `admin` | `demo1234` | Teachers, CRUD студентов/курсов |
| Администратор | **прод** | `admin` | из Render → Environment → `DJANGO_ADMIN_PASSWORD` | не `demo1234` |

На проде **не работают:** `admin` / `demo1234`, `teacher` / `demo1234`, `teacher1` / `demo1234`. Это специально: публичный пароль админа перезаписывается при деплое.

Если первый заход крутится ~30 с — это холодный старт Render. Подождать, не обновлять панически.

Экран **Teachers** на проде уже в коде (`/teachers/`). Зайти туда может только администратор — пароль `admin` на Render не `demo1234`, а `DJANGO_ADMIN_PASSWORD`. Если комиссия попросит завести преподавателя, а пароль админа не под рукой — показать локально (`http://127.0.0.1:8000`) под `admin` / `demo1234`.

---

## 2. Пять минут — сценарий для комиссии

Говорить коротко. Кликать сам. Не читать слайды вслух.

### 0:00 — открыть сайт с титульного слайда

Клик по LIVE-ссылке. Если спит — сказать: *«free tier, first request wakes the process»*.

### 0:30 — вход преподавателя

`prof.martinez` / `demo1234`.

Сказать: *«Students are records, not users. There is no student login and no public registration.»*

На логине нет Forgot password — пароль меняет администратор на экране Teachers.

### 1:00 — Dashboard

KPI: её студенты, её курсы, её оценки. Три графика Chart.js. Данные с `GET /api/dashboard/` — JSON, уже ограничен ролью.

Сказать: *«Same numbers as the HTML page, scoped to this teacher.»*

### 1:30 — Students → карточка студента

Список только тех, кто записан на её MATH-курсы. Открыть любого.

Сказать: *«A colleague’s student returns 404, not an empty page.»*

Не нажимать Add / Edit — у преподавателя этих кнопок нет.

### 2:15 — Courses → Grades

Открыть оценки. Показать **компонент** (coursework / midterm / final / retake) и **вес**.

Сказать: *«The course mark is a weighted mean, not a single number. Components of one course cannot exceed 100 %. Each row stores who saved it — assigned_by.»*

CSV справа — тоже только её данные.

### 3:15 — Attendance → Mark Class

`Attendance` → `Mark Class`: курс + дата, вся группа на одном экране, один Save.

Статусы: present / absent / late. Одна запись на пару (enrolment, date) — это constraint в БД.

### 4:00 — польский

Переключатель EN → PL в шапке. Студенты → Studenci, курсы → Kursy, выход → Wyloguj.

Сказать: *«308 strings, session locale, no page reload of the whole app — Turbo keeps the URL.»*

Вернуть EN, чтобы комиссия читала дальше по-английски.

### 4:30 — изоляция (второй логин)

Logout (кнопка, POST — ссылкой сессию не убить). Войти как `prof.chen` / `demo1234`.

Другие курсы, другие студенты, другой дашборд. Это главный инженерный тезис проекта.

### Если осталась минута — админ

Только если известен прод-пароль админа **или** открыт локальный сервер:

1. `admin` + его пароль.
2. **Teachers** — выдать аккаунт, сменить пароль лектору.
3. Students → Add — запись студента, не аккаунт.
4. Course с `max_students` — лишняя запись отклоняется формой.

Не открывать `/admin/` Django. Комиссии нужен твой UI, не штатная админка.

---

## 3. Чего не открывать

- `/accounts/password_reset/` — маршрута нет, будет 404. Так и задумано.
- Логин студента — студентов-пользователей нет.
- `admin` / `demo1234` на **проде** — пароль уже другой.
- Чужой курс под преподавателем «найти по URL» — покажет 404; это хорошо, но не надо заранее искать pk.
- Редактирование CSS в DevTools.

---

## 4. Что говорить, если спросят «где домен .me»

Если домен уже висит: показать `https://sms-shpak.me` (или тот адрес, который реально зарегистрировали). Render-URL остаётся запасным.

Если Pack только что открыли, а DNS ещё не доехал: *«The app is live on Render with HTTPS. The .me from GitHub Student Pack / Namecheap is being attached now.»*

---

## 5. Вопросы комиссии — короткие ответы

Отвечать на языке вопроса. Ниже — суть своими словами + где это в коде.

### Зачем Django, а не React / Node?

Один язык, серверные шаблоны, готовые сессии, CSRF, ORM, миграции. Для портала преподавателей отдельный SPA не нужен. JWT имел бы смысл при отдельном фронте — его нет.

### Почему студенты не логинятся?

Это **teaching-staff portal**. Студент — запись в таблице `Student`, не `User`. Третья роль — в Future work на слайде 10.

### Как устроен RBAC?

`User.role` = `admin` | `teacher`. Декоратор `role_required` режет маршрут (чужая роль → redirect на дашборд). Queryset `visible_students` / `visible_courses` режет данные. Угаданный URL чужого объекта → **404**. Два слоя специально: декоратор не заменяет фильтр.

### Чем админ отличается от преподавателя?

Админ: студенты, курсы, записи, Teachers, всё. Преподаватель: только свои курсы; оценки и посещаемость может ставить; студентов/курсы не создаёт.

### Как считается итоговая оценка?

Не среднее арифметическое. `weighted_average`: Σ(value × weight) / Σ(weight). Пример: 40 % × 3.0 + 60 % × 5.0 = **4.20**, не 4.00. Сумма весов по курсу ≤ 100 % — проверка в `GradeForm.clean`.

### Кто поставил оценку?

`Grade.assigned_by` → User. Видно в списке и в CSV. Это audit trail.

### Почему нет «Forgot password»?

Нет публичной регистрации и нет почтового потока для сотрудников. Администратор задаёт новый пароль на Teachers (`TeacherForm`, password необязателен при редактировании). На проде пароль `admin` берётся из `DJANGO_ADMIN_PASSWORD`.

### Почему SQLite локально и Postgres в проде?

Один ORM, один код. `DATABASE_URL` через `dj-database-url`. SQLite — ноутбук. Postgres — ACID и несколько пользователей на Render/Neon.

### Как задеплоено?

`render.yaml` + `build.sh`: compilemessages → collectstatic → migrate → `seed_demo`. Сиды только в **пустую** БД. HTTPS, HSTS, secure cookies при `DEBUG=False`. Статика — WhiteNoise, без Nginx-контейнера.

### Что делает keepalive?

Free Render засыпает ~через 15 мин. GitHub Action пингует `/login/` каждые 10 минут. Планировщик GitHub не гарантия — для защиты лучше открыть сайт за 1–2 минуты до выхода.

### Зачем `/api/dashboard/`, если есть HTML?

Те же KPI в JSON, уже по роли. Графики на дашборде его читают. Заготовка под клиента без второго сервера.

### Как устроена посещаемость?

Unique `(enrollment, date)`. Статусы present / absent / late. Mark Class — одна форма, вся группа, один POST.

### Что если курс полный?

`EnrollmentForm`: при `status=active` и `enrolled_count >= max_students` — ошибка формы, не молчаливая обрезка.

### Как сделан польский?

`gettext` в шаблонах, моделях, сообщениях, заголовках CSV. `set_language`, локаль в сессии. `django.mo` в репозитории — деплой не требует gettext на сервере. 308 строк, 0 непереведённых.

### Сколько тестов и что они ловят?

80. Модели, логин, изоляция преподавателей, ёмкость курса, веса оценок, Mark Class, authorship, i18n, `seed_demo`, дым каждой страницы для обеих ролей, бюджет запросов дашборда. CI: тесты + `makemigrations --check` + `check --deploy` + collectstatic.

### 6 моделей — какие связи?

User → Course (преподаватель). Student + Course → Enrollment (unique pair). Enrollment → Grade (несколько компонентов) и Attendance (по дням). Студент не связан с User.

### Почему не Moodle / USOS / Classroom?

Тяжелые или закрытые. SMS — узкий контур кафедры: журнал, посещаемость, роли, EN/PL, один билд, без лицензии.

### Что бы ты добавил дальше?

Честно со слайда 10: портал студента, PDF-транскрипт, письма об оценках, токенный REST, TOTP для админа. Не обещать Stripe/карты/OAuth — к теме не относятся.

### Где секретный ключ?

Не в git. `SECRET_KEY` из окружения. При `DEBUG=False` ключ `django-insecure-…` процесс не запустит.

---

## 6. Админ-сценарий (локально или с паролем Render)

Порядок кликов, если комиссия попросит «покажи, как заводят преподавателя»:

1. Войти как администратор.
2. **Teachers → Add Teacher** — username, имя, кафедра, пароль два раза. Save.
3. Logout → войти новым логином → видит пустой дашборд (курсов ещё нет).
4. Снова админ → **Courses → Add** — назначить этого преподавателя.
5. **Students → Add** — запись, не аккаунт.
6. **Enrollments → Add** — связать студента с курсом.
7. Teachers → Edit → новое поле пароля (пустое = не менять) — смена забытого пароля.

Проверено тестами: `test_create_teacher_and_they_can_sign_in`, `test_admin_can_set_a_new_teacher_password`, `test_admin_pages_render`.

---

## 7. GitHub Student Pack → Namecheap `.me`

Цель: **`sms-shpak.me`** (WHOIS: свободен). Если занят в корзине — `shpak-sms.me`.

1. https://education.github.com/pack → войти GitHub → **Namecheap** → Get offer / Redeem. Авторизовать Namecheap.
2. Откроется nc.me / Namecheap. Искать `sms-shpak.me`, в корзину, checkout. Год должен быть $0; карту Namecheap часто всё равно спрашивает.
3. Namecheap → домен → **Advanced DNS**. Удалить AAAA. Записи (TTL 1 min):
   - A, host `@`, value `216.24.57.1`
   - CNAME, host `www`, value `diploma-project-sms-management-system.onrender.com.`
4. Render → сервис SMS → **Settings → Custom Domains → Add** `sms-shpak.me` (www подтянется сам). **Verify**.
5. Environment: `CUSTOM_DOMAIN=sms-shpak.me` (код уже добавляет apex+www в ALLOWED_HOSTS и CSRF).
6. Когда https://sms-shpak.me открывает логин — сказать, пересоберём слайды (`LIVE_URL` в `scripts/generate_presentation.py`).

Пока Verify красный, комиссия идёт на Render-URL.

---

## 8. Соответствие ТЗ (inżynier I stopnia, Vizja / AEH)

Это **дипломный инженерный проект + экзамен**, не магистерская теза. Комиссии достаточно: рабочая система, роли, документация, слайды, живое демо. Стек Django менять не нужно.

| Требование | Где видно | Статус |
|------------|-----------|--------|
| Рабочее веб-приложение, не макет | Live Render + локальный `runserver` | да |
| Постановка задачи и обоснование стека | Документация §1, слайды 1–3 | да |
| Модель данных и связи | 6 моделей, ER на слайдах, миграции | да |
| Роли и изоляция данных | `admin` / `teacher`; 404 на чужой объект | да |
| Бизнес-правила | веса оценок, ёмкость курса, unique attendance | да |
| Интерфейс EN/PL | 308 строк, переключатель в шапке | да |
| Тесты и CI | `manage.py test` + GitHub Actions | да |
| Деплой HTTPS | Render + Neon, `DEBUG=False` | да |
| Документация + презентация | `docs/`, PPTX | да |
| Домен `.me` | Pack одобрен — вешаем `sms-shpak.me` | в работе |

Чего **нет** в ТЗ I степени и не надо доделывать до защиты: React SPA, Stripe, OAuth, студенческий логин, почтовый reset пароля.

Если спросят «это исследование?»: *«No — it is an engineering implementation of a staff portal, with tests and a live deployment.»*
