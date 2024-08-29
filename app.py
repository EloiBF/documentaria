from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import threading
import time
from doc_translator import traducir_doc

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.abspath('docs/uploads')
app.config['RESULT_FOLDER'] = os.path.abspath('docs/translated')
app.config['ALLOWED_EXTENSIONS'] = {'docx', 'pptx', 'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_result_filename(filename):
    """
    Esta función toma el nombre del archivo original y retorna el nombre esperado del archivo traducido.
    Si el archivo es un PDF, el archivo resultante será un DOCX, de lo contrario, mantendrá la misma extensión.
    """
    file_ext = os.path.splitext(filename)[1].lower()
    result_filename = f"translated_{os.path.splitext(filename)[0]}.docx" if file_ext == '.pdf' else f"translated_{filename}"
    return result_filename


def process_translation(filename, language, origin_language, color_to_exclude):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        result_filename = get_result_filename(filename)
        result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        
        # Ruta para el archivo temporal si es un PDF
        temp_file_path = None
        if filename.lower().endswith('.pdf'):
            temp_file_path = file_path.rsplit('.', 1)[0] + '.docx'

        if os.path.exists(result_file_path):
            os.remove(result_file_path)

        if not os.path.exists(file_path):
            print(f"Archivo de entrada no encontrado: {file_path}")
            return None, temp_file_path

        traducir_doc(
            input_path=file_path,
            output_path=result_file_path,
            origin_language=origin_language,
            destination_language=language,
            extension=os.path.splitext(filename)[1].lower(),
            color_to_exclude=color_to_exclude
        )

        # Elimina el archivo original después de la traducción
        if os.path.exists(file_path):
            os.remove(file_path)

        return result_filename, temp_file_path

    except Exception as e:
        print(f"Error durante la traducción del archivo {filename}: {str(e)}")

        # Asegura la eliminación del archivo original y temporal si ocurre un error
        if os.path.exists(file_path):
            os.remove(file_path)
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        return None, temp_file_path
    

def background_translation(filename, language, origin_language, color_to_exclude):
    # Procesa la traducción del archivo
    translated_filename, temp_file_path = process_translation(filename, language, origin_language, color_to_exclude)
    # Inicia un hilo para eliminar el archivo traducido y los archivos temporales después de un tiempo
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], translated_filename) if translated_filename else None
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    threading.Thread(target=schedule_file_removal, args=(result_file_path, file_path, temp_file_path)).start()
    if not translated_filename:
        print(f"Falló la traducción para {filename}")


def schedule_file_removal(result_file_path, file_path, temp_file_path):
    # Espera 10 minutos antes de eliminar los archivos
    time.sleep(10)
    # Elimina el archivo traducido si existe
    if result_file_path and os.path.exists(result_file_path):
        os.remove(result_file_path)
    # Elimina el archivo original si existe
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    # Elimina el archivo temporal si existe
    if temp_file_path and os.path.exists(temp_file_path):
        os.remove(temp_file_path)



@app.route('/', methods=['GET', 'POST'])
def upload_file():
    max_file_size = app.config['MAX_CONTENT_LENGTH']
    if request.method == 'POST':
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

            threading.Thread(target=background_translation, args=(filename, language, origin_language, color_to_exclude)).start()
            return redirect(url_for('show_progress', filename=filename))
    
    return render_template('home.html', max_file_size=max_file_size)

@app.route('/progress/<filename>')
def show_progress(filename):
    result_filename = get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return redirect(url_for('result', filename=result_filename))
    
    return render_template('progress.html', filename=filename)


@app.route('/download/<filename>')
def download_file(filename):
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], filename)

    if not os.path.exists(result_file_path):
        print(f"Archivo no encontrado en la ruta: {result_file_path}")
        abort(404, description="Archivo no encontrado")

    print(f"Enviando archivo: {filename} desde {result_file_path}")
    threading.Thread(target=schedule_file_removal, args=(result_file_path,)).start()

    return send_from_directory(app.config['RESULT_FOLDER'], filename, as_attachment=True)


@app.route('/result/<filename>')
def result(filename):
    result_filename = get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return render_template('result.html', filename=result_filename)
    else:
        return redirect(url_for('show_progress', filename=filename))


@app.route('/check_status/<filename>')
def check_status(filename):
    result_filename = get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    return jsonify({"status": "completed" if os.path.exists(result_file_path) else "processing"})

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