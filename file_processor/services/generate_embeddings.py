import os
import glob
import re
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings



# Aquest script genera una DB Vectorial que serveix per donar exemples de traduccions a la IA en el prompt quan tradueix un document

# Serveix per fer una traducció "contextual". Es generen exemples automàtics de frases semblants a la que ha de traduir i la traducció real --> S'ha de programar a doc_translator.py

# Per alimentar la DB vectorial hem de posar fitxers amb el prefix CAS_ o CAT_ o ENG_ davant, o l'idioma que volguem, i executem aquest py.







# Funciones para leer diferentes tipos de archivos (mantenidas del original)
from file_processor.services.process_text_reader import read_document, read_docx, read_html, read_pdf, read_pptx, read_txt

def read_document(file_path):
    """Lee el contenido del archivo especificado según su tipo y devuelve el texto y la extensión del archivo."""
    _, file_extension = os.path.splitext(file_path)
    
    if file_extension == '.txt':
        return read_txt(file_path), file_extension
    elif file_extension == '.docx':
        return read_docx(file_path), file_extension
    elif file_extension == '.pdf':
        return read_pdf(file_path), file_extension
    elif file_extension == '.pptx':
        return read_pptx(file_path), file_extension
    elif file_extension == '.html' or file_extension == '.htm':
        return read_html(file_path), file_extension
    else:
        raise ValueError(f"Tipo de archivo no soportado: {file_extension}")

def split_text(text):
    """Divide el texto en fragmentos utilizando signos de puntuación y saltos de línea como delimitadores."""
    fragments = re.split(r'(?<=[.!?])\s+|\n+', text)
    return [fragment.strip() for fragment in fragments if fragment.strip()]

def generate_embeddings(file_paths, languages):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="embedding/chroma_db"))
    
    # Verificar si la colección existe y eliminarla si es necesario
    collection_name = "document_embeddings"
    existing_collections = client.list_collections()
    
    for collection in existing_collections:
        if collection.name == collection_name:
            client.delete_collection(collection_name)
            print(f"Se ha eliminado la colección existente: {collection_name}")
            break
    
    # Crear la nueva colección
    collection = client.create_collection(collection_name)
    print(f"Se ha creado una nueva colección: {collection_name}")

    all_fragments = []
    all_file_paths = []
    all_languages = []
    all_ids = []
    all_id_pos = []  # Añadir el campo id_pos

    for file_path in file_paths:
        language = get_language(file_path, languages)
        text, _ = read_document(file_path)
        fragments = split_text(text)

        # Asignar un ID único y un ID de posición (id_pos)
        for idx, fragment in enumerate(fragments):
            all_fragments.append(fragment)
            all_file_paths.append(file_path)
            all_languages.append(language)
            id_pos = idx + 1  # id_pos es la posición del fragmento (1, 2, 3, ...)
            all_id_pos.append(id_pos)
            all_ids.append(f"{os.path.basename(file_path)}_{id_pos}")  # ID único basado en archivo y posición
            print(f"Archivo {file_path}, fragmento {id_pos}: {fragment[:50]}...")

    embeddings = model.encode(all_fragments)

    collection.add(
        embeddings=embeddings.tolist(),
        metadatas=[{
            "text": fragment, 
            "language": language,
            "document": os.path.basename(file_path), 
            "id_pos": id_pos  # Guardamos el id_pos como parte del metadata
        } for fragment, language, file_path, id_pos in zip(all_fragments, all_languages, all_file_paths, all_id_pos)],
        ids=all_ids  # IDs únicos usando archivo y posición
    )

    # Imprime los metadatos para verificar:
    print(f"Fragmentos añadidos con id_pos:")
    for fragment, id_pos, language in zip(all_fragments, all_id_pos, all_languages):
        print(f"Fragmento: {fragment[:20]}... ID Pos: {id_pos} Language: {language}")

    return collection

def get_language(file_path, languages):
    """Determina el idioma del archivo basado en su nombre."""
    for lang in languages:
        if lang in file_path:
            return lang
    return "unknown"

def search_embeddings(collection, query, original_language, target_languages, k=5):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode([query]).tolist()
    
    results = collection.query(query_embeddings=query_embedding, n_results=k)

    print(f"Resultados de la búsqueda en {original_language} (idioma original):\n")

    for i, (metadata, distance) in enumerate(zip(results['metadatas'][0], results['distances'][0])):
        # Mostrar resultado en el idioma original
        print(f"{i+1}.\nEjemplo {original_language}: {metadata['text'][:50]}... (Distancia: {distance})")
        
        id_pos = metadata['id_pos']
        print(f"ID Posición: {id_pos}")
        
        # Buscar traducciones en los otros idiomas
        for target_language in target_languages:
            traduccion = buscar_traduccion_por_id_pos(collection, id_pos, target_language)
            if traduccion:
                print(f"Traducción {target_language}: {traduccion['text'][:50]}...")
            else:
                print(f"Traducción {target_language}: No se encontró.")
        print()

def buscar_traduccion_por_id_pos(collection, id_pos, target_language):
    """Busca un fragmento basado en el id_pos y luego filtra por el idioma especificado."""
    resultados = collection.get(where={"id_pos": id_pos})
    
    # Filtrar manualmente los resultados por el idioma deseado
    for metadata in resultados['metadatas']:
        if metadata['language'] == target_language:
            return metadata
    
    return None  # Si no se encuentra, devolver None

def crear_db_vectorial(directory='embedding/files'):
    """
    Crea una base de datos vectorial a partir de los archivos en el directorio especificado.
    
    Args:
    - directory: Ruta del directorio que contiene los archivos .docx para procesar.
    """
    # Obtener todos los archivos .docx en el directorio especificado
    file_paths = glob.glob(os.path.join(directory, '*.docx'))
    
    # Asignar los idiomas a los archivos
    languages = ['CAS', 'CAT', 'ENG']  # Supongamos que el orden de los archivos es correcto
    
    # Llamar a la función de generación de embeddings
    collection = generate_embeddings(file_paths, languages)
    
    return collection



# Ejemplo de uso
if __name__ == "__main__":
    # Crear la base de datos vectorial
    collection = crear_db_vectorial()

    # Realizar una búsqueda de ejemplo
    query = "Esto es un señor texto"  # Frase de ejemplo en español
    search_embeddings(collection, query, original_language='CAS', target_languages=['CAT', 'ENG'])  