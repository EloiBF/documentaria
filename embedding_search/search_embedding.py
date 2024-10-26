import sqlite3
from sentence_transformers import SentenceTransformer
import numpy as np
import os

# Define la ruta de la base de datos en el volumen compartido
DB_PATH = os.path.join('..', 'shared_DB', 'embeddings.db')  # Ajusta la ruta según la estructura de tu proyecto

# Conexión a SQLite
def get_db_connection(db_file=DB_PATH):
    conn = sqlite3.connect(db_file)
    return conn

def search_embeddings(query, k=5):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Codifica la consulta
    query_embedding = model.encode(query).astype(np.float32)
    
    # Conectar a SQLite
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Obtener todos los embeddings de la base de datos
    cur.execute("SELECT id, text, language, document, id_pos, embedding, phrase_id, grupo FROM document_embeddings")
    rows = cur.fetchall()
    
    # Calcular distancias
    distances = []
    for row in rows:
        embedding = np.frombuffer(row[5], dtype=np.float32)
        distance = np.linalg.norm(query_embedding - embedding)
        distances.append((row, distance))
    
    # Ordenar por distancia
    distances.sort(key=lambda x: x[1])
    
    # Obtener los k resultados más cercanos
    closest_results = distances[:k]
    
    return closest_results

def find_embedding_examples(text, language=None, k=5):
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtener el embedding de la consulta
    query_embedding = SentenceTransformer('all-MiniLM-L6-v2').encode(text).astype(np.float32)

    # Consulta SQL que filtra por idioma solo si `language` está definido
    if language:
        cur.execute("""
            SELECT id, text, language, document, id_pos, embedding, phrase_id, grupo 
            FROM document_embeddings 
            WHERE language = ?
        """, (language,))
    else:
        cur.execute("SELECT id, text, language, document, id_pos, embedding, phrase_id, grupo FROM document_embeddings")

    rows = cur.fetchall()

    # Calcular distancias
    distances = []
    for row in rows:
        embedding = np.frombuffer(row[5], dtype=np.float32)
        distance = np.linalg.norm(query_embedding - embedding)
        distances.append((row, distance))
    
    # Ordenar los resultados por distancia
    distances.sort(key=lambda x: x[1])

    # Obtener los k resultados más cercanos
    closest_results = distances[:k]
    
    return closest_results

def find_translation_examples(embedding_results, target_language, k=5):
    conn = get_db_connection()
    cur = conn.cursor()

    translation_results = []
    
    for row, _ in embedding_results:
        phrase_id = row[6]
        grupo = row[7]  # Obtener el grupo del embedding

        cur.execute(""" 
            SELECT text, language FROM document_embeddings 
            WHERE phrase_id = ? AND language = ? AND grupo = ? 
            LIMIT ?
        """, (phrase_id, target_language, grupo, k))
        
        translations = cur.fetchall()
        translation_results.extend(translations)

    return translation_results

