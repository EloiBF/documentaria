import os
import sqlite3
import numpy as np
import re
from fastembed import TextEmbedding  # Importa la clase de fastembed

DB_PATH = 'embeddings.db'  # Ajusta la ruta según la estructura de tu proyecto

# Conexión a SQLite
def get_db_connection(db_file=DB_PATH):
    conn = sqlite3.connect(db_file)
    return conn

# Inicializar el modelo de fastembed
embedding_model = TextEmbedding()
print("El modelo BAAI/bge-small-en-v1.5 está listo para usarse.")

# Función para obtener embeddings de un texto de consulta
def get_query_embedding(query):
    query_embedding = list(embedding_model.embed([query]))[0]
    return np.array(query_embedding, dtype=np.float32)

# Búsqueda de embeddings en la base de datos y devuelve k ejemplos por cada frase
def search_translation_embeddings(query, language=None, k=1):
    query_embedding = get_query_embedding(query)
    
    conn = get_db_connection()
    cur = conn.cursor()

    if language:
        cur.execute(""" 
            SELECT id, text, language, document, id_pos, embedding, phrase_id, grupo 
            FROM translation_embedding 
            WHERE language = ? 
        """, (language,))
    else:
        cur.execute("SELECT id, text, language, document, id_pos, embedding, phrase_id, grupo FROM translation_embedding")

    rows = cur.fetchall()

    distances = []
    for row in rows:
        embedding = np.frombuffer(row[5], dtype=np.float32)
        distance = np.linalg.norm(query_embedding - embedding)
        distances.append((row, distance))
    
    distances.sort(key=lambda x: x[1])
    return distances[:k]

# Búsqueda de embeddings generales
def search_general_embeddings(query, k=10):
    query_embedding = get_query_embedding(query)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(""" 
        SELECT id, text, document, embedding 
        FROM document_embedding 
    """)

    rows = cur.fetchall()

    distances = []
    for row in rows:
        if len(row) < 4:
            print("Fila inesperada:", row)
            continue

        embedding = np.frombuffer(row[3], dtype=np.float32)
        distance = np.linalg.norm(query_embedding - embedding)
        distances.append((row, distance))

    distances.sort(key=lambda x: x[1])
    return distances[:k]

# Función para dividir el texto en frases
def split_text(text):
    fragments = re.split(r'(?<=[.!?])\s+|\n+', text)
    return [fragment.strip() for fragment in fragments if fragment.strip()]

# Función para formatear ejemplos de embeddings generales
def find_general_examples(text, k=4):
    fragments = split_text(text)
    all_distances = []

    for fragment in fragments:
        closest_results = search_general_embeddings(fragment, k)
        all_distances.extend(closest_results)

    all_distances.sort(key=lambda x: x[1])
    closest_k_results = all_distances[:10]

    formatted_output = ""
    for i, (row, distance) in enumerate(closest_k_results, 1):
        example_text = row[1]
        formatted_output += f"Ejemplo {i}: {example_text}\n\n"
    
    return formatted_output

# Función para buscar ejemplos de traducción
def find_translation_examples(query_text, language, target_language, k=5):
    fragments = split_text(query_text)
    all_translation_results = []
    all_distances = []

    for fragment in fragments:
        embedding_results = search_translation_embeddings(fragment, language, k)
        all_distances.extend(embedding_results)

    all_distances.sort(key=lambda x: x[1])
    closest_k_results = all_distances[:10]

    conn = get_db_connection()
    cur = conn.cursor()

    for i, (row, distance) in enumerate(closest_k_results, 1):
        if len(row) < 8:
            print("Fila inesperada en embedding_results:", row)
            continue

        phrase_id = row[6]
        grupo = row[7]

        cur.execute(""" 
            SELECT text FROM translation_embedding 
            WHERE phrase_id = ? AND language = ?
        """, (phrase_id, target_language))
        
        translations = cur.fetchall()

        original_text = row[1]
        translation_results = [f"Ejemplo {i}:\nEjemplo original: {original_text}\n"]

        if translations:
            for translation in translations:
                translated_text = translation[0]
                translation_results.append(f"Ejemplo traducido: {translated_text}\n")
        else:
            translation_results.append("Sin traducción disponible\n")
        
        translation_results.append("\n")
        all_translation_results.extend(translation_results)

    formatted_output = "".join(all_translation_results)
    
    return formatted_output
