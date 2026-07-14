from celery import Celery
from celery.schedules import crontab
from config import get_settings

settings = get_settings()

celery_app = Celery(
    "vigia",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "tasks.relatorio_manha",
        "tasks.atualizacao_clima",
        "tasks.atualizacao_precos",
        "tasks.verificacao_risco",
        "tasks.satelite_ndvi",
        "tasks.fatores_demanda",
        "tasks.viveiros_seed",
        "tasks.aprendizado",
    ],
)

celery_app.conf.beat_schedule = {
    "relatorio-manha": {
        "task": "tasks.relatorio_manha.gerar_relatorio_manha",
        "schedule": crontab(hour=5, minute=30),
    },
    "clima-manha": {
        "task": "tasks.atualizacao_clima.atualizar_clima",
        "schedule": crontab(hour=6, minute=0),
    },
    "clima-tarde": {
        "task": "tasks.atualizacao_clima.atualizar_clima",
        "schedule": crontab(hour=18, minute=0),
    },
    "precos-manha": {
        "task": "tasks.atualizacao_precos.atualizar_precos",
        "schedule": crontab(hour=8, minute=0),
    },
    "risco-bihoral": {
        "task": "tasks.verificacao_risco.verificar_riscos",
        "schedule": crontab(minute=0, hour="*/2"),
    },
    "satelite-ndvi": {
        "task": "tasks.satelite_ndvi.processar_ndvi",
        "schedule": crontab(hour=2, minute=0, day_of_week="*/5"),
    },
    "fatores-demanda": {
        "task": "tasks.fatores_demanda.atualizar_fatores",
        "schedule": crontab(hour=7, minute=0, day_of_week="monday"),
    },
    "viveiros": {
        "task": "tasks.viveiros_seed.atualizar_viveiros",
        "schedule": crontab(hour=3, minute=0, day_of_week="tuesday"),
    },
    "aprendizado": {
        "task": "tasks.aprendizado.rodar_aprendizado",
        "schedule": crontab(hour=1, minute=0, day_of_week="sunday"),
    },
}

celery_app.conf.timezone = settings.relatorio_timezone
