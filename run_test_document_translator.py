from pathlib import Path
from doc_translator import traducir_doc


# VARIABLES:
nombre_fichero = 'PRUEBA 2.pptx' # Debe incluir la extensión al final (.pptx, .docx o .pdf)
origin_language = "es"
destination_language = "ca"
color_to_exclude = '#FF0000' # poner en formato #F00000

# Rutas de documentos a traducir y devolución
input_path = f'test/in/{nombre_fichero}'
output_path = f'test/out/Traducido_{destination_language}_{nombre_fichero}'
extension = Path(nombre_fichero).suffix


traducir_doc(
            input_path,
            output_path,
            origin_language,
            destination_language,
            extension,
            color_to_exclude
        )