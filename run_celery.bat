@echo off
REM ============================================
REM Run Celery worker for Generator_post_for_telegramm on Windows
REM ============================================

REM Устанавливаем переменную окружения для Windows (если нужно)
REM set PYTHONPATH=%CD%

REM Запуск worker Celery
celery -A app.celery_app.celery_app worker --loglevel=info --pool=solo

pause
