import requests

# URL del servicio Flask de edición
url = "http://service_edit:5002/edit"  # Cambia el nombre del servicio según corresponda

# Ruta del archivo a editar
file_path = "documents/test/in/song.txt"  # Cambia esto según tu archivo de prueba

# Datos de configuración de la edición
data = {
    "color_to_exclude": "#FFFFFF",  # Ejemplo de color a excluir (puedes ajustar según tu necesidad)
    "add_prompt": "Por favor, edita el documento manteniendo el contexto."  # Instrucción adicional para el modelo de edición
}

try:
    # Realizar la solicitud POST con el archivo y los datos
    with open(file_path, 'rb') as f:
        files = {'file': f}  # El archivo se envía con la clave 'file'
        response = requests.post(url, data=data, files=files)

    # Verificar el estado de la respuesta
    if response.status_code == 200:
        print("Solicitud exitosa!")
        # Guardar el archivo editado
        with open("output_edited.txt", "wb") as f:
            f.write(response.content)
        print("Archivo editado guardado como output_edited.txt")
    else:
        print(f"Error {response.status_code}: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Error al conectar con la API: {e}")
