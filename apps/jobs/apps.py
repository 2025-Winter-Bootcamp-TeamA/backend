from django.apps import AppConfig


class CorpsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField' #PK 타입설정
    name = 'apps.jobs' 
    verbose_name = '기업 및 채용 공고'
