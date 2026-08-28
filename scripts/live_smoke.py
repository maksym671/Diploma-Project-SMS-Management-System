"""Read-only smoke test against the live deployment.

    python3 scripts/live_smoke.py [https://thesms.me]

Signs in with the seeded demo teachers, checks authentication, CSRF, RBAC
isolation, CSV export and logout, and never writes to the remote database.
"""
import re, socket, ssl, sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import certifi
import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://thesms.me"
PW = "demo1234"  # seeded demo password from core/management/commands/seed_data.py
ok = fail = 0

def check(name, cond, info=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {name} {info}")
    else:
        fail += 1; print(f"  FAIL  {name} {info}")

def login(user):
    s = requests.Session()
    r = s.get(f"{BASE}/login/", timeout=30)
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text).group(1)
    r = s.post(f"{BASE}/login/", timeout=30,
               data={"csrfmiddlewaretoken": token, "username": user, "password": PW},
               headers={"Referer": f"{BASE}/login/"}, allow_redirects=True)
    return s, r

def cert_days_left(host):
    # certifi's bundle, because a stock macOS Python has no system CA store.
    ctx = ssl.create_default_context(cafile=certifi.where())
    with ctx.wrap_socket(socket.create_connection((host, 443), timeout=20), server_hostname=host) as sock:
        not_after = sock.getpeercert()["notAfter"]
    expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    return (expires - datetime.now(timezone.utc)).days


print(f"== domain and transport ({BASE}) ==")
host = urlparse(BASE).hostname
try:
    days = cert_days_left(host)
    check("TLS certificate valid for >10 more days", days > 10, f"{days} days left")
except Exception as exc:  # noqa: BLE001 - report, do not crash the run
    check("TLS certificate readable", False, repr(exc))

r = requests.get(f"{BASE}/login/", timeout=30)
check("HSTS header present", "strict-transport-security" in {k.lower() for k in r.headers})
check("clickjacking header present", r.headers.get("x-frame-options") == "DENY",
      r.headers.get("x-frame-options", "missing"))

if host and not host.startswith("www."):
    r = requests.get(f"https://www.{host}/", timeout=30, allow_redirects=False)
    check("www redirects to the apex", r.status_code in (301, 302) and host in r.headers.get("location", ""),
          f"[{r.status_code}] {r.headers.get('location', '')}")

print(f"\n== anonymous access ({BASE}) ==")
for path in ["/", "/students/", "/courses/", "/grades/", "/attendance/", "/teachers/"]:
    r = requests.get(f"{BASE}{path}", timeout=30, allow_redirects=False)
    check(f"{path} blocked for anon", r.status_code in (301, 302) and "/login/" in r.headers.get("location", ""),
          f"[{r.status_code}]")

r = requests.get(f"{BASE}/login/", timeout=30)
check("login page has CSRF token", 'csrfmiddlewaretoken' in r.text)
check("csrftoken cookie is Secure", "Secure" in r.headers.get("set-cookie", ""))

print("\n== bad password is rejected ==")
s = requests.Session()
t = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', s.get(f"{BASE}/login/", timeout=30).text).group(1)
r = s.post(f"{BASE}/login/", data={"csrfmiddlewaretoken": t, "username": "prof.martinez", "password": "wrong-pass"},
           headers={"Referer": f"{BASE}/login/"}, timeout=30, allow_redirects=False)
# 422, not 200: Turbo only renders a form's error page on a 4xx.
check("wrong password not authenticated", r.status_code == 422 and "sessionid" not in s.cookies,
      f"[{r.status_code}]")

print("\n== CSRF protection (POST without token) ==")
r = requests.post(f"{BASE}/login/", data={"username": "prof.martinez", "password": PW}, timeout=30)
check("tokenless POST rejected 403", r.status_code == 403, f"[{r.status_code}]")

courses = {}
for user in ["prof.martinez", "prof.chen"]:
    print(f"\n== {user} ==")
    s, r = login(user)
    check("login succeeded", "sessionid" in s.cookies and "/login/" not in r.url, f"[{r.status_code}] {r.url}")
    if "sessionid" not in s.cookies:
        continue
    for path in ["/", "/students/", "/courses/", "/grades/", "/attendance/", "/profile/"]:
        rr = s.get(f"{BASE}{path}", timeout=30)
        check(f"GET {path}", rr.status_code == 200 and "Traceback" not in rr.text, f"[{rr.status_code}] {len(rr.text)}b")
    rr = s.get(f"{BASE}/courses/", timeout=30)
    courses[user] = set(re.findall(r'/courses/(\d+)/', rr.text))
    print(f"  info  visible course ids: {sorted(courses[user], key=int)}")
    rr = s.get(f"{BASE}/teachers/", timeout=30, allow_redirects=False)
    if user == "admin":
        check("admin can open /teachers/", rr.status_code == 200, f"[{rr.status_code}]")
        aa = s.get(f"{BASE}/admin/", timeout=30)
        check("admin can open /admin/", aa.status_code == 200, f"[{aa.status_code}]")
    else:
        check("teacher blocked from /teachers/", rr.status_code in (302, 403), f"[{rr.status_code}]")
    for path in ["/reports/export/students/", "/reports/export/grades/"]:
        rr = s.get(f"{BASE}{path}", timeout=30)
        check(f"CSV {path}", rr.status_code == 200 and "csv" in rr.headers.get("content-type", ""),
              f"[{rr.status_code}] {rr.headers.get('content-type','')}")
    rr = s.get(f"{BASE}/logout/", timeout=30, allow_redirects=False)
    check("GET /logout/ refused (POST-only)", rr.status_code == 405, f"[{rr.status_code}]")
    tok = s.cookies.get("csrftoken")
    rr = s.post(f"{BASE}/logout/", data={"csrfmiddlewaretoken": tok},
                headers={"Referer": f"{BASE}/"}, timeout=30, allow_redirects=False)
    after = s.get(f"{BASE}/students/", timeout=30, allow_redirects=False)
    check("POST logout ends session", after.status_code in (301, 302), f"[{after.status_code}]")

print("\n== admin account hardening ==")
s, r = login("admin")
check("public demo password does NOT work for admin in prod",
      "sessionid" not in s.cookies, "(DJANGO_ADMIN_PASSWORD override active)")
r = requests.get(f"{BASE}/admin/", timeout=30, allow_redirects=False)
check("/admin/ requires auth", r.status_code in (301, 302), f"[{r.status_code}]")

print("\n== RBAC isolation ==")
if "prof.martinez" in courses and "prof.chen" in courses:
    a, b = courses["prof.martinez"], courses["prof.chen"]
    check("two teachers see different course sets", a != b, f"{sorted(a,key=int)} vs {sorted(b,key=int)}")
    check("no overlap between teachers' courses", not (a & b), f"overlap={sorted(a & b, key=int)}")

print("\n== i18n ==")
s, _ = login("prof.martinez")
t = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', s.get(f"{BASE}/profile/", timeout=30).text)
r = s.post(f"{BASE}/i18n/setlang/", data={"csrfmiddlewaretoken": t.group(1) if t else "", "language": "pl", "next": "/"},
           headers={"Referer": f"{BASE}/"}, timeout=30, allow_redirects=True)
check("switch to Polish", r.status_code == 200, f"[{r.status_code}]")

print(f"\n===== {ok} passed, {fail} failed =====")
sys.exit(1 if fail else 0)
