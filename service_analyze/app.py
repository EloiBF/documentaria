from flask import Flask, request, jsonify, send_file
import os
import tempfile
import json
from doc_analyze import extract_info_from_docs

app = Flask(__name__)

@app.route('/extract-info', methods=['POST'])
def extract_info():
    try:
        # Obtener los datos del request
        files = request.files.getlist('files')  # Lista de archivos
        prompts = request.form.getlist('prompts')  # Lista de prompts
        tipos_respuesta = request.form.getlist('tipos_respuesta')  # Lista de tipos de respuesta
        ejemplos_respuesta = request.form.getlist('ejemplos_respuesta')  # Ejemplos de respuesta opcionales (puede ser vacío)

        # Verificar que todos los parámetros necesarios estén presentes
        if not files or not prompts or not tipos_respuesta:
            return jsonify({'error': 'Missing parameters'}), 400

        # Crear archivos temporales para los archivos subidos
        input_paths = []
        for file in files:
            extension = os.path.splitext(file.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_input_file:
                input_path = temp_input_file.name
                file.save(input_path)
                input_paths.append(input_path)

        # Crear un archivo temporal para guardar el resultado
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_output_file:
            output_path = temp_output_file.name

        # Llamar a la función para extraer la información de los documentos
        final_results = extract_info_from_docs(
            input_paths=input_paths,
            output_path=output_path,
            prompts=prompts,
            tipos_respuesta=tipos_respuesta,
            ejemplos_respuesta=ejemplos_respuesta if ejemplos_respuesta else None
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004)
