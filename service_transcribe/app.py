from flask import Flask, request, jsonify, send_file
import os
import tempfile
from doc_transcribe import transcribe_audio

app = Flask(__name__)

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
    app.run(host='0.0.0.0', port=5003)