# Ponto de entrada do Celery — usado pelo Railway e docker-compose
# `celery -A celery_app worker` funciona porque este arquivo re-exporta a instância
from tasks.celery_app import celery_app  # noqa: F401
