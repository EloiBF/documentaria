from flask import Flask, request, jsonify
import os
import sqlite3
import numpy as np
import re
from fastembed import TextEmbedding
from embedding_gen_general import crear_db_vectorial as create_db_vectorial_general
from embedding_gen_translation import crear_db_vectorial as create_db_vectorial_translation
from embedding_search import find_general_examples, find_translation_examples 


app = Flask(__name__)

@app.route('/create-general-db', methods=['POST'])
def create_general_db():
    try:
        # Obtener el JSON completo de la solicitud
        request_data = request.json
        print(f"Request JSON: {request_data}")  # Imprime el JSON completo

        # Obtener el directorio de la solicitud
        directory = request_data.get('directory')

        # Verificar que el directorio está presente
        if not directory:
            return jsonify({'error': 'Directory is required'}), 400

        print(f"Directory: {directory}")  # Agrega esta línea para depuración

        # Llamar a la función para crear la base de datos vectorial general
        create_db_vectorial_general(directory)  # Cambia a crear_db_vectorial si eso es lo que quieres

        return jsonify({'message': 'General embedding database created successfully'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/create-translation-db', methods=['POST'])
def create_translation_db():
    try:
        # Obtener el JSON completo de la solicitud
        request_data = request.json
        print(f"Request JSON: {request_data}")  # Imprime el JSON completo

        # Obtener el directorio de la solicitud
        directory = request_data.get('directory')      

        # Verificar que el directorio está presente
        if not directory:
            return jsonify({'error': 'Directory is required'}), 400

        print(f"Directory: {directory}")  # Agrega esta línea para depuración

        # Llamar a la función para crear la base de datos vectorial general
        create_db_vectorial_translation(directory)  # Cambia a crear_db_vectorial si eso es lo que quieres

        return jsonify({'message': 'General embedding database created successfully'}), 201

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
        k = request_data.get('k', 5)  # Valor por defecto

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
