from django.contrib import admin
from django.urls import path
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from core import views

def criar_admin_emergencia(request):
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@oneshottech.com.br', 'is_staff': True, 'is_superuser': True, 'perfil': 'SUPER_ADMIN'}
    )
    user.set_password('Motinha@09@')
    user.is_staff = True
    user.is_superuser = True
    user.perfil = 'SUPER_ADMIN'
    user.save()
    return HttpResponse("SUPERUSUARIO CRIADO COM SUCESSO!")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('setup-admin-secret/', criar_admin_emergencia),

    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/staff/', views.registro_staff_view, name='registro_staff'),

    path('dashboard/super-admin/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/staff/', views.staff_dashboard, name='staff_dashboard'),

    path('ghost-login/<int:user_id>/', views.ghost_login_view, name='ghost_login'),

    path('exportar/caches/excel/', views.exportar_caches_excel, name='exportar_caches_excel'),
    path('exportar/caches/pdf/', views.exportar_caches_pdf, name='exportar_caches_pdf'),
    path('exportar/ficha/<int:user_id>/', views.exportar_ficha_staff_pdf, name='exportar_ficha_staff_pdf'),
    path('exportar/extrato/', views.exportar_extrato_staff_pdf, name='exportar_extrato_staff_pdf'),
]