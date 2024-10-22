import requests

# URL del servicio Flask de análisis de documentos
url = "http://service_analyze:5004/extract-info"  # Cambia el nombre del servicio según corresponda

# Rutas de los archivos a analizar
file_paths = ["documents/test/in/PRUEBA 2.pptx", "documents/test/in/pdf_largo.pdf"]  # Cambia esto según tus archivos de prueba

# Datos de configuración para la extracción de información
data = {
    "prompts": ["¿Cuál es el tema principal del documento? En tres palabras.", "Cual es el año del documento?"],  # Prompts para extraer información
    "tipos_respuesta": ["text", "num"],  # Tipos de respuesta para cada prompt
    "ejemplos_respuesta": ["Felicidad, diversión, jugar", "2020"]  # Ejemplos opcionales
}

# Crear la lista de archivos
files = [('files', (open(file, 'rb'))) for file in file_paths]

try:
    # Realizar la solicitud POST con los archivos y los datos
    response = requests.post(url, data=data, files=files)

    # Verificar el estado de la respuesta
    if response.status_code == 200:
        print("Solicitud exitosa!")
        # Guardar el archivo JSON generado
        with open("analysis_output.json", "wb") as f:
            f.write(response.content)
        print("Análisis guardado como analysis_output.json")
    else:
        print(f"Error {response.status_code}: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Error al conectar con la API: {e}")
