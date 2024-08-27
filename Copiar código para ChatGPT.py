import os

# Lista de archivos que deseas leer (debes incluir la extensión)
archivos_a_leer = ['app.py', 'templates/upload.html', 'templates/progress.html', 'templates/result.html', 'static/styles.css']

# Recorrer la lista de archivos especificados
for archivo in archivos_a_leer:
    # Ruta completa del archivo
    ruta_completa = os.path.join(archivo)
    # Verificar si el archivo existe
    if os.path.isfile(ruta_completa):
        # Leer y mostrar el contenido del archivo
        with open(ruta_completa, 'r', encoding='utf-8') as f:
            print(f"--- Contenido del archivo: {archivo} ---")
            print(f.read())
            print("\n" + "-"*50 + "\n")
    else:
        print(f"El archivo {archivo} no existe en la ruta especificada.")
