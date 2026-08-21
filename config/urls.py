from django.contrib import admin
from django.urls import path
from django.contrib.auth import get_user_model
from django.http import HttpResponse

def criar_admin_emergencia(request):
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@oneshottech.com.br', 'is_staff': True, 'is_superuser': True}
    )
    user.set_password('SuaSenhaSegura123!')
    user.save()
    return HttpResponse("SUPERUSUARIO CRIADO COM SUCESSO!")

urlpatterns = [
    path('admin/', admin.site.urls),  # Painel de Admin do Django
    path('setup-admin-secret/', criar_admin_emergencia),
]