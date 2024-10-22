import os
from multiprocessing import Pool
from functools import partial
from doc_editor import editar_doc
from doc_extract_info import extract_info_from_doc
from doc_summary import resumir_doc
from doc_translator import traducir_doc
from audio_transcribe import transcribe_audio

def process_file(file_path, function, **kwargs):
    """
    Procesa un archivo individual con la función y parámetros especificados.
    """
    try:
        result = function(input_path=file_path, **kwargs)
        return (file_path, result)
    except Exception as e:
        return (file_path, f"Error: {str(e)}")

def process_files_parallel(file_paths, function, function_kwargs, num_processes=None):
    """
    Procesa múltiples archivos en paralelo usando la función y parámetros especificados.
    """
    with Pool(processes=num_processes) as pool:
        results = pool.map(partial(process_file, function=function, **function_kwargs), file_paths)
    return dict(results)

def main():
    # Ejemplo de uso
    directory = "test/in/"
    file_paths = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    # Parámetros para cada función
    edit_params = {
        "output_path": f"test/out/{nombre_fichero}",
        "extension": ".docx",
        "color_to_exclude": "red",
        "add_prompt": "Editar este documento"
    }

    extract_params = {
        "output_path": "ruta/salida/extraidos/",
        "prompts": ["Extrae información clave"],
        "tipos_respuesta": ["texto"],
        "ejemplos_respuesta": None,
        "max_retries": 10
    }

    summary_params = {
        "num_words": 100,
        "summary_language": "es",
        "add_prompt": "Resume este documento"
    }

    translate_params = {
        "output_path": "ruta/salida/traducidos/",
        "origin_language": "es",
        "destination_language": "en",
        "extension": ".docx",
        "color_to_exclude": "red",
        "add_prompt": "Traduce este documento"
    }

    transcribe_params = {
        "output_path": "ruta/salida/transcripciones/",
        "language": "es",
        "add_prompt": "Transcribe este audio",
        "model": "distil-whisper-large-v3-en",
        "api_key_file": "API_KEY.txt"
    }

    # Procesar documentos
    edited_docs = process_files_parallel(file_paths, editar_doc, edit_params)
    extracted_info = process_files_parallel(file_paths, extract_info_from_doc, extract_params)
    summaries = process_files_parallel(file_paths, resumir_doc, summary_params)
    translated_docs = process_files_parallel(file_paths, traducir_doc, translate_params)

    # Procesar archivos de audio
    audio_files = [f for f in file_paths if f.endswith(('.mp3', '.wav', '.ogg'))]
    transcriptions = process_files_parallel(audio_files, transcribe_audio, transcribe_params)

    # Aquí puedes hacer algo con los resultados, como guardarlos o procesarlos más

if __name__ == "__main__":
    main()