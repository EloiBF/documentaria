import os
import time
import threading
import requests
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404, JsonResponse
from django.conf import settings
import json
import tempfile
import shutil
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required


# Vista de registre d'usuaris
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "El teu compte s'ha creat amb èxit. Ja pots iniciar sessió!")
            return redirect('login')  # Redirigeix a la pàgina d'inici de sessió
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

logger = logging.getLogger(__name__)

# Carpeta donde se guardarán los documentos generados temporalmente
RESULT_FOLDER = settings.DOWNLOADS_ROOT
os.makedirs(RESULT_FOLDER, exist_ok=True)
DELETE_TIME = settings.DELETE_TIME


class DocumentService:
    ALLOWED_EXTENSIONS = ['pdf', 'docx', 'xlsx', 'pptx', 'txt', 'html']

    def __init__(self, service_name, api_url):
        self.service_name = service_name
        self.api_url = api_url

    @staticmethod
    def is_allowed_extension(filename):
        extension = os.path.splitext(filename)[1].lstrip('.').lower()
        return extension in DocumentService.ALLOWED_EXTENSIONS

    @staticmethod
    def download(request, filename):
        file_path = os.path.join(RESULT_FOLDER, filename)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            threading.Thread(target=DocumentService.remove_file, args=(file_path, 30)).start()
            return response
        raise Http404("Archivo no encontrado")

    @staticmethod
    def remove_file(file_path, delay):
        time.sleep(delay)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Archivo {file_path} eliminado después del tiempo de espera.")
        except Exception as e:
            print(f"Error al eliminar el archivo: {e}")

    @staticmethod
    def save_file(file):
        fs = FileSystemStorage(RESULT_FOLDER)
        file_path = fs.save(file.name, file)
        return os.path.join(RESULT_FOLDER, file_path)

    def get_request_data(self, **kwargs):
        """
        Método para que las clases derivadas definan los parámetros de la solicitud.
        """
        raise NotImplementedError("Este método debe ser implementado por la subclase")

    def check_result_file_exists(self, filename):
        """
        Verifica si el archivo de resultados existe en el directorio de resultados.
        :param filename: Nombre del archivo a verificar.
        :return: True si el archivo existe, False de lo contrario.
        """
        result_file_path = os.path.join(RESULT_FOLDER, filename)
        return os.path.exists(result_file_path)

    def call_api(self, request_data):
        print('RUUUUUUUN')
        try:
            # En este caso, request_data ya debe contener el payload necesario
            print(f"Enviando solicitud a la API: {self.api_url} con datos: {request_data}")  

            # Configuración de la solicitud
            if 'files' in request_data:
                # Si hay archivos, se envían así
                response = requests.post(
                    self.api_url,
                    data=request_data['data'],  # Envía los datos como formulario
                    files=request_data['files']  # Envía el archivo
                )
            else:
                # Si no hay archivos, solo se envían los datos
                response = requests.post(
                    self.api_url,
                    json=request_data['data'],  # Envía los datos como formulario
                )

            response.raise_for_status()  # Levanta un error si la respuesta es un error HTTP

            # Verificar el tamaño y contenido de la respuesta
            print(f"Respuesta de la API recibida, tamaño: {len(response.content)} bytes")  

            # Guardar el contenido de la respuesta en el archivo especificado
            result_file_path = request_data.get('file_path') 
            with open(result_file_path, 'wb') as file:
                file.write(response.content)
            
            print(f"Archivo guardado en {result_file_path}")  

            # Iniciar un hilo para eliminar el archivo generado después de 2 minutos
            threading.Thread(target=self.remove_file, args=(result_file_path, 120)).start()
        
        except requests.exceptions.RequestException as e:
            print(f"Error en la llamada a la API: {str(e)}")  # Log para errores de solicitud
        except Exception as e:
            print(f"Error al guardar el archivo: {str(e)}")  # Log para errores al guardar


class API_GENERATE(DocumentService):
    def __init__(self):
        super().__init__('generate', 'http://agents:5000/generate')

    def generate_unique_filename(self, file_type):
        return f"document_generated_{int(time.time())}.{file_type}"

    def handle_request(self, request):
        if request.method == 'POST':
            prompt = request.POST.get('prompt')
            file_type = request.POST.get('file_type', 'docx')

            if not prompt:
                return render(request, 'upload_generate.html', {'error_message': "Falta el prompt"})

            result_filename = self.generate_unique_filename(file_type)
            result_file_path = os.path.join(RESULT_FOLDER, result_filename)

            # Crear el payload que se envía a la API
            request_data = {
                'file_path': result_file_path,  # Ruta fichero Resultado
                'data': {'prompt': prompt, 'file_type': file_type},
            }

            thread = threading.Thread(target=self.call_api, args=(request_data,))
            thread.start()

            threading.Thread(target=self.remove_file, args=(result_file_path, DELETE_TIME)).start()

            return redirect('progress_generate', filename=result_filename)

        return render(request, 'upload_generate.html')

class API_TRANSLATE(DocumentService):
    def __init__(self):
        super().__init__('translate', 'http://agents:5000/translate')

    def generate_unique_filename(self, original_name):
        """Genera un nombre único basado en el nombre del archivo original y un timestamp.
        Si el archivo es un PDF, cambia la extensión a .docx.
        """
        base_name = os.path.splitext(original_name)[0]  # Obtiene el nombre sin la extensión.
        extension = os.path.splitext(original_name)[1].lstrip('.').lower()  # Obtiene la extensión original.
        
        # Si el archivo es PDF, cambiar la extensión a 'docx'.
        if extension == 'pdf':
            extension = 'docx'
        
        # Agregar un timestamp para hacer el nombre único.
        timestamp = int(time.time())
        return f"{base_name}_translated_{timestamp}.{extension}"

    def handle_request(self, request):
            if request.method == 'POST':
                file = request.FILES.get('file')
                target_language = request.POST.get('target_language')
                source_language = request.POST.get('source_language')
                color_to_exclude = request.POST.get('color_to_exclude', None)
                add_prompt = request.POST.get('add_prompt', '')
                use_embedding = request.POST.get('use_embedding', 'NO') 

                print(use_embedding)

                if not file or not target_language or not source_language:
                    return render(request, 'upload_translate.html', {'error_message': "Faltan parámetros: asegúrate de que se haya cargado un archivo y que se hayan especificado los idiomas."})

                if not self.is_allowed_extension(file.name):
                    return render(request, 'upload_translate.html', {'error_message': "El tipo de archivo no es soportado."})

                # Guardamos temporalmente el archivo subido.
                file_path = self.save_file(file)
                result_filename = self.generate_unique_filename(file.name)  # Generar un nombre único.
                result_file_path = os.path.join(RESULT_FOLDER, result_filename)

                # Configuración de los datos de la solicitud a la API de traducción
                request_data = {
                    'files': {'file': open(file_path, 'rb')},
                    'file_path': result_file_path ,  # Ruta Archivo resultante. app.py de agents lo crea y procesa el borrado.                  
                    'data': {
                        'origin_language': source_language,
                        'destination_language': target_language,
                        'color_to_exclude': color_to_exclude,
                        'add_prompt': add_prompt,
                        'use_embedding':use_embedding
                    },
                }

                # Llamada a la API y guardado del archivo en un hilo separado.
                thread = threading.Thread(target=self.call_api, args=(request_data,))
                thread.start()
                # Programar eliminación del archivo después de XX segundos
                threading.Thread(target=self.remove_file, args=(result_file_path, DELETE_TIME)).start()

                return redirect('progress_translate', filename=result_filename)

            return render(request, 'upload_translate.html')

class API_EDIT(DocumentService):
    def __init__(self):
        super().__init__('translate', 'http://agents:5000/edit')

    def generate_unique_filename(self, original_name):
        base_name = os.path.splitext(original_name)[0]
        extension = os.path.splitext(original_name)[1].lstrip('.').lower()
        
        if extension == 'pdf':
            extension = 'docx'
        
        timestamp = int(time.time())
        return f"{base_name}_edited_{timestamp}.{extension}"

    def handle_request(self, request):
        if request.method == 'POST':
            file = request.FILES.get('file')
            color_to_exclude = request.POST.get('color_to_exclude', None)
            add_prompt = request.POST.get('add_prompt', '')

            if not file:
                return render(request, 'upload_edit.html', {'error_message': "No se ha cargado ningún archivo."})
            
            if not self.is_allowed_extension(file.name):
                return render(request, 'upload_edit.html', {'error_message': "El tipo de archivo no es soportado."})

            # Guardar temporalmente el archivo subido
            file_path = self.save_file(file)
            result_filename = self.generate_unique_filename(file.name)
            result_file_path = os.path.join(RESULT_FOLDER, result_filename)

            # Crear el payload directamente en handle_request
            request_data = {
                'files': {'file': open(file_path, 'rb')},
                'file_path': result_file_path,  # Ruta Archivo resultante
                'data': {
                    'color_to_exclude': color_to_exclude,
                    'add_prompt': add_prompt
                },
            }

            # Llama a la API en un hilo separado
            thread = threading.Thread(target=self.call_api, args=(request_data,))
            thread.start()

            # Programar eliminación del archivo después de 120 segundos
            threading.Thread(target=self.remove_file, args=(result_file_path, DELETE_TIME)).start()

            return redirect('progress_edit', filename=result_filename)

        return render(request, 'upload_edit.html')
    
class API_TRANSCRIBE(DocumentService):
    def __init__(self):
        super().__init__('transcribe', 'http://agents:5000/transcribe')

    def generate_unique_filename(self, original_name):
        base_name = os.path.splitext(original_name)[0]
        timestamp = int(time.time())
        return f"{base_name}_transcribed_{timestamp}.txt"

    def handle_request(self, request):
        if request.method == 'POST':
            audio_file = request.FILES.get('file')
            language = request.POST.get('language', 'auto')
            add_prompt = request.POST.get('add_prompt', '')
            model = request.POST.get('model', 'distil-whisper-large-v3-en')

            if not audio_file:
                return render(request, 'upload_transcribe.html', {'error_message': "Faltan parámetros: asegúrate de que se haya cargado un archivo de audio."})

            file_path = self.save_file(audio_file)
            result_filename = self.generate_unique_filename(audio_file.name)
            result_file_path = os.path.join(RESULT_FOLDER, result_filename)

            # Crear el payload directamente en handle_request
            request_data = {
                    'files': {'file': open(file_path, 'rb')},
                    'file_path': result_file_path ,  # Ruta Archivo resultante. call_API lo crea y procesa el borrado.         
                'data': {
                    'language': language,
                    'add_prompt': add_prompt,
                    'model': model
                },
            }

            thread = threading.Thread(target=self.call_api, args=(request_data,))
            thread.start()

            # Programar eliminación del archivo después de 120 segundos
            threading.Thread(target=self.remove_file, args=(result_file_path, DELETE_TIME)).start()

            return redirect('progress_transcribe', filename=result_filename)

        return render(request, 'upload_transcribe.html')

class API_ANALYZE(DocumentService):
    def __init__(self):
        super().__init__('analyze', 'http://agents:5000/analyze')

    def generate_unique_filename(self, original_name):
        base_name = os.path.splitext(original_name)[0]
        timestamp = int(time.time())
        return f"{base_name}_analysis_{timestamp}.json"

    def save_file(self, file):
        """Guardar el archivo subido temporalmente y devolver su ruta."""
        file_path = os.path.join(RESULT_FOLDER, file.name)
        with open(file_path, 'wb') as dest:
            for chunk in file.chunks():
                dest.write(chunk)
        return file_path

    def call_api(self, request_data):
        """Enviar los archivos y datos al servicio externo."""
        try:
            files = request_data.pop('files')  # Extraer los archivos del payload

            # Enviar el request con multipart/form-data
            response = requests.post(self.api_url, files=files, data=request_data['data'])
            
            if response.status_code == 200:
                with open(request_data['file_path'], 'wb') as f:
                    f.write(response.content)
                print(f"Resultado guardado en {request_data['file_path']}")
            else:
                print(f"Error en la API: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error durante la llamada a la API: {str(e)}")

    def handle_request(self, request):
        if request.method == 'POST':
            files = request.FILES.getlist('files')
            prompts = request.POST.getlist('prompts')
            tipos_respuesta = request.POST.getlist('response_types')
            ejemplos_respuesta = request.POST.getlist('ejemplos_respuesta', None)

            if not files or not prompts or not tipos_respuesta:
                return render(request, 'upload_analyze.html', {'error_message': "Faltan parámetros: asegúrate de haber cargado los archivos y especificado los prompts."})

            file_paths = [self.save_file(file) for file in files]
            result_filename = self.generate_unique_filename(files[0].name)
            result_file_path = os.path.join(RESULT_FOLDER, result_filename)

            # Preparar archivos y datos para el payload, sin pasar los nombres originales
            request_data = {
                'files': [('files', open(file_path, 'rb')) for file_path in file_paths],  # Lista de archivos a enviar
                'file_path': result_file_path,  # Ruta donde se guardará el resultado
                'data': {
                    'prompts': prompts,
                    'tipos_respuesta': tipos_respuesta,
                    'ejemplos_respuesta': ejemplos_respuesta if ejemplos_respuesta else [],
                }
            }

            # Iniciar el thread para llamar a la API sin bloquear el flujo principal
            thread = threading.Thread(target=self.call_api, args=(request_data,))
            thread.start()

            # Programar eliminación del archivo después de 120 segundos
            threading.Thread(target=self.remove_file, args=(result_file_path, DELETE_TIME)).start()

            return redirect('progress_analyze', filename=result_filename)

        return render(request, 'upload_analyze.html')

class API_SUMMARIZE(DocumentService):
    def __init__(self):
        super().__init__('summarize', 'http://agents:5000/summarize')

    def generate_unique_filename(self, original_name):
        base_name = os.path.splitext(original_name)[0]
        timestamp = int(time.time())
        return f"{base_name}_summary_{timestamp}.txt"

    def handle_request(self, request):
        if request.method == 'POST':
            file = request.FILES.get('file')
            num_words = request.POST.get('num_words', '100')
            summary_language = request.POST.get('summary_language', 'en')
            add_prompt = request.POST.get('add_prompt', 'Resume el documento de forma concisa.')

            if not file:
                return render(request, 'upload_summarize.html', {'error_message': "Faltan parámetros: asegúrate de haber cargado un archivo."})

            file_path = self.save_file(file)
            result_filename = self.generate_unique_filename(file.name)
            result_file_path = os.path.join(RESULT_FOLDER, result_filename)

            # Crear el payload directamente en handle_request
            request_data = {
                'files': {'file': open(file_path, 'rb')},
                'file_path': result_file_path,
                'data': {
                    'num_words': num_words,
                    'summary_language': summary_language,
                    'add_prompt': add_prompt
                },
            }

            thread = threading.Thread(target=self.call_api, args=(request_data,))
            thread.start()

            # Programar eliminación del archivo después de 120 segundos
            threading.Thread(target=self.remove_file, args=(result_file_path, DELETE_TIME)).start()

            return redirect('progress_summarize', filename=result_filename)

        return render(request, 'upload_summarize.html')

class API_SUMMARIZE(DocumentService):
    def __init__(self):
        super().__init__('summarize', 'http://agents:5000/summarize')

    def generate_unique_filename(self, original_name):
        base_name = os.path.splitext(original_name)[0]
        timestamp = int(time.time())
        return f"{base_name}_summary_{timestamp}.txt"

    def handle_request(self, request):
        if request.method == 'POST':
            file = request.FILES.get('file')
            num_words = request.POST.get('num_words', '100')
            summary_language = request.POST.get('summary_language', 'en')
            add_prompt = request.POST.get('add_prompt', 'Resume el documento de forma concisa.')

            if not file:
                return render(request, 'upload_summarize.html', {'error_message': "Faltan parámetros: asegúrate de haber cargado un archivo."})

            file_path = self.save_file(file)
            result_filename = self.generate_unique_filename(file.name)
            result_file_path = os.path.join(RESULT_FOLDER, result_filename)

            # Crear el payload directamente en handle_request
            request_data = {
                'files': {'file': open(file_path, 'rb')},
                'file_path': result_file_path,
                'data': {
                    'num_words': num_words,
                    'summary_language': summary_language,
                    'add_prompt': add_prompt
                },
            }

            thread = threading.Thread(target=self.call_api, args=(request_data,))
            thread.start()

            # Programar eliminación del archivo después de 120 segundos
            threading.Thread(target=self.remove_file, args=(result_file_path, DELETE_TIME)).start()

            return redirect('progress_summarize', filename=result_filename)

        return render(request, 'upload_summarize.html')


# Vistas estáticas y de servicios
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

def download(request, filename):
    return DocumentService.download(request, filename)

def check_file_status(request, filename):
    # No es necesario crear una instancia de DocumentService para esta función.
    try:
        result_file_path = os.path.join(RESULT_FOLDER, filename)
        exists = os.path.exists(result_file_path)
        return JsonResponse({'exists': exists})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Vistas de gestión de Usuario

@login_required
def user_dashboard(request):
    # Exemple de dades que es poden passar al context
    context = {
        'user_stats': {
            'translations': 12,  # Nombre de traduccions realitzades
            'edits': 8,          # Nombre d'edicions
            'transcriptions': 5, # Nombre de transcripcions
        },
        'updates': [
            "Nova funcionalitat: Suport per documents en alemany! 📝",
            "Millores de rendiment implementades aquesta setmana.",
            "Recorda revisar la configuració del teu compte per assegurar la privacitat.",
        ]
    }
    return render(request, 'dashboard.html', context)




# Vistas de los servicios


# Vistas Generate

@login_required
def upload_generate(request):
    api_generate = API_GENERATE()
    return api_generate.handle_request(request)

def progress_generate(request, filename):
    return render(request, 'progress_generate.html', {'filename': filename})

def result_generate(request, filename):
    return render(request, 'result_generate.html', {'filename': filename})



# Vistas Translate

@login_required
def upload_translate(request):
    api_translate = API_TRANSLATE()
    return api_translate.handle_request(request)

def progress_translate(request, filename):
    return render(request, 'progress_translate.html', {'filename': filename})

def result_translate(request, filename):
    return render(request, 'result_translate.html', {'filename': filename})


# Vistas Edit

@login_required
def upload_edit(request):
    api_edit = API_EDIT()  # Suponiendo que ya tienes una clase API_EDIT definida
    return api_edit.handle_request(request)

def progress_edit(request, filename):
    return render(request, 'progress_edit.html', {'filename': filename})

def result_edit(request, filename):
    return render(request, 'result_edit.html', {'filename': filename})


# Vistas Transcribe
@login_required
def upload_transcribe(request):
    api_transcribe = API_TRANSCRIBE()  # Suponiendo que ya tienes una clase API_TRANSCRIBE definida
    return api_transcribe.handle_request(request)

def progress_transcribe(request, filename):
    return render(request, 'progress_transcribe.html', {'filename': filename})

# Función para mostrar el resultado de la transcripción
def result_transcribe(request, filename):
    # Suponiendo que RESULT_FOLDER es la carpeta donde se guardan los resultados
    result_file_path = os.path.join(RESULT_FOLDER, filename)

    # Verifica si el archivo existe y lee su contenido
    if os.path.exists(result_file_path):
        with open(result_file_path, 'r', encoding='utf-8') as f:
            transcription = f.read()
    else:
        transcription = "Error: no se encontró el archivo de transcripción."

    # Renderiza la plantilla y pasa la transcripción
    return render(request, 'result_transcribe.html', {'transcription': transcription})


# Vistas Analyze
@login_required
def upload_analyze(request):
    api_analyze = API_ANALYZE()  # Suponiendo que ya tienes una clase API_ANALYZE definida
    return api_analyze.handle_request(request)

def progress_analyze(request, filename):
    return render(request, 'progress_analyze.html', {'filename': filename})

def result_analyze(request, filename):
    result_file_path = os.path.join(RESULT_FOLDER, filename)

    # Verifica si el archivo existe y lee su contenido
    if os.path.exists(result_file_path):
        with open(result_file_path, 'r', encoding='utf-8') as f:
            result_data = json.load(f)  # Cargar los datos del JSON
    else:
        result_data = None

    # Procesar result_data para generar una tabla
    result_table = ""
    if isinstance(result_data, dict) and len(result_data) > 0:  # Asegúrate de que es un diccionario no vacío
        # Obtener las claves del primer archivo para los encabezados
        first_key = next(iter(result_data))  # Obtener la primera clave
        headers = ["Document"] + list(result_data[first_key].keys())  # Agregar encabezado para el nombre del archivo

        result_table += "<table><thead><tr>"
        for header in headers:
            result_table += f"<th>{header}</th>"
        result_table += "</tr></thead><tbody>"

        # Iterar sobre cada archivo y sus datos
        for file_name, file_data in result_data.items():
            result_table += "<tr>"
            result_table += f"<td>{file_name}</td>"  # Añadir el nombre del archivo como primera columna
            for value in file_data.values():
                result_table += f"<td>{value}</td>"
            result_table += "</tr>"
        result_table += "</tbody></table>"
    else:
        # Si no hay datos válidos, puedes manejarlo aquí
        result_table = "<p>No s'han trobat dades per mostrar.</p>"

    # Renderiza la plantilla y pasa los datos del análisis
    return render(request, 'result_analyze.html', {'result_table': result_table})



# Vistas Summarize
@login_required
def upload_summarize(request):
    api_summarize = API_SUMMARIZE()  # Suponiendo que ya tienes una clase API_SUMMARIZE definida
    return api_summarize.handle_request(request)

def progress_summarize(request, filename):
    return render(request, 'progress_summarize.html', {'filename': filename})

# Función para mostrar el resultado del resumen
def result_summarize(request, filename):
    result_file_path = os.path.join(RESULT_FOLDER, filename)

    # Verifica si el archivo existe y lee su contenido
    if os.path.exists(result_file_path):
        with open(result_file_path, 'r', encoding='utf-8') as f:
            summary = f.read()
    else:
        summary = "Error: no se encontró el archivo de resumen."

    # Renderiza la plantilla y pasa el contenido del resumen
    return render(request, 'result_summarize.html', {'summary': summary})


    api_embedding = API_EMBEDDING()
    return api_embedding.handle_request(request)