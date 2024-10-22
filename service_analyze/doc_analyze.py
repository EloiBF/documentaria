import re
import os
from dateutil import parser
from groq import Groq
import json
from process_text_reader import read_document, split_text

# Funcions específiques per extreure dades en format JSON d'un arxiu a base de prompts i check de la resposta.

tipos_respuesta = ["SI/NO","text","num","date"]

def model_exctact_info(texto, prompt, respuesta_tipo, ejemplo_respuesta=None, file_type=None, model='llama-3.2-90b-vision-preview', api_key_file='API_KEY.txt'):
    try:
        # Inicializa el cliente de Groq
        with open(api_key_file, 'r') as fichero:
            api_key = fichero.read().strip()
        client = Groq(api_key=api_key)

        # Define el prompt base según el tipo de archivo y parámetros proporcionados
        ejemplo_texto = f"Examples of responses include: {ejemplo_respuesta}" if ejemplo_respuesta else ""
        
        if file_type in ['.pptx', '.docx', '.pdf', '.txt', '.html', None]:
            prompt_completo = f"""
            You are a data extraction assistant. Follow these rules:
            - Your task is to extract specific information from the text based on the user's instructions.
            - The type of response expected is: {respuesta_tipo}. {ejemplo_texto}
            - Provide only the extracted information as per the instructions. Do not add any extra comments or information.
            - Ensure that the response matches the expected format and content type.
            
            Prompt for extraction:
            {prompt}
            Text to analyze:
            {texto}
            """
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Llama a la API de Groq para extraer la información
        chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt_completo,
                    }
                ],
                model=model
            )

        respuesta = chat_completion.choices[0].message.content.strip()

    except Exception as e:
        raise RuntimeError(f"Error during information extraction: {e}")
    
    return respuesta

def validar_respuesta(respuesta, tipo):
    """
    Valida la respuesta según el tipo de respuesta esperado.
    """
    if respuesta is None:
        print(f"Respuesta inválida: N/D (Ninguna respuesta proporcionada)")
        return False
    
    respuesta = respuesta.strip().lower()  # Normalizar respuesta
    
    if tipo == 'SI/NO':
        # Aceptar variaciones de sí/no en español e inglés
        if not re.match(r'^(sí?|si?|no?|y(es)?|n(o)?)$', respuesta, re.IGNORECASE):
            print(f"Respuesta inválida: {respuesta} (debe ser 'sí', si , 'no', 'yes', o 'no')")
            return False
        return True
    
    elif tipo == 'num':
        # Eliminar cualquier carácter no numérico (excepto dígitos)
        respuesta_sin_simbolos = re.sub(r'\D', '', respuesta)
        if not respuesta_sin_simbolos.isdigit():
            print(f"Respuesta inválida: {respuesta} (debe ser un número)")
            return False
        return True
    
    elif tipo == 'date':
        try:
            # Intentar parsear la fecha
            parser.parse(respuesta, fuzzy=True)
            return True
        except ValueError:
            print(f"Respuesta inválida: {respuesta} (no es una fecha válida)")
            return False
    
    elif tipo == 'text':
        if not (isinstance(respuesta, str) and len(respuesta) > 0):
            print(f"Respuesta inválida: {respuesta} (debe ser un texto libre no vacío)")
            return False
        return True
    
    else:
        print(f"Tipo de respuesta desconocido: {tipo}. Debe ser: text, num, SI/NO, o date")
        return False

def extract_with_retry(texto, prompt, respuesta_tipo, ejemplo_respuesta=None, file_type=None, model='llama-3.2-90b-vision-preview', api_key_file='API_KEY.txt', max_retries=3):
    """
    Intenta extraer información del texto con reintentos en caso de fallo.
    """
    for intento in range(max_retries):
        try:
            respuesta = model_exctact_info(
                texto=texto,
                prompt=prompt,
                respuesta_tipo=respuesta_tipo,
                ejemplo_respuesta=ejemplo_respuesta,
                file_type=file_type,
                model=model,
                api_key_file=api_key_file
            )
            return respuesta
        except Exception as e:
            print(f"Intento {intento + 1} de {max_retries} fallido: {e}")
            if intento == max_retries - 1:
                raise  # Re-lanzar la excepción si se han agotado los reintentos

def reflexionar_respuestas(respuestas, prompt, tipo_respuesta):
    """
    Usa el modelo para reflexionar sobre todas las respuestas obtenidas y determinar la más adecuada.
    Incluye el tipo de respuesta en el prompt para que el modelo considere el formato adecuado.
    """
    # Usamos un prompt para pedir al modelo que reflexione sobre las respuestas obtenidas

    prompt_reflexion = f"""
    A continuación, se te proporcionan varias respuestas obtenidas para la pregunta '{prompt}':
    
    {respuestas}
    
    Considera que el tipo de respuesta esperado es: {tipo_respuesta}.
    Reflexiona sobre estas respuestas y genera una única respuesta final basada en el consenso o en la información más relevante.
    El resultado final debe dar respuesta a la pregunta y encajar en el tipo de datos esperado.
    """
    
    # Enviar el prompt al modelo para que genere la respuesta final consolidada
    respuesta_consolidada = model_exctact_info(
        texto="",
        prompt=prompt_reflexion,
        respuesta_tipo=tipo_respuesta,
        model='llama-3.2-90b-vision-preview',  # Ajusta según el modelo que estás utilizando
        api_key_file='API_KEY.txt'
    )
    return respuesta_consolidada.strip()

import json

def extract_info_from_docs(input_paths, output_path, prompts, tipos_respuesta, ejemplos_respuesta=None, max_retries=10):
    """Función principal para extraer información de múltiples documentos usando múltiples prompts y tipos de respuesta."""
    final_results = {}

    for input_path in input_paths:
        try:
            # Obtener solo el nombre del archivo sin la ruta
            file_name = os.path.basename(input_path)
            
            # Leer el documento y obtener el tipo de archivo
            text, file_type = read_document(input_path)
            
            # Dividir el texto en bloques si es necesario
            blocks = split_text(text)
            
            # Diccionario para almacenar respuestas por cada pregunta
            respuestas_por_prompt = {prompt: [] for prompt in prompts}
            
            # Iterar por cada bloque y extraer información
            for block in blocks:
                print(f"Procesando bloque de texto de {file_name}...")
                
                for prompt, tipo in zip(prompts, tipos_respuesta or []):
                    # Llamada a la nueva función con reintentos
                    extracted_info = extract_with_retry(
                        texto=block,
                        prompt=prompt,
                        respuesta_tipo=tipo,
                        ejemplo_respuesta=ejemplos_respuesta,
                        file_type=file_type,
                        max_retries=max_retries
                    )
                    
                    # Guardar la respuesta parcial en el diccionario
                    respuestas_por_prompt[prompt].append(extracted_info)

            # Reflexionar sobre las respuestas y obtener una respuesta final por pregunta
            for prompt, tipo in zip(prompts, tipos_respuesta):
                respuestas = respuestas_por_prompt[prompt]
                intentos = 0
                
                while True:
                    # Reflexionar sobre las respuestas y generar una respuesta consolidada
                    respuesta_final = reflexionar_respuestas(respuestas, prompt, tipo)
                    
                    if validar_respuesta(respuesta_final, tipo):
                        # Agregar la respuesta final al diccionario usando solo el nombre del archivo
                        if file_name not in final_results:
                            final_results[file_name] = {}
                        final_results[file_name][prompt] = respuesta_final  # Guardar como cadena
                        break  # Salir del bucle si la validación es correcta
                    else:
                        print(f"Verificación fallida para el prompt: {prompt}. Reiniciando el procesamiento...")
                        intentos += 1
                        
                        # Reiniciar el procesamiento si la validación falla
                        respuestas_por_prompt[prompt] = []  # Limpiar respuestas para esa pregunta
                        
                        # Procesar nuevamente todos los bloques para esa pregunta
                        for block in blocks:
                            extracted_info = extract_with_retry(
                                texto=block,
                                prompt=prompt,
                                respuesta_tipo=tipo,
                                ejemplo_respuesta=ejemplos_respuesta,
                                file_type=file_type,
                                max_retries=max_retries
                            )
                            respuestas_por_prompt[prompt].append(extracted_info)
                        
                        # Si se alcanzan los reintentos, asignar 'N/D'
                        if intentos >= max_retries:
                            final_results[file_name][prompt] = 'N/D'  # Guardar 'N/D' como cadena
                            break
            
            print(final_results)

        except Exception as e:
            print(f"Ocurrió un error procesando el archivo {input_path}: {e}")
    
    # Guardar el resultado en el archivo JSON especificado por output_path
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)
    
    print(f"Resultados guardados en {output_path}")
    
    return final_results
