@echo off
REM ============================================
REM Run Celery worker and beat for Generator_post_for_telegram on Windows
REM ============================================

REM Устанавливаем переменную окружения для Windows (если нужно)
REM set PYTHONPATH=%CD%

REM Запуск Celery worker в отдельном окне
start "Celery Worker" cmd /k "celery -A app.celery_app.celery_app worker --concurrency=1 --loglevel=info --pool=solo"

REM Запуск Celery beat в отдельном окне
start "Celery Beat" cmd /k "celery -A app.celery_app.celery_app beat --loglevel=info"

echo ============================================
echo Celery worker and beat запущены в отдельных окнах
echo ============================================
pause
