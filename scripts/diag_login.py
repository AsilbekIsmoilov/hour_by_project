"""ВРЕМЕННАЯ диагностика 500 при логине — РЕАЛЬНЫЙ HTTP через nginx.

Воспроизводит вход двумя способами (как браузер/фронт), печатает статус и тело
(при DEBUG=1 тело 500 = traceback). Запуск из CI:
    docker compose exec -T web python scripts/diag_login.py
"""
import http.cookiejar
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = "10.145.20.9:4020"
BASE = "http://nginx"  # nginx-контейнер в compose-сети


def _wait_uvicorn():
    for _ in range(40):
        try:
            urllib.request.urlopen("http://localhost:8000/api/v1/", timeout=10)
            return
        except urllib.error.HTTPError:
            return
        except urllib.error.URLError:
            time.sleep(2)


def show(label, exc_or_resp):
    if isinstance(exc_or_resp, urllib.error.HTTPError):
        print(label, "STATUS", exc_or_resp.code)
        print("---- BODY ----")
        print(exc_or_resp.read().decode("utf-8", "ignore")[:9000])
    else:
        print(label, "STATUS", exc_or_resp.getcode())


_wait_uvicorn()

# === [1] JWT token endpoint через nginx (как фронт) ===
print("=== [1] POST /api/v1/auth/token/ через nginx ===")
body = json.dumps({"username": "admin", "password": "123"}).encode()
req = urllib.request.Request(
    BASE + "/api/v1/auth/token/", data=body,
    headers={"Content-Type": "application/json", "Host": HOST},
)
try:
    show("[token]", urllib.request.urlopen(req, timeout=25))
except urllib.error.HTTPError as e:
    show("[token]", e)
except Exception as e:  # noqa: BLE001
    print("[token] ERR", repr(e))

# === [2] Admin login (форма) через nginx: GET (csrf) -> POST ===
print("=== [2] POST /admin/login/ (форма admin) через nginx ===")
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
LOGIN = BASE + "/admin/login/?next=/admin/"
try:
    g = opener.open(
        urllib.request.Request(LOGIN, headers={"Host": HOST}), timeout=25
    )
    html = g.read().decode("utf-8", "ignore")
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    csrf = m.group(1) if m else ""
    print("csrf token получен:", bool(csrf))
    form = urllib.parse.urlencode({
        "username": "admin", "password": "123",
        "csrfmiddlewaretoken": csrf, "next": "/admin/",
    }).encode()
    p = urllib.request.Request(
        LOGIN, data=form,
        headers={"Host": HOST, "Referer": LOGIN,
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    show("[admin-login]", opener.open(p, timeout=25))
except urllib.error.HTTPError as e:
    show("[admin-login]", e)
except Exception as e:  # noqa: BLE001
    print("[admin-login] ERR", repr(e))
