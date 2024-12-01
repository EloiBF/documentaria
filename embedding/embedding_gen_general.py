import os
import sqlite3
import numpy as np
from fastembed import TextEmbedding  # Importa la clase de fastembed
from process_text_reader import read_document, read_docx, read_html, read_pdf, read_pptx, read_txt
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

# Carregar les variables del fitxer .env
load_dotenv()

# Ara pots accedir a les teves variables d'entorn
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
EMBEDDING_DB_PATH = os.getenv('EMBEDDING_DB_PATH')

# Conexión a SQLite
def get_db_connection(db_file=EMBEDDING_DB_PATH):
    conn = sqlite3.connect(db_file)
    return conn

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


def split_text(text, chunk_size=1000, chunk_overlap=200):
    """
    Divide el texto en fragmentos utilizando LangChain.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_text(text)
    return chunks

def generate_embeddings(file_path, language=None, grupo=None):
    # Instancia el modelo de fastembed
    embedding_model = TextEmbedding()
    print("El modelo BAAI/bge-small-en-v1.5 está listo para usarse.")

    all_fragments = []
    all_file_paths = []
    all_languages = []
    all_ids = []
    phrase_id_mapping = {}
                
    text, _ = read_document(file_path)
    fragments = split_text(text)

    phrase_id_counter = 1
    for fragment in fragments:
        if fragment not in phrase_id_mapping:
            phrase_id_mapping[fragment] = phrase_id_counter
            phrase_id_counter += 1

        all_fragments.append(fragment)
        all_file_paths.append(file_path)
        all_languages.append(language)
        all_ids.append(phrase_id_mapping[fragment])

    # Genera los embeddings y conviértelos a una lista
    embeddings_list = list(embedding_model.embed(all_fragments))

    # Guardar en SQLite
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Crear la taula amb la nova columna filename si no existeix
    cur.execute(""" 
    CREATE TABLE IF NOT EXISTS document_embedding (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        document TEXT,
        embedding BLOB,
        filename TEXT
    )
    """)

    # Insertar embeddings en la base de datos
    for text, document, embedding in zip(all_fragments, all_file_paths, embeddings_list):
        cur.execute(""" 
        INSERT INTO document_embedding (text, document, embedding, filename)
        VALUES (?, ?, ?, ?) 
        """, (text, os.path.basename(document), np.array(embedding).tobytes(), os.path.basename(file_path)))

    conn.commit()
    cur.close()
    conn.close()

    print(f"Embeddings guardados en SQLite para el archivo: {file_path}")


# Ahora, en vez de recibir una lista de archivos, procesamos un solo archivo:
def crear_db_vectorial(file_path):
    """Crea la base de datos vectorial a partir de un único archivo."""
    print(f"Procesando el archivo: {file_path}")
    generate_embeddings(file_path)

# Ejemplo de uso
if __name__ == "__main__":
    file_path = 'ruta/a/tu/archivo'
    crear_db_vectorial(file_path)
