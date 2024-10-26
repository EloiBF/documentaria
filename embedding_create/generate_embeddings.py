import os
import glob
import re
import sqlite3
from sentence_transformers import SentenceTransformer
import numpy as np


# Define la ruta de la base de datos en el volumen compartido
DB_PATH = os.path.join('..', 'shared_DB', 'embeddings.db')  # Ajusta la ruta según la estructura de tu proyecto

# Conexión a SQLite
def get_db_connection(db_file=DB_PATH):
    conn = sqlite3.connect(db_file)
    return conn

# Funciones para leer diferentes tipos de archivos
from process_text_reader import read_document, read_docx, read_html, read_pdf, read_pptx, read_txt

def read_document(file_path):
    _, file_extension = os.path.splitext(file_path)
    
    if file_extension == '.txt':
        return read_txt(file_path), file_extension
    elif file_extension == '.docx':
        return read_docx(file_path), file_extension
    elif file_extension == '.pdf':
        return read_pdf(file_path), file_extension
    elif file_extension == '.pptx':
        return read_pptx(file_path), file_extension
    elif file_extension in ['.html', '.htm']:
        return read_html(file_path), file_extension
    else:
        raise ValueError(f"Tipo de archivo no soportado: {file_extension}")

def split_text(text):
    fragments = re.split(r'(?<=[.!?])\s+|\n+', text)
    return [fragment.strip() for fragment in fragments if fragment.strip()]

def generate_embeddings(file_paths, languages, grupo=None):
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Listas para almacenar los datos
    all_fragments = []
    all_file_paths = []
    all_languages = []
    all_ids = []
    phrase_id_mapping = {}

    for language in languages:
        for file_path in file_paths:
            # Verificar si el file_path comienza con el lenguaje
            if file_path.startswith(language):
                text, _ = read_document(file_path)
                fragments = split_text(text)

                phrase_id_counter = 1  # Reiniciar el contador de phrase_id para cada archivo
                for fragment in fragments:
                    if fragment not in phrase_id_mapping:
                        phrase_id_mapping[fragment] = phrase_id_counter
                        phrase_id_counter += 1

                    all_fragments.append(fragment)
                    all_file_paths.append(file_path)
                    all_languages.append(language)
                    all_ids.append(phrase_id_mapping[fragment])

    embeddings = model.encode(all_fragments)

    # Guardar en SQLite
    conn = get_db_connection()
    cur = conn.cursor()

    #cur.execute(""" DROP TABLE document_embeddings """)

    # Crear tabla si no existe
    cur.execute(""" 
    CREATE TABLE IF NOT EXISTS document_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phrase_id INT NOT NULL,
        text TEXT,
        language TEXT,
        document TEXT,
        id_pos INTEGER,
        grupo INTEGER,  -- Nuevo campo para el grupo de archivos
        embedding BLOB
    )
    """)

    # Insertar embeddings en la base de datos
    for i, (text, language, document, id_pos, embedding) in enumerate(zip(all_fragments, all_languages, all_file_paths, range(1, len(all_fragments) + 1), embeddings)):
        cur.execute(""" 
        INSERT INTO document_embeddings (phrase_id, text, language, document, id_pos, grupo, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?) 
        """, (all_ids[i], text, language, os.path.basename(document), id_pos, grupo, embedding.tobytes()))

    conn.commit()
    cur.close()
    conn.close()

    print("Embeddings guardados en SQLite.")

def crear_db_vectorial(directory, languages, grupo=None):
    """Crea la base de datos vectorial a partir de los documentos en el directorio dado."""
    file_paths = glob.glob(os.path.join(directory, '*'))
    print(f'Archivos encontrados: {file_paths}')
    languages = ['CAS', 'CAT', 'ENG']
    
    generate_embeddings(file_paths, languages, grupo=grupo)
