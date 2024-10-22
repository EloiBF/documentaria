from doc_generate import generate_and_create_file
from flask import Flask, request, jsonify, send_file
import os
import tempfile

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
