from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticação & Demo
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('login/demo/<str:tipo>/', views.login_demo_direto_view, name='login_demo_direto'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/staff/', views.registro_staff_view, name='registro_staff'),

    # Portal do Cliente
    path('portal-aprovacao/<str:token>/', views.portal_aprovacao_cliente_view, name='portal_aprovacao_cliente'),

    # Diagnóstico & Povoamento
    path('status-db/', views.status_db_view, name='status_db'),
    path('popular-dados/', views.criar_dados_demo_view, name='popular_dados_web'),

    # Dashboards
    path('dashboard/super-admin/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('dashboard/empresa/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/staff/', views.staff_dashboard, name='staff_dashboard'),

    # Ghost Login
    path('ghost-login/<int:user_id>/', views.ghost_login_view, name='ghost_login'),

    # Exportações & Relatórios
    path('exportar/casting-cliente-pdf/<int:evento_id>/', views.exportar_casting_cliente_pdf, name='exportar_casting_cliente_pdf'),
    path('exportar/post-event-pdf/<int:evento_id>/', views.exportar_relatorio_post_event_pdf, name='exportar_relatorio_post_event_pdf'),
    path('exportar/lote-pix-csv/', views.exportar_lote_pix_csv, name='exportar_lote_pix_csv'),
    path('exportar/pagamentos-evento/<int:evento_id>/', views.exportar_pagamentos_evento_csv, name='exportar_pagamentos_evento_csv'),
    path('exportar/extrato-staff/<int:user_id>/', views.exportar_extrato_staff_pdf, name='exportar_extrato_staff_pdf'),
    path('exportar/ficha-staff/<int:user_id>/', views.exportar_ficha_staff_pdf, name='exportar_ficha_staff_pdf'),
    path('exportar/caches-excel/', views.exportar_caches_excel, name='exportar_caches_excel'),
    path('exportar/caches-pdf/', views.exportar_caches_pdf, name='exportar_caches_pdf'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)