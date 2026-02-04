# Procfile para Heroku/Railway
web: gunicorn app:app --bind 0.0.0.0:$PORT
# Worker opcional para cron jobs (se quiser rodar separadamente)
# worker: python cron_runner.py