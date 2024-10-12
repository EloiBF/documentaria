# views.py
import time
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.core.files.storage import FileSystemStorage
import os
import threading
import json
from pathlib import Path
from file_processor.services.doc_translator import traducir_doc
from file_processor.services.audio_transcribe import transcribe_audio
from file_processor.services.doc_editor import editar_doc
from file_processor.services.doc_summary import resumir_doc
from file_processor.services.doc_extract_info import extract_info_from_docs
from file_processor.services.doc_generate import generate_and_create_file
import pandas as pd
import logging

logger = logging.getLogger(__name__)

UPLOAD_FOLDER = os.path.abspath('docs/uploads')
RESULT_FOLDER = os.path.abspath('docs/downloads')
ALLOWED_EXTENSIONS = {'docx', 'pptx', 'pdf', 'txt', 'html', 'm4a', 'wav', 'mp3'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
DELAY_TIME = 36000  # 10 horas (36000 segundos) para eliminar archivos subidos


class FileProcessor:
    def __init__(self, process_func):
        self.process_func = process_func

    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def handle_file_removal(self, file_path):
        threading.Event().wait(20)  # Espera 20 segundos
        if os.path.exists(file_path):
            os.remove(file_path)

    def process_file(self, file, *args):
        fs = FileSystemStorage(UPLOAD_FOLDER)
        filename = fs.save(file.name, file)
        file_path = fs.url(filename)
        result_filename = self.get_result_filename(filename)
        result_file_path = os.path.join(RESULT_FOLDER, result_filename)
        threading.Thread(target=self.process_func, args=(file_path, result_file_path, *args)).start()
        return filename, result_filename

    def download_file(self, filename):
        # Ruta completa del archivo de resultado (traducido o procesado)
        result_file_path = os.path.join(RESULT_FOLDER, filename)
        print(result_file_path)  # Imprime la ruta del archivo de resultado para depuración

        # Verifica si el archivo de resultado existe
        if not os.path.exists(result_file_path):
            raise Http404("Archivo no encontrado")

        # Ruta completa del archivo de subida (el archivo de entrada original)
        upload_file_path = os.path.join(UPLOAD_FOLDER, filename)
        print(upload_file_path)  # Imprime la ruta del archivo de subida para depuración

        # Elimina el archivo de entrada/subida en un hilo separado
        threading.Thread(target=self.handle_file_removal, args=(upload_file_path,)).start()

        # Elimina el archivo de resultado en un hilo separado
        threading.Thread(target=self.handle_file_removal, args=(result_file_path,)).start()

        # Abrir el archivo de resultado en modo binario
        with open(result_file_path, 'rb') as file:
            # Crear la respuesta HTTP con el contenido del archivo
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            # Ajusta el encabezado para que el navegador lo trate como una descarga
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response


    # Función GENERICA para obtener la ruta del archivo de entrada -- se especifica en cada clase
    def get_input_file_path(self, filename):
        return os.path.join(UPLOAD_FOLDER, filename)

    # Función GENERICA para obtener la ruta del archivo de salida -- se especifica en cada clase
    def get_output_file_path(self, original_filename):
        file_ext = os.path.splitext(original_filename)[1].lower()
        if file_ext == '.pdf':
            return os.path.join(RESULT_FOLDER, f"{os.path.splitext(original_filename)[0]}.docx")
        else:
            return os.path.join(RESULT_FOLDER, original_filename)

    def check_status(self, filename):
        result_file_path = self.get_output_file_path(filename)
        return JsonResponse({"status": "completed" if os.path.exists(result_file_path) else "processing"})



# Aquí implementamos las clases específicas para cada tipo de procesamiento
class DocumentTranslator(FileProcessor):
    def __init__(self):
        super().__init__(self.background_translation)

    def background_translation(self, file_path, result_file_path, language, origin_language, color_to_exclude, add_prompt):
        logger.info(f"Starting translation: {file_path} to {result_file_path} from {origin_language} to {language}")
        try:
            if os.path.exists(result_file_path):
                os.remove(result_file_path)

            traducir_doc(
                input_path=file_path,
                output_path=result_file_path,
                origin_language=origin_language,
                destination_language=language,
                extension=os.path.splitext(file_path)[1].lower(),
                color_to_exclude=color_to_exclude,
                add_prompt=add_prompt
            )
        except Exception as e:
            print(f"Error durante la traducción del archivo: {str(e)}")


class AudioTranscriber(FileProcessor):
    def __init__(self):
        super().__init__(self.background_transcribe)

    def get_output_file_path(self, original_filename):
        return os.path.join(RESULT_FOLDER, f"{os.path.splitext(original_filename)[0]}.txt")

    def background_transcribe(self, file_path, result_file_path, audio_language):
        try:
            if os.path.exists(result_file_path):
                os.remove(result_file_path)

            transcribed_text = transcribe_audio(file_path, output_path=result_file_path, language=audio_language, model='whisper-large-v3')
            with open(result_file_path, 'w') as file:
                file.write(transcribed_text)
        except Exception as e:
            print(f"Error durante la transcripción del archivo: {str(e)}")


class DocumentEditor(FileProcessor):
    def __init__(self):
        super().__init__(self.background_edit)

    def background_edit(self, file_path, result_file_path, add_prompt, color_to_exclude):
        try:
            if os.path.exists(result_file_path):
                os.remove(result_file_path)
            extension = os.path.splitext(file_path)[1].lower()
            editar_doc(file_path, result_file_path, extension, color_to_exclude, add_prompt)
        except Exception as e:
            print(f"Error durante la edición del archivo: {str(e)}")


class DocumentSummarizer(FileProcessor):
    def __init__(self):
        super().__init__(self.background_summarize)

    def get_output_file_path(self, original_filename):
        return os.path.join(RESULT_FOLDER, f"{os.path.splitext(original_filename)[0]}.txt")

    def background_summarize(self, file_path, result_file_path, num_words, summary_language, add_prompt):
        try:
            if os.path.exists(result_file_path):
                os.remove(result_file_path)

            summarized_text = resumir_doc(file_path, num_words=num_words, summary_language=summary_language, add_prompt=add_prompt)

            if not isinstance(summarized_text, str):
                raise ValueError("El texto resumido no es una cadena")

            with open(result_file_path, 'w') as file:
                file.write(summarized_text)

        except Exception as e:
            print(f"Error durante el resumen del archivo: {str(e)}")


class InformationExtractor(FileProcessor):
    def __init__(self):
        super().__init__(self.background_extract)

    def get_output_file_path(self, original_filename):
        return os.path.join(RESULT_FOLDER, f"RESULTADO.json")  # Usamos un nombre fijo para el resultado

    def process_files(self, files, prompts, response_types):
        file_paths = []
        result_file_path = self.get_output_file_path("RESULTADO.json")  # Solo hay un resultado

        for file in files:
            fs = FileSystemStorage(UPLOAD_FOLDER)
            filename = fs.save(file.name, file)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file_paths.append(file_path)
        
        # Iniciar el hilo para la extracción en segundo plano
        threading.Thread(target=self.background_extract, args=(file_paths, result_file_path, prompts, response_types)).start()

        return result_file_path  # Retornamos el path del archivo de resultado

    def background_extract(self, file_paths, result_file_path, prompts, response_types):
        print(file_paths)
        try:
            # Eliminar el archivo de resultado si ya existe
            result_file_path = self.get_output_file_path("RESULTADO.json")
            if os.path.exists(result_file_path):
                os.remove(result_file_path)

            extract_info_from_docs(file_paths, result_file_path, prompts, response_types)  
            print(f"Archivo procesado")

            print(f"Datos extraídos y guardados en {result_file_path}")

        except Exception as e:
            print(f"Error durante la extracción de información de los archivos: {str(e)}")


class DocumentGenerator(FileProcessor):
    def __init__(self):
        super().__init__(self.background_generation)

    def get_output_file_path(self, original_filename):
        return os.path.join(RESULT_FOLDER, original_filename)

    def background_generation(self, prompt, result_file_path, file_type='docx'):
        logger.info(f"Starting document generation with prompt: {prompt} to {result_file_path} as {file_type}")
        try:
            if os.path.exists(result_file_path):
                os.remove(result_file_path)

            # Llamar a la función que genera y crea el archivo
            generate_and_create_file(prompt, file_type=file_type, output=result_file_path)
        except Exception as e:
            print(f"Error durante la generación del documento: {str(e)}")




# Instancias para cada tipo de procesamiento
translator = DocumentTranslator()
transcriber = AudioTranscriber()
editor = DocumentEditor()
summarizer = DocumentSummarizer()
extractor = InformationExtractor()
generator = DocumentGenerator()



# Rutas estáticas
def index(request):
    return render(request, 'index.html')

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def terms_and_conditions(request):
    return render(request, 'terms_and_conditions.html')

def about_us(request):
    return render(request, 'about_us.html')

def contact(request):
    return render(request, 'contact.html')



# Rutas de traducción
def upload_translate(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        language = request.POST.get('target_language')
        origin_language = request.POST.get('source_language')
        color_to_exclude = request.POST.get('color_to_exclude', None)
        add_prompt = request.POST.get('add_prompt', '')

        if not file or not language or not origin_language:
            error_message = "Faltan parámetros"
            return render(request, 'upload_translate.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if file.name == '':
            error_message = "No se seleccionó ningún archivo"
            return render(request, 'upload_translate.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if translator.allowed_file(file.name):
            # Guardar el archivo en la carpeta especificada
            fs = FileSystemStorage(UPLOAD_FOLDER)
            fs.save(file.name, file)  # Solo guardamos el archivo

            file_path = translator.get_input_file_path(filename=file.name)  # Ruta completa del archivo guardado
            result_file_path = translator.get_output_file_path(original_filename=file.name)  # Ruta del archivo resultante
            
            # Procesar el archivo en un hilo
            threading.Thread(target=translator.process_func, args=(file_path, result_file_path, language, origin_language, color_to_exclude, add_prompt)).start()

            # Iniciar temporizador para eliminar tanto el archivo subido como el archivo de resultado
            threading.Thread(target=FileProcessor.handle_file_removal, args=(file_path, result_file_path, DELAY_TIME)).start()

            return redirect('check_progress_translate', filename=file.name)

    return render(request, 'upload_translate.html', {'max_file_size': MAX_CONTENT_LENGTH})

def check_progress_translate(request, filename):
    result_file_path = translator.get_output_file_path(filename)
    if os.path.exists(result_file_path):
        return redirect('result_translate', filename=filename)
    return render(request, 'progress_translate.html', {'filename': filename})

def result_translate(request, filename):
    result_file_path = translator.get_output_file_path(filename)

    if os.path.exists(result_file_path):
        return render(request, 'result_translate.html', {'filename': filename})
    else:
        raise Http404("Archivo no encontrado")

def download_translate(request, filename):
    return translator.download_file(filename)

def check_status_translate(request, filename):
    return translator.check_status(filename)


# Rutas de transcripción
def upload_transcribe(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        audio_language = request.POST.get('audio_language')

        if not file or not audio_language:
            error_message = "Faltan parámetros"
            return render(request, 'upload_transcribe.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if transcriber.allowed_file(file.name):
            fs = FileSystemStorage(UPLOAD_FOLDER)
            fs.save(file.name, file)  # Guardar archivo en la carpeta uploads
            file_path = transcriber.get_input_file_path(filename=file.name)  # Ruta completa del archivo guardado
            result_file_path = transcriber.get_output_file_path(original_filename=file.name)
            
            # Procesar el archivo en un hilo
            threading.Thread(target=transcriber.process_func, args=(file_path, result_file_path, audio_language)).start()

            # Iniciar temporizador para eliminar tanto el archivo subido como el archivo de resultado
            threading.Thread(target=FileProcessor.handle_file_removal, args=(file_path, result_file_path, DELAY_TIME)).start()

            return redirect('check_progress_transcribe', filename=file.name)

    return render(request, 'upload_transcribe.html', {'max_file_size': MAX_CONTENT_LENGTH})

def check_progress_transcribe(request, filename):
    result_file_path = transcriber.get_output_file_path(filename)
    if os.path.exists(result_file_path):
        return redirect('result_transcribe', filename=filename)
    return render(request, 'progress_transcribe.html', {'filename': filename})

def result_transcribe(request, filename):
    result_file_path = transcriber.get_output_file_path(filename)

    if os.path.exists(result_file_path):
        # Leer el contenido del archivo de resultado
        with open(result_file_path, 'r') as result_file:
            transcription_content = result_file.read()  # Leer el contenido del archivo

        return render(request, 'result_transcribe.html', {'filename': filename, 'transcription': transcription_content})
    else:
        raise Http404("Archivo no encontrado")

def download_transcribe(request, filename):
    return transcriber.download_file(filename)

def check_status_transcribe(request, filename):
    return transcriber.check_status(filename)


# Rutas de edición
def upload_edit(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        add_prompt = request.POST.get('add_prompt')
        color_to_exclude = request.POST.get('color_to_exclude', None)

        if not file:
            error_message = "Faltan parámetros"
            return render(request, 'upload_edit.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if file.name == '':
            error_message = "No se seleccionó ningún archivo"
            return render(request, 'upload_edit.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if editor.allowed_file(file.name):
            fs = FileSystemStorage(UPLOAD_FOLDER)
            fs.save(file.name, file)  # Guardar archivo en la carpeta uploads
            file_path = editor.get_input_file_path(filename=file.name)  # Ruta completa del archivo guardado
            result_file_path = editor.get_output_file_path(original_filename=file.name)  # Ruta del archivo resultante
            
            # Procesar el archivo en un hilo
            threading.Thread(target=editor.process_func, args=(file_path, result_file_path, add_prompt, color_to_exclude)).start()

            # Iniciar temporizador para eliminar tanto el archivo subido como el archivo de resultado
            threading.Thread(target=FileProcessor.handle_file_removal, args=(file_path, result_file_path, DELAY_TIME)).start()

            return redirect('check_progress_edit', filename=file.name)
    return render(request, 'upload_edit.html', {'max_file_size': MAX_CONTENT_LENGTH})

def check_progress_edit(request, filename):
    result_file_path = editor.get_output_file_path(filename)
    if os.path.exists(result_file_path):
        return redirect('result_edit', filename=filename)
    return render(request, 'progress_edit.html', {'filename': filename})

def result_edit(request, filename):
    result_file_path = editor.get_output_file_path(filename)

    if os.path.exists(result_file_path):
        return render(request, 'result_edit.html', {'filename': filename})
    else:
        raise Http404("Archivo no encontrado")

def download_edit(request, filename):
    return editor.download_file(filename)

def check_status_edit(request, filename):
    return editor.check_status(filename)



# Rutas de resumen
def upload_summarize(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        num_words = request.POST.get('num_words')
        summary_language = request.POST.get('summary_language')
        add_prompt = request.POST.get('add_prompt')

        if not file or not num_words or not summary_language:
            error_message = "Faltan parámetros"
            return render(request, 'upload_summarize.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if summarizer.allowed_file(file.name):
            fs = FileSystemStorage(UPLOAD_FOLDER)
            fs.save(file.name, file)  # Guardar archivo en la carpeta uploads
            file_path = summarizer.get_input_file_path(filename=file.name)  # Ruta completa del archivo guardado
            result_file_path = summarizer.get_output_file_path(original_filename=file.name)
            
            # Procesar el archivo en un hilo
            threading.Thread(target=summarizer.process_func, args=(file_path, result_file_path, num_words, summary_language, add_prompt)).start()

            # Iniciar temporizador para eliminar tanto el archivo subido como el archivo de resultado
            threading.Thread(target=FileProcessor.handle_file_removal, args=(file_path, result_file_path, DELAY_TIME)).start()

            return redirect('check_progress_summarize', filename=file.name)

    return render(request, 'upload_summarize.html', {'max_file_size': MAX_CONTENT_LENGTH})

def check_progress_summarize(request, filename):
    result_file_path = summarizer.get_output_file_path(filename)
    if os.path.exists(result_file_path):
        return redirect('result_summarize', filename=filename)
    return render(request, 'progress_summarize.html', {'filename': filename})

def result_summarize(request, filename):
    result_file_path = summarizer.get_output_file_path(filename)

    if os.path.exists(result_file_path):
        # Leer el contenido del archivo de resultado
        with open(result_file_path, 'r') as result_file:
            summary_content = result_file.read()  # Leer el contenido del archivo

        return render(request, 'result_summarize.html', {'filename': filename, 'summary': summary_content})
    else:
        raise Http404("Archivo no encontrado")

def download_summarize(request, filename):
    return summarizer.download_file(filename)

def check_status_summarize(request, filename):
    return summarizer.check_status(filename)













# Vista para manejar la subida de archivos y extracción de información
def upload_extract_info(request):
    if request.method == 'POST':
        files = request.FILES.getlist('files')  # Ahora coincide con el nombre del input
        prompts = request.POST.getlist('prompts')  # Obtener múltiples prompts
        response_types = request.POST.getlist('response_types')  # Obtener tipos de respuesta

        extractor = InformationExtractor()
        result_file_path = extractor.process_files(files, prompts, response_types)

        return redirect('check_progress_extract', filename='RESULTADO.json')  # Redirigir al progreso

    return render(request, 'upload_extract_info.html')


# Vista para verificar el progreso de la extracción de información
def check_progress_extract(request, filename):
    result_file_path = os.path.join(RESULT_FOLDER, filename)

    # Comprobar si el archivo de resultado ya existe
    if os.path.exists(result_file_path):
        return redirect('result_extract_info', filename=filename)

    return render(request, 'progress_extract_info.html', {'filename': filename, 'result_filename': 'RESULTADO.json'})


# Vista para mostrar los resultados de la extracción de información
def result_extract_info(request, filename):
    result_file_path = os.path.join(RESULT_FOLDER, filename)

    if os.path.exists(result_file_path):
        # Leer el contenido del archivo de resultado
        with open(result_file_path, 'r', encoding='utf-8') as result_file:
            result_content = json.load(result_file)  # Cargar el contenido JSON

        # Convertir el diccionario en un DataFrame
        df = pd.DataFrame.from_dict(result_content, orient='index')

        # Convertir el DataFrame a HTML
        result_table_html = df.to_html(classes='result-table', index=True, header=True)

        return render(request, 'result_extract_info.html', {
            'filename': filename,
            'result_table': result_table_html,  # Pasar la tabla HTML
        })
    else:
        raise Http404("Archivo no encontrado")

# Vista para descargar los resultados combinados de la extracción de información
def download_extract_info(request):
    result_file_path = os.path.join(RESULT_FOLDER, 'RESULTADO.json')

    if os.path.exists(result_file_path):
        with open(result_file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename="RESULTADO.json"'
            return response
    else:
        raise Http404("Archivo no encontrado")


# Vista para verificar el estado de la extracción de un archivo específico
def check_status_extract_info(request, filename='RESULTADO.json'):
    result_file_path = os.path.join(RESULT_FOLDER, filename)  # Usamos 'RESULTADO.JSON'
        # Comprobar si el archivo de resultado ya existe
    if os.path.exists(result_file_path):
        return JsonResponse({'status': 'completed'})  # Retornar el estado como completado
    return JsonResponse({'status': 'processing'})  # Indicar que todavía se está procesando










# Rutas para la generación de documentos
def upload_generate(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        file_type = request.POST.get('pptx', 'docx')  # Puedes permitir que el usuario elija el tipo de archivo
        
        if not prompt:
            error_message = "Falta el prompt"
            return render(request, 'upload_generate.html', {'error_message': error_message})

        # Generar un nombre de archivo único
        result_filename = f"document_generated_{int(time.time())}.{file_type}"
        result_file_path = os.path.join(RESULT_FOLDER, result_filename)

        # Procesar el archivo en un hilo
        threading.Thread(target=generator.process_func, args=(prompt, result_file_path, file_type)).start()

        # Iniciar temporizador para eliminar el archivo de resultado
        threading.Thread(target=FileProcessor.handle_file_removal, args=(None, result_file_path, DELAY_TIME)).start()

        return redirect('check_progress_generate', filename=result_filename)

    return render(request, 'upload_generate.html')


def check_progress_generate(request, filename):
    result_file_path = os.path.join(RESULT_FOLDER, filename)
    if os.path.exists(result_file_path):
        return redirect('result_generate', filename=filename)
    return render(request, 'progress_generate.html', {'filename': filename})


def result_generate(request, filename):
    result_file_path = os.path.join(RESULT_FOLDER, filename)

    if os.path.exists(result_file_path):
        return render(request, 'result_generate.html', {'filename': filename})
    else:
        raise Http404("Archivo no encontrado")


def download_generate(request, filename):
    return generator.download_file(filename)


def check_status_generate(request, filename):
    return generator.check_status(filename)
