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

Экран **Teachers** на проде появится только после пуша текущего кода. Если там 404 — этот шаг показать локально (`http://127.0.0.1:8000`) под `admin` / `demo1234`.

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

Только если Teachers уже на проде **или** открыт локальный сервер:

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

*«The live system is already on Render with HTTPS. A custom .me domain is waiting on GitHub Student Pack / Namecheap. Functionally the defence uses this URL.»*

Пока Pack закрыт, домен не нужен.

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

77. Модели, логин, изоляция преподавателей, ёмкость курса, веса оценок, Mark Class, authorship, i18n, `seed_demo`, дым каждой страницы для обеих ролей. CI: тесты + `makemigrations --check` + `check --deploy` + collectstatic.

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

## 7. Когда откроется GitHub Student Pack

Это **не** часть пятиминутного демо. После оффера Namecheap:

1. Забрать `.me` (например `sms-shpak.me`).
2. DNS: CNAME на `diploma-project-sms-management-system.onrender.com`.
3. Render → Settings → Custom Domains — вписать домен.
4. Обновить `LIVE_URL` в `scripts/generate_presentation.py` и пересобрать слайды.

До этого в слайдах и документации остаётся текущий Render-URL.
