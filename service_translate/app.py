from flask import Flask, request, jsonify, send_file
import os
import tempfile
from doc_translate import traducir_doc

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
