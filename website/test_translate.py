import requests

# URL del servicio Flask de traducción
url = "http://service_translate:5001/translate"

# Ruta del archivo a traducir
file_path = "documents/test/in/song.txt"

# Datos de configuración de la traducción
data = {
    "origin_language": "es",  # Idioma de origen, por ejemplo, español
    "destination_language": "en",  # Idioma de destino, por ejemplo, inglés
    "color_to_exclude": "#FFFFFF",  # Ejemplo de color a excluir (puedes ajustar según tu necesidad)
    "add_prompt": "Por favor, traduce el documento manteniendo el contexto."  # Instrucción adicional para el modelo de traducción
}

try:
    # Realizar la solicitud POST con el archivo y los datos
    with open(file_path, 'rb') as f:
        files = {'file': f}  # El archivo se envía con la clave 'file'
        response = requests.post(url, data=data, files=files)

    # Verificar el estado de la respuesta
    if response.status_code == 200:
        print("Solicitud exitosa!")
        # Guardar el archivo traducido
        with open("output_translated.txt", "wb") as f:
            f.write(response.content)
        print("Archivo traducido guardado como output_translated.txt")
    else:
        print(f"Error {response.status_code}: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Error al conectar con la API: {e}")
