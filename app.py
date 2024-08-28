from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import threading
import time
from doc_translator import traducir_doc

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'docs/uploads'
app.config['RESULT_FOLDER'] = 'docs/translated'
app.config['ALLOWED_EXTENSIONS'] = {'docx', 'pptx', 'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_translation(filename, language, origin_language, color_to_exclude):
    try:
        # Define las rutas de entrada y salida
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        result_filename = f"translated_{filename}"
        result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

        # Verifica si el archivo de salida ya existe y lo elimina si es necesario
        if os.path.exists(result_file_path):
            print(f"Archivo existente encontrado y eliminado: {result_file_path}")
            os.remove(result_file_path)

        # Verifica la existencia del archivo de entrada antes de proceder
        if not os.path.exists(file_path):
            print(f"Archivo de entrada no encontrado: {file_path}")
            return None

        print(f"Iniciando traducción del archivo: {file_path}")
        
        # Llama a la función de traducción
        traducir_doc(
            input_path=file_path,
            output_path=result_file_path,
            origin_language=origin_language,
            destination_language=language,
            extension=os.path.splitext(filename)[1].lower(),
            color_to_exclude=color_to_exclude
        )

        # Verifica si el archivo de resultado fue creado
        if os.path.exists(result_file_path):
            print(f"Traducción exitosa, archivo guardado en: {result_file_path}")
            return result_filename
        else:
            print(f"Traducción fallida, archivo de resultado no encontrado: {result_file_path}")
            return None

    except Exception as e:
        # Captura y muestra detalles de cualquier excepción
        print(f"Error durante la traducción del archivo {filename}: {str(e)}")
        return None


def background_translation(filename, language, origin_language, color_to_exclude):
    translated_filename = process_translation(filename, language, origin_language, color_to_exclude)
    if translated_filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        result_file_path = os.path.join(app.config['RESULT_FOLDER'], translated_filename)
        threading.Thread(target=schedule_file_removal, args=(result_file_path,)).start()
    else:
        print(f"Falló la traducción para {filename}")

def schedule_file_removal(file_path):
    time.sleep(30)
    if os.path.exists(file_path):
        os.remove(file_path)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    max_file_size = app.config['MAX_CONTENT_LENGTH']
    error_message = None
    if request.method == 'POST':
        if 'file' not in request.files or 'language' not in request.form or 'origin_language' not in request.form:
            error_message = "Faltan parámetros"
            return render_template('home.html', max_file_size=max_file_size, error_message=error_message)

        file = request.files.get('file')
        language = request.form.get('language')
        origin_language = request.form.get('origin_language')
        color_to_exclude = request.form.get('color_to_exclude', None)

        if not file or not language or not origin_language:
            error_message = "Faltan parámetros"
            return render_template('home.html', max_file_size=max_file_size, error_message=error_message)

        if file.filename == '':
            error_message = "No se seleccionó ningún archivo"
            return render_template('home.html', max_file_size=max_file_size, error_message=error_message)

        if file and allowed_file(file.filename):
            if file.content_length > max_file_size:
                error_message = "Archivo demasiado grande"
                return render_template('home.html', max_file_size=max_file_size, error_message=error_message)

            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            thread = threading.Thread(target=background_translation, args=(filename, language, origin_language, color_to_exclude))
            thread.start()

            return redirect(url_for('show_progress', filename=filename))
    return render_template('home.html', max_file_size=max_file_size, error_message=error_message)

@app.route('/progress/<filename>')
def show_progress(filename):
    result_filename = f"translated_{filename}"
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return redirect(url_for('result', filename=filename))

    return render_template('progress.html', filename=filename)

@app.route('/download/<filename>')
def download_file(filename):
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], filename)

    if not os.path.exists(result_file_path):
        abort(404, description="Archivo no encontrado")

    # Iniciar un hilo para eliminar el archivo después de 10 segundos
    threading.Thread(target=schedule_file_removal, args=(result_file_path, 10)).start()

    return send_from_directory(app.config['RESULT_FOLDER'], filename, as_attachment=True)

@app.route('/result/<filename>')
def result(filename):
    result_filename = f"translated_{filename}"
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return render_template('result.html', filename=result_filename)
    else:
        return redirect(url_for('show_progress', filename=filename))

@app.route('/check_status/<filename>')
def check_status(filename):
    result_filename = f"translated_{filename}"
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
    if os.path.exists(result_file_path):
        return jsonify({"status": "completed"})
    else:
        return jsonify({"status": "processing"})

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

if __name__ == '__main__':
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['RESULT_FOLDER']).mkdir(parents=True, exist_ok=True)
    app.run(debug=True)
