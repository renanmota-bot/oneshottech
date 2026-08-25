from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from core import views


def criar_admin_emergencia(request):
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@oneshottech.com.br',
            'is_staff': True,
            'is_superuser': True,
            'perfil': 'SUPER_ADMIN'
        }
    )
    user.is_staff = True
    user.is_superuser = True
    user.perfil = 'SUPER_ADMIN'
    user.set_password('Motinha@09@')
    user.save()

    if created:
        return HttpResponse("SUPERUSUARIO CRIADO COM SUCESSO! Senha: Motinha@09@")
    else:
        return HttpResponse("SUPERUSUARIO ATUALIZADO! Senha redefinida para: Motinha@09@")


urlpatterns = [
    # Admin nativo e Rota de emergência
    path('admin/', admin.site.urls),
    path('setup-admin-secret/', criar_admin_emergencia),

    # Autenticação
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/staff/', views.registro_staff_view, name='registro_staff'),

    # Dashboards
    path('dashboard/super-admin/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('dashboard/empresa/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/', views.admin_dashboard),
    path('dashboard/staff/', views.staff_dashboard, name='staff_dashboard'),

    # Ghost Login
    path('ghost-login/<int:user_id>/', views.ghost_login_view, name='ghost_login'),

    # Exportações & Relatórios
    path('exportar/excel/', views.exportar_caches_excel, name='exportar_excel'),
    path('exportar/pdf/', views.exportar_caches_pdf, name='exportar_pdf'),
    path('exportar/lote-pix/', views.exportar_lote_pix_csv, name='exportar_lote_pix'),
    path('exportar/staff-pdf/<int:user_id>/', views.exportar_ficha_staff_pdf, name='exportar_ficha_staff'),
    path('exportar/extrato-staff-pdf/', views.exportar_extrato_staff_pdf, name='exportar_extrato_staff'),
    path('exportar/evento-excel/<int:evento_id>/', views.exportar_evento_excel, name='exportar_evento_excel'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

path('popular-dados/', views.criar_dados_demo_view, name='popular_dados_web'),