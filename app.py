from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
import os
import threading
import time
from pathlib import Path
from doc_translator import traducir_doc
from model_translator import translate_text
from model_whisper import transcribe_audio
from doc_editor import editar_doc

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.abspath('docs/uploads')
app.config['RESULT_FOLDER'] = os.path.abspath('docs/downloads')
app.config['ALLOWED_EXTENSIONS'] = {'docx', 'pptx', 'pdf', 'm4a', 'wav', 'mp3'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB


# Páginas estáticas

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')



# Funciones comunes: carga, nombre archivo, check de archivo y descarga

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_result_filename(filename):
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext == '.pdf':
        return f"{os.path.splitext(filename)[0]}.docx"
    elif file_ext in {'.m4a', '.wav', '.mp3'}:
        return f"{os.path.splitext(filename)[0]}.txt"
    else:
        return filename

def handle_file_removal(file_path):
    time.sleep(20)
    if os.path.exists(file_path):
        os.remove(file_path)

def process_file(file, process_func, *args):
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    result_filename = get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
    threading.Thread(target=process_func, args=(file_path, result_file_path, *args)).start()
    return filename, result_filename

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], filename)

    if not os.path.exists(result_file_path):
        print(f"Archivo no encontrado en la ruta: {result_file_path}")
        abort(404, description="Archivo no encontrado")

    print(f"Enviando archivo: {filename} desde {result_file_path}")

    # Crear un fil per a l'eliminació dels fitxers després de la descàrrega
    threading.Thread(target=handle_file_removal, args=(file_path,)).start()
    threading.Thread(target=handle_file_removal, args=(result_file_path,)).start()

    return send_from_directory(app.config['RESULT_FOLDER'], filename, as_attachment=True)


@app.route('/check_status/<filename>')
def check_status(filename):
    result_filename = get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    return jsonify({"status": "completed" if os.path.exists(result_file_path) else "processing"})




# Traducción de documentos
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

        if allowed_file(file.filename):
            filename, result_filename = process_file(file, background_translation, language, origin_language, color_to_exclude, add_prompt)
            return redirect(url_for('check_progress_translate', filename=filename))
    
    return render_template('serv_translate.html', max_file_size=app.config['MAX_CONTENT_LENGTH'])

def background_translation(file_path, result_file_path, language, origin_language, color_to_exclude, add_prompt):
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


@app.route('/progress_translate/<filename>')
def check_progress_translate(filename):
    result_filename = get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return redirect(url_for('result_translate', filename=result_filename))
    
    return render_template('serv_translate_progress.html', filename=filename)

@app.route('/result_translate/<filename>')
def result_translate(filename):
    result_filename = get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return render_template('serv_translate_result.html', filename=result_filename)
    else:
        return redirect(url_for('check_progress_translate', filename=filename))


# Transcripción de audio
@app.route('/transcribe', methods=['GET', 'POST'])
def upload_transcribe():
    if request.method == 'POST':
        file = request.files.get('file')
        audio_language = request.form.get('audio_language')

        if file and allowed_file(file.filename):
            filename, result_filename = process_file(file, background_transcribe, audio_language)
            return redirect(url_for('check_progress_transcribe', filename=filename))
    
    return render_template('serv_transcribe.html')

def background_transcribe(file_path, result_file_path, audio_language):
    try:
        if os.path.exists(result_file_path):
            os.remove(result_file_path)

        transcribed_text = transcribe_audio(file_path, output_path=result_file_path, language=audio_language, model='whisper-large-v3')
        with open(result_file_path, 'w') as file:
            file.write(transcribed_text)
    except Exception as e:
        print(f"Error durante la transcripción del archivo: {str(e)}")

@app.route('/show_progress_transcribe/<filename>')
def check_progress_transcribe(filename):
    result_filename = get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return redirect(url_for('result_transcribe', filename=result_filename))
    
    return render_template('serv_transcribe_progress.html', filename=filename)

@app.route('/result_transcribe/<filename>', methods=['GET'])
def result_transcribe(filename):
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], filename)

    if os.path.exists(result_file_path):
        with open(result_file_path, 'r') as file:
            transcription = file.read()
        return render_template('serv_transcribe_result.html', transcription=transcription)
    else:
        return redirect(url_for('check_progress_transcribe', filename=filename))


# Edición de documentos
@app.route('/edit', methods=['GET', 'POST'])
def upload_edit():
    if request.method == 'POST':
        file = request.files.get('file')
        add_prompt = request.form.get('add_prompt')
        color_to_exclude = request.form.get('color_to_exclude')
        
        if file:
            filename, result_filename = process_file(file, background_edit, add_prompt, color_to_exclude)
            return redirect(url_for('check_progress_edit', filename=filename))
        else:
            return "No file uploaded", 400
    
    return render_template('serv_edit.html')

def background_edit(file_path, result_file_path, add_prompt, color_to_exclude):
    try:
        if os.path.exists(result_file_path):
            os.remove(result_file_path)
        extension = os.path.splitext(file_path)[1].lower()
        editar_doc(file_path, result_file_path, extension, color_to_exclude, add_prompt)
    except Exception as e:
        print(f"Error durante la edición del archivo: {str(e)}")


@app.route('/check_progress_edit/<filename>')
def check_progress_edit(filename):
    result_filename = get_result_filename(filename)
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

    if os.path.exists(result_file_path):
        return redirect(url_for('result_edit', filename=result_filename))
    
    return render_template('serv_edit_progress.html', filename=filename)


@app.route('/result_edit/<filename>')
def result_edit(filename):
    result_file_path = os.path.join(app.config['RESULT_FOLDER'], filename)

    if os.path.exists(result_file_path):
        return render_template('serv_edit_result.html', filename=filename)
    else:
        return redirect(url_for('check_progress_edit', filename=filename))


if __name__ == '__main__':
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['RESULT_FOLDER']).mkdir(parents=True, exist_ok=True)
    app.run(debug=True)
