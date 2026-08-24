from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('registro/staff/', views.registro_staff_view, name='registro_staff'),
    path('logout/', views.logout_view, name='logout'),
    
    path('dashboard/super-admin/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('ghost-login/<int:user_id>/', views.ghost_login_view, name='ghost_login'),
    path('dashboard/empresa/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/staff/', views.staff_dashboard, name='staff_dashboard'),

    # Rotas de Exportação
    path('exportar/excel/', views.exportar_caches_excel, name='exportar_excel'),
    path('exportar/pdf/', views.exportar_caches_pdf, name='exportar_pdf'),
    path('exportar/staff-pdf/<int:user_id>/', views.exportar_ficha_staff_pdf, name='exportar_ficha_staff_pdf'),
    path('exportar/extrato-staff-pdf/', views.exportar_extrato_staff_pdf, name='exportar_extrato_staff_pdf'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)