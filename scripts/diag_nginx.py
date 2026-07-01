"""Диагностика ПОЛНОГО HTTP-пути через nginx (nginx -> web).

Бьёт по сервису nginx (внутреннее имя `nginx`, порт 80) изнутри сети compose —
ровно так же, как это делает браузер снаружи через порт 4020. Показывает
статус и тело ответа, чтобы поймать 500/502 именно на слое nginx.

Запуск: docker compose exec -T web python scripts/diag_nginx.py
"""
import json
import urllib.request

BASE = "http://nginx"


def hit(method, path, body=None):
    url = BASE + path
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read(500).decode("utf-8", "replace")
            print(f"  {method} {path} -> {resp.status}")
            print(f"    body: {text[:300]}")
    except urllib.error.HTTPError as e:
        text = e.read(1000).decode("utf-8", "replace")
        print(f"  {method} {path} -> HTTP {e.code}")
        print(f"    body: {text[:600]}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {method} {path} -> СЕТЕВАЯ ОШИБКА: {exc!r}")


hit("GET", "/api/v1/")
hit("POST", "/api/v1/auth/token/", {"username": "admin", "password": "123"})
