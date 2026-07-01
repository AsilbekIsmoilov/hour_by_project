"""Проверяет, тот ли это хост: сравнивает 127.0.0.1:4020 (nginx ЭТОГО хоста)
и 10.145.20.9:4020 (адрес "прода"). Запускать в контейнере с --network host.

Если 127.0.0.1:4020 -> 302, а 10.145.20.9:4020 -> 500, значит 10.145.20.9 —
ДРУГАЯ машина/стек, и наш пайплайн деплоит не туда, куда смотрит браузер.
"""
import http.cookiejar
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0"


def my_ip_towards(target):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((target, 80))
        return s.getsockname()[0]
    except Exception as e:  # noqa: BLE001
        return f"?({e})"
    finally:
        s.close()


print("hostname:", socket.gethostname())
print("IP этого хоста в сторону 10.145.20.9:", my_ip_towards("10.145.20.9"))
print()


def probe(base):
    print(f"--- {base} ---")
    login = base + "/api-auth/login/"
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    h = {"Accept": "text/html", "User-Agent": UA}
    try:
        resp = op.open(urllib.request.Request(login, headers=dict(h)), timeout=15)
        html = resp.read().decode("utf-8", "replace")
        print("  GET  ->", resp.status, "| Server:", resp.headers.get("Server"))
    except urllib.error.HTTPError as e:
        html = e.read().decode("utf-8", "replace")
        print("  GET  -> HTTP", e.code)
    except Exception as e:  # noqa: BLE001
        print("  GET  -> СЕТЬ:", repr(e))
        return
    m = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', html)
    token = m.group(1) if m else ""
    data = urllib.parse.urlencode({
        "username": "admin", "password": "123",
        "csrfmiddlewaretoken": token, "next": "/api/v1/",
    }).encode()
    hp = dict(h)
    hp.update({
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": base, "Referer": login,
    })
    try:
        resp = op.open(urllib.request.Request(login, data=data, headers=hp, method="POST"), timeout=15)
        print("  POST ->", resp.status, "| Server:", resp.headers.get("Server"), "(500 НЕТ)")
    except urllib.error.HTTPError as e:
        print("  POST -> HTTP", e.code, "| Server:", e.headers.get("Server"))
    except Exception as e:  # noqa: BLE001
        print("  POST -> СЕТЬ:", repr(e))


probe("http://127.0.0.1:4020")
probe("http://10.145.20.9:4020")
