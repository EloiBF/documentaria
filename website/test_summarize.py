import requests

# URL del servicio Flask de resumen
url = "http://service_summarize:5005/summarize"  # Cambia el nombre del servicio según corresponda

# Ruta del archivo a resumir
file_path = "documents/test/in/song.txt"  # Cambia esto según tu archivo de prueba

# Datos de configuración del resumen
data = {
    "num_words": "100",  # Número de palabras para el resumen
    "summary_language": "en",  # Idioma del resumen
    "add_prompt": "Resume el documento de forma concisa."  # Instrucción adicional para el modelo de resumen
}

try:
    # Realizar la solicitud POST con el archivo y los datos
    with open(file_path, 'rb') as f:
        files = {'file': f}  # El archivo se envía con la clave 'file'
        response = requests.post(url, data=data, files=files)

    # Verificar el estado de la respuesta
    if response.status_code == 200:
        print("Solicitud exitosa!")
        # Guardar el resumen generado
        with open("summary_output.txt", "wb") as f:
            f.write(response.content)
        print("Resumen guardado como summary_output.txt")
    else:
        print(f"Error {response.status_code}: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Error al conectar con la API: {e}")
