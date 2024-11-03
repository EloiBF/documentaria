from flask import Flask, request, jsonify, send_file
import os
import tempfile
from doc_translate import traducir_doc
from doc_analyze import extract_info_from_docs
from doc_edit import editar_doc
from doc_generate import generate_and_create_file
from doc_summarize import resumir_doc
from doc_transcribe import transcribe_audio


app = Flask(__name__)

def save_temp_file(file):
    """Guardar el archivo subido en un archivo temporal y devolver su ruta."""
    extension = os.path.splitext(file.filename)[1].lower()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    file.save(temp_file.name)
    return temp_file.name

@app.route('/translate', methods=['POST'])
def translate_file():
    try:
        # Obtener datos del request
        file = request.files['file']
        origin_language = request.form['origin_language']
        destination_language = request.form['destination_language']
        color_to_exclude = request.form.get('color_to_exclude', None)
        add_prompt = request.form.get('add_prompt', '')

        # Verificar que todos los parámetros estén presentes
        if not file or not origin_language or not destination_language:
            return jsonify({'error': 'Missing parameters'}), 400

        # Crear un archivo temporal para guardar el archivo subido
        extension = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_input_file:
            input_path = temp_input_file.name
            file.save(input_path)

        # Crear un archivo temporal para el resultado de la traducción
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_output_file:
            output_path = temp_output_file.name

        # Llamar a la función de traducción
        traducir_doc(
            input_path=input_path,
            output_path=output_path,
            origin_language=origin_language,
            destination_language=destination_language,
            extension=extension,
            color_to_exclude=color_to_exclude,
            add_prompt=add_prompt
        )

        # Devolver el archivo traducido
        return send_file(output_path, as_attachment=True, download_name=os.path.basename(output_path))

    except KeyError as e:
        return jsonify({'error': f'Missing key: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Limpiar archivos temporales
        if 'input_path' in locals() and os.path.exists(input_path):
            os.remove(input_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Obtener los datos del request
        files = request.files.getlist('files')  
        prompts = request.form.getlist('prompts')  
        tipos_respuesta = request.form.getlist('tipos_respuesta')  
        ejemplos_respuesta = request.form.getlist('ejemplos_respuesta')  # Opcional

        # Verificar que todos los parámetros necesarios estén presentes
        if not files or not prompts or not tipos_respuesta:
            return jsonify({'error': 'Missing parameters'}), 400

        # Guardar los archivos subidos en archivos temporales
        input_paths = [save_temp_file(file) for file in files]

        # Crear un archivo temporal para guardar el resultado
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_output_file:
            output_path = temp_output_file.name

        # Llamar a la función para extraer la información de los documentos
        final_results = extract_info_from_docs(
            input_paths=input_paths,
            output_path=output_path,
            prompts=prompts,
            tipos_respuesta=tipos_respuesta,
            ejemplos_respuesta=ejemplos_respuesta or None,
            original_filenames=[file.filename for file in files]
        )

        # Devolver el archivo JSON resultante
        return send_file(output_path, as_attachment=True, download_name=os.path.basename(output_path))

    except KeyError as e:
        return jsonify({'error': f'Missing key: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Limpiar archivos temporales
        for input_path in input_paths:
            if os.path.exists(input_path):
                os.remove(input_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)


@app.route('/edit', methods=['POST'])
def edit_file():
    try:
        # Obtener archivo del request
        file = request.files['file']
        
        # Obtener parámetros individuales del request.form
        color_to_exclude = request.form.get('color_to_exclude', None)
        add_prompt = request.form.get('add_prompt', '')

        # Obtener la extensión del archivo
        extension = os.path.splitext(file.filename)[1].lower()

        # Crear un archivo temporal para guardar el archivo subido
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_input_file:
            input_path = temp_input_file.name
            file.save(input_path)

        # Crear un archivo temporal para el resultado de la edición
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_output_file:
            output_path = temp_output_file.name

        # Llamar a la función editar_doc (procesar el documento)
        editar_doc(
            input_path=input_path,
            output_path=output_path,
            extension=extension,
            color_to_exclude=color_to_exclude,
            add_prompt=add_prompt
        )

        # Devolver el archivo editado al cliente
        return send_file(output_path, as_attachment=True, download_name=os.path.basename(output_path))

    except KeyError as e:
        return jsonify({'error': f'Missing key: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Limpiar archivos temporales
        if 'input_path' in locals() and os.path.exists(input_path):
            os.remove(input_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)


@app.route('/generate', methods=['POST'])
def generate_file():
    try:
        prompt = request.json['prompt']
        file_type = request.json['file_type']
        
        # Crear un archivo temporal para guardar el documento generado
        with tempfile.NamedTemporaryFile(delete=False, suffix='.' + file_type.lower()) as temp_file:
            output = temp_file.name  # Obtener el nombre del archivo temporal

            # Llamar a la función que genera el archivo
            generate_and_create_file(prompt, file_type, output)

        # Devolver el archivo generado
        return send_file(output, as_attachment=True, download_name=os.path.basename(output))
    
    except KeyError as e:
        return jsonify({'error': f'Missing key: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/summarize', methods=['POST'])
def summarize_file():
    try:
        # Obtener los datos del request
        file = request.files['file']  # Archivo a resumir
        num_words = int(request.form['num_words'])  # Número de palabras para el resumen
        summary_language = request.form['summary_language']  # Idioma del resumen
        add_prompt = request.form.get('add_prompt', '')  # Prompt adicional opcional

        # Verificar que todos los parámetros estén presentes
        if not file or not num_words or not summary_language:
            return jsonify({'error': 'Missing parameters'}), 400

        # Crear un archivo temporal para guardar el archivo subido
        extension = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_input_file:
            input_path = temp_input_file.name
            file.save(input_path)

        # Llamar a la función de resumen
        summary = resumir_doc(
            input_path=input_path,
            num_words=num_words,
            summary_language=summary_language,
            add_prompt=add_prompt
        )

        if summary is None:
            return jsonify({'error': 'An error occurred while summarizing the document'}), 500

        # Crear un archivo temporal para guardar el resumen
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_output_file:
            output_path = temp_output_file.name
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(summary)

        # Devolver el archivo TXT con el resumen
        return send_file(output_path, as_attachment=True, download_name='summary.txt')

    except KeyError as e:
        return jsonify({'error': f'Missing key: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Limpiar archivos temporales
        if 'input_path' in locals() and os.path.exists(input_path):
            os.remove(input_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)


@app.route('/transcribe', methods=['POST'])
def transcribe_file():
    try:
        # Obtener los datos del request
        audio_file = request.files['file']
        language = request.form.get('language', 'auto')
        add_prompt = request.form.get('add_prompt', '')
        model = request.form.get('model', 'distil-whisper-large-v3-en')

        # Verificar que todos los parámetros estén presentes
        if not audio_file:
            return jsonify({'error': 'Missing audio file'}), 400

        # Crear un archivo temporal para guardar el archivo de audio subido
        extension = os.path.splitext(audio_file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_audio_file:
            audio_path = temp_audio_file.name
            audio_file.save(audio_path)

        # Crear un archivo temporal para el resultado de la transcripción
        output_path = os.path.splitext(audio_path)[0] + '.txt'

        # Llamar a la función de transcripción
        transcribed_text = transcribe_audio(
            audio_file=audio_path,
            output_path=output_path,
            language=language,
            add_prompt=add_prompt,
            model=model
        )

        # Devolver el archivo transcrito
        return send_file(output_path, as_attachment=True, download_name=os.path.basename(output_path))

    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Limpiar archivos temporales
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port = 5000)
