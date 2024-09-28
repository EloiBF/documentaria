# views.py

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.core.files.storage import FileSystemStorage
import os
import threading
import json
from pathlib import Path
from file_processor.documentaria_scripts.doc_translator import traducir_doc
from file_processor.documentaria_scripts.audio_transcribe import transcribe_audio
from file_processor.documentaria_scripts.doc_editor import editar_doc
from file_processor.documentaria_scripts.doc_summary import resumir_doc
from file_processor.documentaria_scripts.doc_extract_info import extract_info_from_doc

UPLOAD_FOLDER = os.path.abspath('docs/uploads')
RESULT_FOLDER = os.path.abspath('docs/downloads')
ALLOWED_EXTENSIONS = {'docx', 'pptx', 'pdf', 'txt', 'html', 'm4a', 'wav', 'mp3'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

class FileProcessor:
    def __init__(self, process_func):
        self.process_func = process_func

    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def get_result_filename(self, filename):
        raise NotImplementedError("Subclasses should implement this method")

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
        result_file_path = os.path.join(RESULT_FOLDER, filename)

        if not os.path.exists(result_file_path):
            raise Http404("Archivo no encontrado")

        threading.Thread(target=self.handle_file_removal, args=(result_file_path,)).start()
        return HttpResponse(result_file_path, content_type='application/octet-stream')

    def check_status(self, filename):
        result_filename = self.get_result_filename(filename)
        result_file_path = os.path.join(RESULT_FOLDER, result_filename)

        return JsonResponse({"status": "completed" if os.path.exists(result_file_path) else "processing"})

# Aquí implementamos las clases específicas para cada tipo de procesamiento
class DocumentTranslator(FileProcessor):
    def __init__(self):
        super().__init__(self.background_translation)

    def get_result_filename(self, filename):
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext == '.pdf':
            return f"{os.path.splitext(filename)[0]}.docx"
        else:
            return filename

    def background_translation(self, file_path, result_file_path, language, origin_language, color_to_exclude, add_prompt):
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

    def get_result_filename(self, filename):
        return f"{os.path.splitext(filename)[0]}.txt"

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

    def get_result_filename(self, filename):
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext == '.pdf':
            return f"{os.path.splitext(filename)[0]}.docx"
        else:
            return filename  # Mantener el mismo nombre de archivo

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

    def get_result_filename(self, filename):
        return f"{os.path.splitext(filename)[0]}.txt"

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

    def get_result_filename(self, filename):
        return f"{os.path.splitext(filename)[0]}.json"

    def process_file(self, file, prompts, response_types):
        fs = FileSystemStorage(UPLOAD_FOLDER)
        filename = fs.save(file.name, file)
        file_path = fs.url(filename)
        result_filename = self.get_result_filename(filename)
        result_file_path = os.path.join(RESULT_FOLDER, result_filename)

        threading.Thread(target=self.background_extract, args=(file_path, result_file_path, prompts, response_types)).start()

        return filename, result_filename

    def background_extract(self, file_path, result_file_path, prompts, response_types):
        try:
            if os.path.exists(result_file_path):
                os.remove(result_file_path)

            extracted_data = extract_info_from_doc(file_path, result_file_path, prompts, response_types)

            with open(result_file_path, 'w') as file:
                json.dump(extracted_data, file, indent=4)

        except Exception as e:
            print(f"Error durante la extracción de información del archivo: {str(e)}")

# Instancias para cada tipo de procesamiento
translator = DocumentTranslator()
transcriber = AudioTranscriber()
editor = DocumentEditor()
summarizer = DocumentSummarizer()
extractor = InformationExtractor()

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
            return render(request, 'serv_translate.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if file.name == '':
            error_message = "No se seleccionó ningún archivo"
            return render(request, 'serv_translate.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if translator.allowed_file(file.name):
            filename, result_filename = translator.process_file(file, language, origin_language, color_to_exclude, add_prompt)
            return redirect('check_progress_translate', filename=result_filename)

    return render(request, 'serv_translate.html', {'max_file_size': MAX_CONTENT_LENGTH})

def check_progress_translate(request, filename):
    result_filename = translator.get_result_filename(filename)
    result_file_path = os.path.join(RESULT_FOLDER, result_filename)
    if os.path.exists(result_file_path):
        return redirect('result_translate', filename=result_filename)
    return render(request, 'serv_translate_progress.html', {'filename': filename})

def result_translate(request, filename):
    result_filename = translator.get_result_filename(filename)
    result_file_path = os.path.join(RESULT_FOLDER, result_filename)

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
            return render(request, 'serv_transcribe.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if transcriber.allowed_file(file.name):
            filename, result_filename = transcriber.process_file(file, audio_language)
            return redirect('check_progress_transcribe', filename=result_filename)

    return render(request, 'serv_transcribe.html', {'max_file_size': MAX_CONTENT_LENGTH})

def check_progress_transcribe(request, filename):
    result_filename = transcriber.get_result_filename(filename)
    result_file_path = os.path.join(RESULT_FOLDER, result_filename)
    if os.path.exists(result_file_path):
        return redirect('result_transcribe', filename=result_filename)
    return render(request, 'serv_transcribe_progress.html', {'filename': filename})

def result_transcribe(request, filename):
    result_filename = transcriber.get_result_filename(filename)
    result_file_path = os.path.join(RESULT_FOLDER, result_filename)

    if os.path.exists(result_file_path):
        return render(request, 'result_transcribe.html', {'filename': filename})
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
            return render(request, 'serv_edit.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if editor.allowed_file(file.name):
            filename, result_filename = editor.process_file(file, add_prompt, color_to_exclude)
            return redirect('check_progress_edit', filename=result_filename)

    return render(request, 'serv_edit.html', {'max_file_size': MAX_CONTENT_LENGTH})

def check_progress_edit(request, filename):
    result_filename = editor.get_result_filename(filename)
    result_file_path = os.path.join(RESULT_FOLDER, result_filename)
    if os.path.exists(result_file_path):
        return redirect('result_edit', filename=result_filename)
    return render(request, 'serv_edit_progress.html', {'filename': filename})

def result_edit(request, filename):
    result_filename = editor.get_result_filename(filename)
    result_file_path = os.path.join(RESULT_FOLDER, result_filename)

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
            return render(request, 'serv_summarize.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if summarizer.allowed_file(file.name):
            filename, result_filename = summarizer.process_file(file, num_words, summary_language, add_prompt)
            return redirect('check_progress_summarize', filename=result_filename)

    return render(request, 'serv_summarize.html', {'max_file_size': MAX_CONTENT_LENGTH})

def check_progress_summarize(request, filename):
    result_filename = summarizer.get_result_filename(filename)
    result_file_path = os.path.join(RESULT_FOLDER, result_filename)
    if os.path.exists(result_file_path):
        return redirect('result_summarize', filename=result_filename)
    return render(request, 'serv_summarize_progress.html', {'filename': filename})

def result_summarize(request, filename):
    result_filename = summarizer.get_result_filename(filename)
    result_file_path = os.path.join(RESULT_FOLDER, result_filename)

    if os.path.exists(result_file_path):
        return render(request, 'result_summarize.html', {'filename': filename})
    else:
        raise Http404("Archivo no encontrado")

def download_summarize(request, filename):
    return summarizer.download_file(filename)

def check_status_summarize(request, filename):
    return summarizer.check_status(filename)

# Rutas de extracción de información
def upload_extract_info(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        prompts = request.POST.get('prompts')
        response_types = request.POST.get('response_types')

        if not file or not prompts or not response_types:
            error_message = "Faltan parámetros"
            return render(request, 'serv_extract_info.html', {'max_file_size': MAX_CONTENT_LENGTH, 'error_message': error_message})

        if extractor.allowed_file(file.name):
            filename, result_filename = extractor.process_file(file, prompts, response_types)
            return redirect('check_progress_extract_info', filename=result_filename)

    return render(request, 'serv_extract_info.html', {'max_file_size': MAX_CONTENT_LENGTH})

def check_progress_extract_info(request, filename):
    result_filename = extractor.get_result_filename(filename)
    result_file_path = os.path.join(RESULT_FOLDER, result_filename)
    if os.path.exists(result_file_path):
        return redirect('result_extract_info', filename=result_filename)
    return render(request, 'serv_extract_info_progress.html', {'filename': filename})

def result_extract_info(request, filename):
    result_filename = extractor.get_result_filename(filename)
    result_file_path = os.path.join(RESULT_FOLDER, result_filename)

    if os.path.exists(result_file_path):
        return render(request, 'serv_extract_result.html', {'filename': filename})
    else:
        raise Http404("Archivo no encontrado")

def download_extract_info(request, filename):
    return extractor.download_file(filename)

def check_status_extract_info(request, filename):
    return extractor.check_status(filename)
