from django.urls import path
from file_processor import views

urlpatterns = [
    # Página principal
    path('', views.index, name='index'),

    # Rutas para la traducción de documentos
    path('translate/', views.upload_translate, name='upload_translate'),
    path('progress_translate/<str:filename>/', views.check_progress_translate, name='check_progress_translate'),
    path('result_translate/<str:filename>/', views.result_translate, name='result_translate'),
    path('download_translate/<str:filename>/', views.download_translate, name='download_translate'),  # Ruta de descarga para traducción
    path('check_status_translate/<str:filename>/', views.check_status_translate, name='check_status_translate'),  # Check status

    # Rutas para el resumen de documentos
    path('summarize/', views.upload_summarize, name='upload_summarize'),
    path('progress_summarize/<str:filename>/', views.check_progress_summarize, name='check_progress_summarize'),
    path('result_summarize/<str:filename>/', views.result_summarize, name='result_summarize'),
    path('download_summarize/<str:filename>/', views.download_summarize, name='download_summarize'),  # Ruta de descarga para resumen
    path('check_status_summarize/<str:filename>/', views.check_status_summarize, name='check_status_summarize'),  # Check status

    # Rutas para la extracción de información (Base de datos)
    path('extract/', views.upload_extract_info, name='upload_extract_info'),
    path('progress_extract/<str:filename>/', views.check_progress_extract_info, name='check_progress_extract_info'),
    path('result_extract/<str:filename>/', views.result_extract_info, name='result_extract_info'),
    path('download_extract/<str:filename>/', views.download_extract_info, name='download_extract_info'),  # Ruta de descarga para extracción
    path('check_status_extract/<str:filename>/', views.check_status_extract_info, name='check_status_extract_info'),  # Check status

    # Rutas para la edición de documentos
    path('edit/', views.upload_edit, name='upload_edit'),
    path('progress_edit/<str:filename>/', views.check_progress_edit, name='check_progress_edit'),
    path('result_edit/<str:filename>/', views.result_edit, name='result_edit'),
    path('download_edit/<str:filename>/', views.download_edit, name='download_edit'),  # Ruta de descarga para edición
    path('check_status_edit/<str:filename>/', views.check_status_edit, name='check_status_edit'),  # Check status

    # Rutas para la transcripción de documentos
    path('transcribe/', views.upload_transcribe, name='upload_transcribe'),
    path('progress_transcribe/<str:filename>/', views.check_progress_transcribe, name='check_progress_transcribe'),
    path('result_transcribe/<str:filename>/', views.result_transcribe, name='result_transcribe'),
    path('download_transcribe/<str:filename>/', views.download_transcribe, name='download_transcribe'),  # Ruta de descarga para transcripción
    path('check_status_transcribe/<str:filename>/', views.check_status_transcribe, name='check_status_transcribe'),  # Check status

    # Otras rutas de funciones adicionales (si tienes más funcionalidades)
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),  # Política de Privacidad
    path('terms-and-conditions/', views.terms_and_conditions, name='terms_and_conditions'),  # Términos y Condiciones
    path('contact/', views.contact, name='contact'),  # Contacto
]
