# Usa una imagen base de Python
FROM python:3.9-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo de requisitos al contenedor
COPY requirements.txt ./

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código fuente del servicio al contenedor
COPY . .

# Expone el puerto en el que Django correrá
EXPOSE 8000

# Comando para ejecutar la aplicación utilizando main.py
CMD ["python", "main.py", "runserver", "0.0.0.0:8000"]
