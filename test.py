# Prueba con varios archivos

from doc_extract_info import extract_info_from_multiple_docs

file_paths = [
    'test/in/pdf_largo.pdf',
    'test/in/TEST.docx',
    'test/in/PRUEBA 2.pptx'
]

prompts = ['El documento está en español?', '¿De qué año es el estudio?', 'Explicame en 5 palabras de que va el documento']
tipos_respuesta = ['SI/NO', 'numérica','texto libre']
ejemplos_respuesta = ['SI', '2025','Estudio sobre las ranas del lago']  # Esto es opcional

resultados = extract_info_from_multiple_docs(file_paths, prompts, tipos_respuesta, ejemplos_respuesta)

print(resultados)