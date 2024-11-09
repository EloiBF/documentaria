from flask import Flask, request, jsonify
import os
import sqlite3
import numpy as np
import re
from fastembed import TextEmbedding
from embedding_gen_general import crear_db_vectorial as create_db_vectorial_general
from embedding_gen_translation import crear_db_vectorial as create_db_vectorial_translation
from embedding_search import find_general_examples, find_translation_examples 
import tempfile
import shutil

app = Flask(__name__)

@app.route('/create-general-db', methods=['POST'])
def create_general_db():
    try:
        # Obtener el archivo enviado
        file = request.files.get('file')  # Solo un archivo
        if not file:
            return jsonify({'error': 'No file provided'}), 400

        # Crear un directorio temporal para almacenar el archivo
        temp_dir = tempfile.mkdtemp(prefix='general_embedding_')
        temp_file_path = os.path.join(temp_dir, file.filename)
        
        # Guardar el archivo en el directorio temporal
        file.save(temp_file_path)

        # Llamar a la función para crear la base de datos vectorial general
        create_db_vectorial_general(temp_file_path)

        # Limpiar el archivo temporal después de procesarlo
        shutil.rmtree(temp_dir)

        return jsonify({'message': 'General embedding database created successfully'}), 201

    except KeyError as e:
        return jsonify({'error': f'Missing key: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create-translation-db', methods=['POST'])
def create_translation_db():
    try:
        # Obtener el archivo enviado
        file = request.files.get('file')  # Solo un archivo
        if not file:
            return jsonify({'error': 'No file provided'}), 400

        # Obtener los parámetros de lenguaje y grupo
        language = request.form.get('language')
        grupo = request.form.get('grupo')

        # Verificar que todos los parámetros estén presentes
        if not language or not grupo:
            return jsonify({'error': 'Missing required fields (language, grupo)'}), 400

        # Crear un directorio temporal para almacenar el archivo
        temp_dir = tempfile.mkdtemp(prefix='embedding_')
        temp_file_path = os.path.join(temp_dir, file.filename)
        
        # Guardar el archivo en el directorio temporal
        file.save(temp_file_path)

        # Llamar a la función para procesar el archivo y generar los embeddings
        create_db_vectorial_translation(temp_file_path, language=language, grupo=grupo)

        # Limpiar el archivo temporal después de procesarlo
        shutil.rmtree(temp_dir)

        return jsonify({'message': 'Embeddings generated successfully'}), 201

    except KeyError as e:
        return jsonify({'error': f'Missing key: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/find-translation-examples', methods=['POST'])
def find_translation_examples_api():
    try:
        # Obtener los datos de la solicitud
        request_data = request.json
        query_text = request_data.get('query_text')
        language = request_data.get('language')
        target_language = request_data.get('target_language')
        k = request_data.get('k', 1)  # Valor por defecto

        if not query_text or not language or not target_language:
            return jsonify({'error': 'Query text, language, and target language are required'}), 400

        # Llamar a la función para encontrar ejemplos de traducción
        results = find_translation_examples(query_text, language, target_language, k)

        return jsonify({'results': results}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/find-general-examples', methods=['POST'])
def find_general_examples_api():
    try:
        # Obtener los datos de la solicitud
        request_data = request.json
        text = request_data.get('text')
        k = request_data.get('k', 4)  # Puedes establecer un valor por defecto si es necesario

        if not text:
            return jsonify({'error': 'Text is required'}), 400

        # Llamar a la función para encontrar ejemplos generales
        results = find_general_examples(text, k)

        return jsonify({'results': results}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6000)
