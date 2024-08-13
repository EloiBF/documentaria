from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import subprocess
import threading
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'
app.config['ALLOWED_EXTENSIONS'] = {'docx', 'pptx', 'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_translation(filename, language, origin_language, color_to_exclude):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        result_filename = f"translated_{filename}"
        result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        
        # Eliminar el archivo de resultados si ya existe
        if os.path.exists(result_file_path):
            os.remove(result_file_path)
        
        # Ejecuta el script de traducción
        script_name = "translate_docx.py" if filename.endswith('.docx') else "translate_pptx.py"
        command = [
            'python', script_name,
            file_path,
            result_file_path,
            origin_language,
            language,
            color_to_exclude
        ]
        print(f"Ejecutando comando: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True)
        print(f"Salida del script: {result.stdout}")
        print(f"Errores del script: {result.stderr}")
        
        # Verifica si el archivo traducido fue creado
        if os.path.exists(result_file_path):
            print(f"Traducción completada para {filename}")
            return result_filename
        else:
            print(f"El archivo traducido no fue encontrado en {result_file_path}")
            return None
    except Exception as e:
        print(f"Error durante la traducción: {e}")
        return None

def background_translation(filename, language, origin_language, color_to_exclude):
    translated_filename = process_translation(filename, language, origin_language, color_to_exclude)
    if translated_filename:
        # Elimina el archivo subido después de la traducción
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Archivo subido {filename} eliminado.")
       
        # Inicia un hilo para eliminar el archivo después de 30 segundos
        result_file_path = os.path.join(app.config['RESULT_FOLDER'], translated_filename)
        threading.Thread(target=schedule_file_removal, args=(result_file_path,)).start()
    else:
        print(f"Falló la traducción para {filename}")

def schedule_file_removal(file_path):
    time.sleep(30)  # Espera 30 segundos antes de eliminar el archivo
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Archivo {file_path} eliminado después de 30 segundos.")

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files or 'language' not in request.form or 'origin_language' not in request.form or 'color_to_exclude' not in request.form:
            return "Faltan parámetros", 400
        
        file = request.files.get('file')
        language = request.form.get('language')
        origin_language = request.form.get('origin_language')
        color_to_exclude = request.form.get('color_to_exclude')
        
        if not file or not language or not origin_language or not color_to_exclude:
            return "Faltan parámetros", 400

        if file.filename == '':
            return "No se seleccionó ningún archivo", 400
        
        if file and allowed_file(file.filename):
            if file.content_length > app.config['MAX_CONTENT_LENGTH']:
                return "Archivo demasiado grande", 413
            
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Iniciar la traducción en un hilo separado
            thread = threading.Thread(target=background_translation, args=(filename, language, origin_language, color_to_exclude))
            thread.start()
            
            # Redirigir a la página de progreso
            return redirect(url_for('show_progress', filename=filename))
    return render_template('upload.html')

@app.route('/progress/<filename>')
def show_progress(filename):
    # Verificar el estado de la traducción
    result_filename = f"translated_{filename}"
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
    
    if os.path.exists(result_file_path):
        return redirect(url_for('result', filename=filename))
    
    # Opcional: Actualizar la página cada pocos segundos para comprobar el progreso
    return render_template('progress.html', filename=filename)

@app.route('/download/<filename>')
def download_file(filename):
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], filename)
    
    if not os.path.exists(result_file_path):
        abort(404, description="Archivo no encontrado")
    
    print(f"Descargando archivo desde {result_file_path}")  # Debug log
    
    # Enviar el archivo
    return send_from_directory(app.config['RESULT_FOLDER'], filename, as_attachment=True)

@app.route('/result/<filename>')
def result(filename):
    result_filename = f"translated_{filename}"
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
    
    if os.path.exists(result_file_path):
        return render_template('result.html', filename=result_filename)
    else:
        # Redirigir a la página de progreso si el archivo aún no está disponible
        return redirect(url_for('show_progress', filename=filename))

@app.route('/check_status/<filename>')
def check_status(filename):
    result_filename = f"translated_{filename}"
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
    if os.path.exists(result_file_path):
        return jsonify({"status": "completed"})
    else:
        return jsonify({"status": "processing"})

if __name__ == '__main__':
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['RESULT_FOLDER']).mkdir(parents=True, exist_ok=True)
    app.run(debug=True)
