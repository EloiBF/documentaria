from flask import Flask, request, jsonify, send_file
import os
import tempfile
from doc_summarize import resumir_doc

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)