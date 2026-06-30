#!/bin/sh
set -e

if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "[entrypoint] Applying migrations (default)..."
  python manage.py migrate --noinput
  echo "[entrypoint] Applying migrations (archive)..."
  python manage.py migrate --database=archive --noinput

  # ⚠️ ОДНОРАЗОВЫЙ ПОЛНЫЙ СБРОС ДАННЫХ. Включается только при RESET_DB=1.
  # Удаляет ВСЕ данные (default + archive), схема остаётся (миграции уже
  # применены выше). Дальше seed восстановит базовые данные и активный цикл.
  # ВАЖНО: после одного успешного деплоя ВЕРНУТЬ RESET_DB="0" и задеплоить снова,
  # иначе данные будут стираться при КАЖДОМ рестарте.
  if [ "$RESET_DB" = "1" ]; then
    echo "[entrypoint] !!! RESET_DB=1 — УДАЛЕНИЕ ВСЕХ ДАННЫХ (default + archive) !!!"
    python manage.py flush --noinput
    python manage.py flush --database=archive --noinput
    echo "[entrypoint] Все данные удалены. Seed восстановит базовые данные ниже."
  fi

  echo "[entrypoint] Seeding initial data (idempotent)..."
  python manage.py seed_initial_data

  echo "[entrypoint] Collecting static files..."
  python manage.py collectstatic --noinput

  echo "[entrypoint] Ensuring admin superuser..."
  python manage.py shell -c "from django.contrib.auth import get_user_model; U = get_user_model(); u, created = U.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True, 'role': 'admin'}); (u.set_password('123'), u.save(), print('[entrypoint] superuser admin created')) if created else print('[entrypoint] superuser admin already exists')"
fi

exec "$@"
