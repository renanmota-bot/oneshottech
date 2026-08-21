import os
import dj_database_url
from pathlib import Path

# Diretório Raiz do Projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# CHAVE DE SEGURANÇA (Altere para uma chave própria em produção)
SECRET_KEY = 'django-insecure-sua-chave-secreta-hostgator-aqui-troque-em-producao'

# SEGURANÇA E PRODUÇÃO
# Em produção na Hostgator, altere DEBUG para False
DEBUG = True

# Domínios e Subdomínios liberados para acessar a aplicação
# Subsitua pelo seu domínio/subdomínio da Hostgator (ex: 'app.suadominio.com.br')
ALLOWED_HOSTS = ['.onrender.com', 'app.oneshottech.com.br', 'localhost', '127.0.0.1']

# APLICAÇÕES INSTALADAS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Módulos Internos do Sistema One Shot Tech
    'core',
    'eventos',
]

# MIDDLEWARES
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# TEMPLATES (HTML)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'passenger_wsgi.application'


# BANCO DE DADOS
# Nota: Para rodar localmente usará o SQLite. Se preferir usar o MySQL da Hostgator, basta preencher a área comentada.
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

"""
# CONFIGURAÇÃO DE BANCO MYSQL PARA HOSTGATOR (Caso vá migrar para o cPanel MySQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'usuario_oneshottech',        # Nome do Banco criado no cPanel
        'USER': 'usuario_admin',              # Usuário do Banco no cPanel
        'PASSWORD': 'SuaSenhaForteAqui123!',  # Senha do Banco no cPanel
        'HOST': 'localhost',                  # Na Hostgator geralmente é 'localhost'
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
"""


# MODELO DE USUÁRIO PERSONALIZADO
AUTH_USER_MODEL = 'core.Usuario'

# VALIDAÇÃO DE SENHAS
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# INTERNACIONALIZAÇÃO & FUSO HORÁRIO (Brasil / São Paulo)
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# REDIRECIONAMENTOS DE AUTENTICAÇÃO
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'login'
LOGOUT_REDIRECT_URL = 'login'


# ARQUIVOS ESTÁTICOS (CSS, JS, LOGO E IMAGENS DO SISTEMA)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
# Pasta onde o comando 'python manage.py collectstatic' agrupará os arquivos para a Hostgator servir
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


# ARQUIVOS DE MÍDIA (FOTOS DE PERFIL DOS STAFFS E COMPROVANTES ENVIADOS)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# CONFIGURAÇÃO DE DISPARO DE E-MAIL (SMTP HOSTGATOR)
# Preencha com os dados da sua conta de e-mail criada no cPanel para enviar confirmações aos Staffs
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'mail.suadominio.com.br'  # Geralmente 'mail.seudominio.com.br' ou 'smtp.hostgator.com.br'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'contato@suadominio.com.br'  # E-mail do cPanel
EMAIL_HOST_PASSWORD = 'SuaSenhaDoEmailAqui123' # Senha do E-mail no cPanel
DEFAULT_FROM_EMAIL = 'One Shot Tech <contato@suadominio.com.br>'


# TIPO DE CHAVE PRIMÁRIA PADRÃO
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'