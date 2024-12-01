from django.contrib import admin
from django.urls import path
from frontend import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),  # Página principal
    path('download/<str:filename>/', views.download, name='download'),  # Descargar documento generado
    path('check_file/<str:filename>/', views.check_file_status, name='check_file_status'),

    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),

    # Rutas estáticas
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),  # Política de privacidad
    path('terms-and-conditions/', views.terms_and_conditions, name='terms_and_conditions'),  # Términos y condiciones
    path('about-us/', views.about_us, name='about_us'),  # Sobre nosotros
    path('contact/', views.contact, name='contact'),  # Contacto

    # Rutas para "generate"
    path('upload_generate/', views.upload_generate, name='upload_generate'),   
    path('progress_generate/<str:filename>/', views.progress_generate, name='progress_generate'),
    path('result_generate/<str:filename>/', views.result_generate, name='result_generate'),

    # Rutas para "translate"
    path('upload_translate/', views.upload_translate, name='upload_translate'),    
    path('progress_translate/<str:filename>/', views.progress_translate, name='progress_translate'),
    path('result_translate/<str:filename>/', views.result_translate, name='result_translate'),  

    # Rutas para "edit"
    path('upload_edit/', views.upload_edit, name='upload_edit'),
    path('progress_edit/<str:filename>/', views.progress_edit, name='progress_edit'),
    path('result_edit/<str:filename>/', views.result_edit, name='result_edit'),

    # Rutas para "transcribe"
    path('upload_transcribe/', views.upload_transcribe, name='upload_transcribe'),
    path('progress_transcribe/<str:filename>/', views.progress_transcribe, name='progress_transcribe'),
    path('result_transcribe/<str:filename>/', views.result_transcribe, name='result_transcribe'),

    # Rutas para "analyze"
    path('upload_analyze/', views.upload_analyze, name='upload_analyze'),
    path('progress_analyze/<str:filename>/', views.progress_analyze, name='progress_analyze'),
    path('result_analyze/<str:filename>/', views.result_analyze, name='result_analyze'),

    # Rutas para "summarize"
    path('upload_summarize/', views.upload_summarize, name='upload_summarize'),
    path('progress_summarize/<str:filename>/', views.progress_summarize, name='progress_summarize'),
    path('result_summarize/<str:filename>/', views.result_summarize, name='result_summarize'),

    # Rutas para embedding

]



# Añadir la configuración para servir archivos de medios durante el desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
