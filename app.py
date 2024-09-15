from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
import os
import threading
import time
from pathlib import Path
import json
from doc_translator import traducir_doc
from audio_transcribe import transcribe_audio
from doc_editor import editar_doc
from doc_summary import resumir_doc  # Asumimos que tienes una función para resumir documentos
from doc_extract_info import extract_info_from_doc

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.abspath('docs/uploads')
app.config['RESULT_FOLDER'] = os.path.abspath('docs/downloads')
app.config['ALLOWED_EXTENSIONS'] = {'docx', 'pptx', 'pdf','txt','html', 'm4a', 'wav', 'mp3'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

class FileProcessor:
    def __init__(self, process_func):
        self.process_func = process_func

    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    def get_result_filename(self, filename):
        raise NotImplementedError("Subclasses should implement this method")

    def handle_file_removal(self, file_path):
        time.sleep(20)
        if os.path.exists(file_path):
            os.remove(file_path)

    def process_file(self, file, *args):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        result_filename = self.get_result_filename(filename)
        result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        threading.Thread(target=self.process_func, args=(file_path, result_file_path, *args)).start()
        return filename, result_filename

    def download_file(self, filename):
        result_file_path = os.path.join(app.config['RESULT_FOLDER'], filename)

        if not os.path.exists(result_file_path):
            print(f"Archivo no encontrado en la ruta: {result_file_path}")
            abort(404, description="Archivo no encontrado")

        print(f"Enviando archivo: {filename} desde {result_file_path}")

        # Crear un hilo para la eliminación de los archivos después de la descarga
        threading.Thread(target=self.handle_file_removal, args=(os.path.join(app.config['UPLOAD_FOLDER'], self.get_original_filename(filename)),)).start()
        threading.Thread(target=self.handle_file_removal, args=(result_file_path,)).start()

        return send_from_directory(app.config['RESULT_FOLDER'], filename, as_attachment=True)

    def check_status(self, filename):
        result_filename = self.get_result_filename(filename)
        result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

        return jsonify({"status": "completed" if os.path.exists(result_file_path) else "processing"})

    def get_original_filename(self, result_filename):
        return result_filename  # Implementar lógica si se necesita obtener el nombre del archivo original a partir del resultado


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
            # Eliminar el archivo de resultado existente si ya existe
            if os.path.exists(result_file_path):
                os.remove(result_file_path)

            # Llamar a la función de resumen con los parámetros adicionales
            summarized_text = resumir_doc(file_path, num_words=num_words, summary_language=summary_language, add_prompt=add_prompt)
            
            # Verificar que el resultado es una cadena
            if not isinstance(summarized_text, str):
                raise ValueError("El texto resumido no es una cadena")

            # Guardar el texto resumido en el archivo de resultado
            with open(result_file_path, 'w') as file:
                file.write(summarized_text)
                
        except Exception as e:
            print(f"Error durante el resumen del archivo: {str(e)}")


class InformationExtractor(FileProcessor):
    def __init__(self):
        super().__init__(self.background_extract)

    def get_result_filename(self, filename):
        return f"{os.path.splitext(filename)[0]}_extracted.txt"

    def process_file(self, file, prompts, response_types, examples):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        result_filename = self.get_result_filename(filename)
        result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        
        # Guardar archivo subido
        file.save(file_path)

        # Llamar al método que procesará el archivo en segundo plano
        threading.Thread(target=self.background_extract, args=(file_path, result_file_path, prompts, response_types, examples)).start()

        return filename, result_filename

    def background_extract(self, file_path, result_file_path, prompts, response_types, examples):
        try:
            if os.path.exists(result_file_path):
                os.remove(result_file_path)

            # Extraer la información
            extracted_data = extract_info_from_doc(
                file_path,
                prompts, 
                response_types, 
                ejemplos_respuesta=examples
            )
            
            # Guardar los datos extraídos en un archivo JSON
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
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms_and_conditions')
def terms_and_conditions():
    return render_template('terms_and_conditions.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/check_status/<process_type>/<filename>')
def check_status(process_type, filename):
    if process_type == "translate":
        result_filename = translator.get_result_filename(filename)
    elif process_type == "transcribe":
        result_filename = transcriber.get_result_filename(filename)
    elif process_type == "edit":
        result_filename = editor.get_result_filename(filename)
    elif process_type == "summary":
        result_filename = summarizer.get_result_filename(filename)
    elif process_type == "extract":
        result_filename = extractor.get_result_filename(filename)
    else:
        return jsonify({"status": "error", "message": "Invalid process type"}), 400

    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
    if os.path.exists(result_file_path):
        return jsonify({"status": "completed"})
    else:
        return jsonify({"status": "in_progress"})


@app.route('/download/<process_type>/<filename>')
def download_file(process_type, filename):
    if process_type == "translate":
        result_filename = translator.get_result_filename(filename)
    elif process_type == "transcribe":
        result_filename = transcriber.get_result_filename(filename)
    elif process_type == "edit":
        result_filename = editor.get_result_filename(filename)
    elif process_type == "summary":
        result_filename = summarizer.get_result_filename(filename)
    elif process_type == "extract":
        result_filename = extractor.get_result_filename(filename)        
    else:
        abort(400, description="Tipo de proceso inválido")

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if not os.path.exists(result_file_path):
        print(f"Archivo no encontrado en la ruta: {result_file_path}")
        abort(404, description="Archivo no encontrado")

    print(f"Enviando archivo: {result_filename} desde {result_file_path}")

    # Crear un hilo para la eliminación de los archivos después de la descarga
    threading.Thread(target=translator.handle_file_removal, args=(file_path,)).start()
    threading.Thread(target=translator.handle_file_removal, args=(result_file_path,)).start()

    return send_from_directory(app.config['RESULT_FOLDER'], result_filename, as_attachment=True)








# Rutas de traducción
@app.route('/translate', methods=['GET', 'POST'])
def upload_translate():
    if request.method == 'POST':
        file = request.files.get('file')
        language = request.form.get('target_language')
        origin_language = request.form.get('source_language')
        color_to_exclude = request.form.get('color_to_exclude', None)
        add_prompt = request.form.get('add_prompt', '')

        if not file or not language or not origin_language:
            error_message = "Faltan parámetros"
            return render_template('serv_translate.html', max_file_size=app.config['MAX_CONTENT_LENGTH'], error_message=error_message)

        if file.filename == '':
            error_message = "No se seleccionó ningún archivo"
            return render_template('serv_translate.html', max_file_size=app.config['MAX_CONTENT_LENGTH'], error_message=error_message)

        if translator.allowed_file(file.filename):
            filename, result_filename = translator.process_file(file, language, origin_language, color_to_exclude, add_prompt)
            return redirect(url_for('check_progress_translate', filename=result_filename))

    return render_template('serv_translate.html', max_file_size=app.config['MAX_CONTENT_LENGTH'])

@app.route('/progress_translate/<filename>')
def check_progress_translate(filename):
    result_filename = translator.get_result_filename(filename)
    print(f"Checking result file: {result_filename}")
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
    print(f"Full path to result file: {result_file_path}")
    if os.path.exists(result_file_path):
        print("File exists, redirecting to result page.")
        return redirect(url_for('result_translate', filename=result_filename))
    print("File does not exist, staying on progress page.")
    return render_template('serv_translate_progress.html', filename=filename)


@app.route('/result_translate/<filename>')
def result_translate(filename):
    result_filename = translator.get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return render_template('serv_translate_result.html', filename=result_filename)
    else:
        return redirect(url_for('check_progress_translate', filename=filename))


# Rutas de transcripción
@app.route('/transcribe', methods=['GET', 'POST'])
def upload_transcribe():
    if request.method == 'POST':
        file = request.files.get('file')
        audio_language = request.form.get('audio_language')

        if file and transcriber.allowed_file(file.filename):
            filename, result_filename = transcriber.process_file(file, audio_language)
            return redirect(url_for('check_progress_transcribe', filename=result_filename))
    
    return render_template('serv_transcribe.html')

@app.route('/progress_transcribe/<filename>')
def check_progress_transcribe(filename):
    result_filename = transcriber.get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return redirect(url_for('result_transcribe', filename=result_filename))
    
    return render_template('serv_transcribe_progress.html', filename=filename)

@app.route('/result_transcribe/<filename>', methods=['GET'])
def result_transcribe(filename):
    result_filename = transcriber.get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        with open(result_file_path, 'r') as file:
            transcription = file.read()
        return render_template('serv_transcribe_result.html', transcription=transcription)
    else:
        return redirect(url_for('check_progress_transcribe', filename=filename))


# Rutas de edición
@app.route('/edit', methods=['GET', 'POST'])
def upload_edit():
    if request.method == 'POST':
        file = request.files.get('file')
        add_prompt = request.form.get('add_prompt')
        color_to_exclude = request.form.get('color_to_exclude')
        
        if file:
            filename, result_filename = editor.process_file(file, add_prompt, color_to_exclude)
            return redirect(url_for('check_progress_edit', filename=result_filename))
        else:
            return "No file uploaded", 400
    
    return render_template('serv_edit.html')

@app.route('/check_progress_edit/<filename>')
def check_progress_edit(filename):
    result_filename = editor.get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return redirect(url_for('result_edit', filename=result_filename))
    
    return render_template('serv_edit_progress.html', filename=filename)

@app.route('/result_edit/<filename>')
def result_edit(filename):
    result_filename = editor.get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return render_template('serv_edit_result.html', filename=result_filename)
    else:
        return redirect(url_for('check_progress_edit', filename=filename))


# Rutas de resumen
@app.route('/summary', methods=['GET', 'POST'])
def upload_summary():
    if request.method == 'POST':
        file = request.files.get('file')
        num_words = request.form.get('num_words')
        summary_language = request.form.get('summary_language')
        add_prompt = request.form.get('add_prompt', '')

        if file:
            # Procesar el archivo utilizando el resumidor de documentos
            filename, result_filename = summarizer.process_file(file, num_words, summary_language, add_prompt)
            return redirect(url_for('check_progress_summary', filename=result_filename))
    
    return render_template('serv_summary.html')

@app.route('/check_progress_summary/<filename>')
def check_progress_summary(filename):
    result_filename = summarizer.get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return redirect(url_for('result_summary', filename=result_filename))
    
    return render_template('serv_summary_progress.html', filename=filename)

@app.route('/result_summary/<filename>', methods=['GET'])
def result_summary(filename):
    result_filename = summarizer.get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        with open(result_file_path, 'r') as file:
            summary = file.read()
        return render_template('serv_summary_result.html', summary=summary)
    else:
        return redirect(url_for('check_progress_summary', filename=filename))


# Extracció de dades de documents

# Rutas de extracción de información ajustadas
@app.route('/extract', methods=['GET', 'POST'])
def upload_extract():
    if request.method == 'POST':
        file = request.files.get('file')  # Obtener el único archivo subido
        prompts = request.form.getlist('prompts')  # Obtener las preguntas como lista
        response_types = request.form.getlist('response_types')  # Obtener los tipos de respuesta como lista
        examples = request.form.getlist('examples')  # Obtener ejemplos si existen

        if file:
            filename, result_filename = extractor.process_file(file, prompts, response_types, examples)
            return redirect(url_for('check_progress_extract', filename=result_filename))
    
    return render_template('serv_extract.html')


@app.route('/check_progress_extract/<filename>')
def check_progress_extract(filename):
    result_filename = extractor.get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return redirect(url_for('result_extract', filename=result_filename))
    
    return render_template('serv_extract_progress.html', filename=filename)


@app.route('/result_extract/<filename>')
def result_extract(filename):
    result_filename = extractor.get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        with open(result_file_path, 'r') as file:
            extracted_data = json.load(file)

        return render_template('serv_extract_result.html', extracted_data=extracted_data)
    else:
        return redirect(url_for('check_progress_extract', filename=filename))
    

if __name__ == '__main__':
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['RESULT_FOLDER']).mkdir(parents=True, exist_ok=True)
    app.run(debug=True)
