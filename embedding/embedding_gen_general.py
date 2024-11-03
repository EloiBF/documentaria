import os
import glob
import sqlite3
import numpy as np
from fastembed import TextEmbedding  # Importa la clase correcta para fastembed
from process_text_reader import read_document, read_docx, read_html, read_pdf, read_pptx, read_txt

# Define la ruta de la base de datos en el volumen compartido
DB_PATH = 'embeddings.db'

# Conexión a SQLite
def get_db_connection(db_file=DB_PATH):
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

def split_text_into_chunks(text, chunk_size=500):
    words = text.split()
    chunks = []
    current_chunk = []

    for word in words:
        current_chunk.append(word)
        if len(' '.join(current_chunk)) >= chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = []

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def generate_embeddings(file_paths, chunk_size=500):
    # Instancia el modelo de fastembed
    embedding_model = TextEmbedding()
    print("El modelo BAAI/bge-small-en-v1.5 está listo para usarse.")

    all_chunks = []
    all_file_paths = []
    
    for file_path in file_paths:              
        text, _ = read_document(file_path)
        chunks = split_text_into_chunks(text, chunk_size)

        for chunk in chunks:
            all_chunks.append(chunk)
            all_file_paths.append(file_path)

    # Genera embeddings usando fastembed y convierte el generador en lista
    embeddings_list = list(embedding_model.embed(all_chunks))

    # Guardar en SQLite
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(""" DROP TABLE IF EXISTS document_embedding """)

    cur.execute(""" 
    CREATE TABLE IF NOT EXISTS document_embedding (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        document TEXT,
        embedding BLOB
    )
    """)

    for text, document, embedding in zip(all_chunks, all_file_paths, embeddings_list):
        cur.execute(""" 
        INSERT INTO document_embedding (text, document, embedding)
        VALUES (?, ?, ?) 
        """, (text, os.path.basename(document), np.array(embedding).tobytes()))

    conn.commit()
    cur.close()
    conn.close()

    print("Embeddings guardados en SQLite.")

def crear_db_vectorial(directory, chunk_size=500):
    file_paths = glob.glob(os.path.join(directory, '*'))
    print(f'Archivos encontrados: {file_paths}')
    
    generate_embeddings(file_paths, chunk_size=chunk_size)

# Ejemplo de uso
if __name__ == "__main__":
    directory_path = 'ruta/a/tu/directorio'
    crear_db_vectorial(directory_path, chunk_size=500)
