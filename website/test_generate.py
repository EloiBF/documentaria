import requests

# URL del servicio Flask
url = "http://service_generate:5000/generate"

# Datos a enviar
data = {
    "prompt": "Este es un ejemplo de generación de documentos.",
    "file_type": "docx"
}

try:
    # Realizar la solicitud POST
    response = requests.post(url, json=data)

    # Verificar el estado de la respuesta
    if response.status_code == 200:
        print("Solicitud exitosa!")
        # Si la respuesta incluye un archivo, puedes guardarlo
        with open("output.docx", "wb") as f:
            f.write(response.content)
        print("Archivo guardado como output.docx")
    else:
        print(f"Error {response.status_code}: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Error al conectar con la API: {e}")