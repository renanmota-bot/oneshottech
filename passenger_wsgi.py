import os
import sys

# Aponta para o diretório da aplicação
sys.path.insert(0, os.path.dirname(__file__))

# Define as configurações do Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
