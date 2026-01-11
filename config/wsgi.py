"""
WSGI 설정
Gunicorn 등의 WSGI 서버에서 사용
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

application = get_wsgi_application()
