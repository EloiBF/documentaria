from groq import Groq
import re
from process_text_editor import Modify_Diccionarios, Modify_Bloques,Validar_Bloques, DOCX_process, PPTX_process, Excel_process, PDF_process, TXT_process, HTML_process
import requests


# Funcions específiques de la traducció de documents. Prompting i model IA.

# Crida a la API per embeddings
def obtener_ejemplos_api(query_text, origin_language, target_language, k=1):
    """
    Llama a la API para obtener ejemplos de traducción.
    """
    url = "http://embedding:6000/find-translation-examples"
    data = {
        "query_text": query_text,
        "language": origin_language,
        "target_language": target_language,
        "k": k
    }

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            print(f"API call failed with status code {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error in API request: {e}")
        return []

class Aplicar_Modelo:

    # Función genérica para traducir con IA, con soporte para contexto y ejemplos
    def modelo_traduccion_contexto(
        texto, origin_language, destination_language, add_prompt, file_type,
        model, api_key_file, use_embedding):
        """
        Traduce el texto utilizando el cliente de Groq con el contexto anterior y siguiente.
        """

        try:
            # Inicializa el cliente de Groq
            with open(api_key_file, 'r') as fichero:
                api_key = fichero.read().strip()
            client = Groq(api_key=api_key)

            # Genera el prompt base para la traducción según el tipo de archivo
            if file_type in ['.pptx', '.docx', '.pdf', '.txt', '.html']:
                base_prompt = f"""
                    Translation Instructions:
                    Translate the text in the code given, maintaining exact <ph> and </ph> tags.
                    Do not translate or alter any content within <ph> and </ph> tags. These are placeholders and must remain exactly as they appear in the original text.
                    Preserve all <ph> and </ph> tags in their original positions within the text.
                    Do not add any comments, annotations, or changes outside the required translation.
                    Ensure the translation is grammatically correct and coherent in {destination_language}, with proper usage of punctuation, symbols, and apostrophes.
                    All punctuation, symbols, numbers, line breaks, and white spaces should be preserved exactly as they appear in the original text, except where {destination_language} grammar rules require changes.
                    Translate every word, including those starting with capital letters, unless they are clearly proper nouns that should not be translated.
                    Maintain a similar text length in the translation to match the original as closely as possible.
                    The text is part of a larger document. Use the context provided by the surrounding words to ensure an accurate and natural translation.
                    If you encounter any ambiguities or context-dependent terms, translate them based on the most likely interpretation given the surrounding context.

                    Example:
                    Original in English: "<ph>The cat,</ph><ph> </ph><ph>animal_1</ph> sat on the <ph>object_2</ph>."
                    Translation to Spanish: "<ph>El gato,</ph><ph> </ph><ph>animal_1</ph> se sentó en el <ph>object_2</ph>."
                """
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Construye el prompt completo
            prompt = base_prompt

            # Agrega instrucciones adicionales si se proporcionan
            if add_prompt:
                prompt += f"\n\nAdditional translation instructions: {add_prompt}"

            # Llama a la API de ejemplos de traducción si use_embedding está activado
            if use_embedding == True:
                ejemplos = obtener_ejemplos_api(texto, origin_language, destination_language)
                prompt += f"\n\nTranslation Examples: {ejemplos}\n"


            # Agrega el texto de traducción al prompt
            if origin_language == "auto":
                prompt += f"Translate the code to {destination_language}.\nCode to translate:\n{texto}"
            else:
                prompt += f"Translate the code from {origin_language} to {destination_language}.\nCode to translate:\n{texto}"

            # Llama a la API de Groq para traducir el texto
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model
            )

            traduccion = chat_completion.choices[0].message.content.strip()

            print(prompt)  # Opcional: para depuración

            return traduccion

        except Exception as e:
            raise RuntimeError(f"Error during translation: {e}")

    #  Función genérica para traducir con IA, con soporte para contexto
    def modelo_traduccion_placeholders(texto, texto_traducido, texto_original, origin_language, destination_language, add_prompt, model, api_key_file):
        """
        Revisa el texto traducido utilizando el cliente de Groq comparándolo con el texto original.
        """
        try:
            # Inicializa el cliente de Groq
            with open(api_key_file, 'r') as fichero:
                api_key = fichero.read().strip()
            client = Groq(api_key=api_key)

            # Genera el prompt para la revisión
            base_prompt = f"""
                Translation Instructions:
                The following is a rework of a translation. The original text is in {origin_language} and the translated text is in {destination_language}.
                Compare the translation to the original, and translate using the same words text with placeholders
                - Ensure there are intact <ph> and </ph> tags in their original positions (could be between words or characters).
                - Ensure translation is grammatically correct and coherent in {destination_language}.
                - Use proper vocabulary in {destination_language} ensuring words are correct and usual in this language. 
                - Translation properly reflects the meaning of the original text without adding or omitting content.
                - It matches punctuation, symbols, and special formatting of the original text unless changes are required by {destination_language} grammar.
                - Do not comment or add any extra message.

                Original text without placeholders: {texto_original}
                Translated text with placeholders: {texto_traducido}

                Text to translate with placeholders: {texto}
            """

            if add_prompt:
                base_prompt += f"\n\nAdditional instructions: {add_prompt}"

            # Llama a la API de Groq para revisar el texto traducido
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": base_prompt}],
                model=model
            )

            revision = chat_completion.choices[0].message.content.strip()

            print(base_prompt)  # Para propósitos de depuración, muestra el prompt

            return revision

        except Exception as e:
            raise RuntimeError(f"Error during translation revision: {e}")


    def aplicar_modelo_IA(bloques, origin_language, destination_language, extension, add_prompt, model, api_key_file, numintentos, use_embedding):
        """
        Aplica el modelo de traducción y revisión a los bloques. Verifica los placeholders después de cada paso.
        """
        bloques_traducidos = []

        bloques_contexto = Modify_Bloques.generar_bloques_contexto(bloques)

        # Iterar sobre cada bloque para traducir
        for i, bloque in enumerate(bloques):
            reintentos = 0
            traduccion_valida = False
            bloque_extendido = bloques_contexto[i]
            while reintentos < numintentos:
                try:
                    # Traducimos el bloque actual
                    traduccion = Aplicar_Modelo.modelo_traduccion_contexto(bloque_extendido, origin_language, destination_language, add_prompt, extension, model, api_key_file, use_embedding)
                    revision = Aplicar_Modelo.modelo_traduccion_placeholders(bloque, traduccion, bloque_extendido, origin_language, destination_language, add_prompt, model, api_key_file)

                    # Verificamos que los placeholders se mantengan en la revisión
                    if Validar_Bloques.verificar_placeholders(bloque, revision):
                        print(f'BLOQUE ORIGINAL: {bloque}')
                        print(f'TRADUCCIÓN: {traduccion}')
                        print(f'REVISIÓN: {revision}')

                        # Si pasa la validación, añadimos el bloque revisado
                        bloques_traducidos.append(revision)
                        traduccion_valida = True
                        break  # Salimos del bucle si la revisión es válida
                    else:
                        print(f'[ERROR] Bloque original: {bloque}')
                        print(f'[ERROR] Bloque revisado: {revision}')
                        raise ValueError("Error por revisión no válida")

                except Exception as e:
                    print(f'Error en la traducción/revisión del bloque. {e}. Reintentando...')
                    reintentos += 1

            if not traduccion_valida:
                print(f'No se pudo traducir ni revisar correctamente el bloque después de {numintentos} intentos')
                bloques_traducidos.append(bloque)  # Si no fue posible, se añade el bloque original

        return bloques_traducidos

# Función final que lee el documento y realiza la traducción. Genera el diccionario original, lo ajusta, recibe el traducido, lo ajusta y reemplaza los textos con los valores del traducido final
def traducir_doc(input_path, output_path, origin_language, destination_language, extension, color_to_exclude, add_prompt="", model='llama-3.1-70b-versatile', api_key_file='API_KEY.txt', numintentos = 20, use_embedding=False):
    
    textos_originales = {}
    
    if extension == ".pptx":
        textos_originales = PPTX_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final=None, action="leer")
        print("Diccionario textos_originales")
        print(textos_originales)

    elif extension == ".docx":
        textos_originales = DOCX_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final=None, action="leer")
        print("Diccionario textos_originales")
        print(textos_originales)

    elif extension == ".pdf":
        textos_originales = PDF_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final=None, action="leer")
        print("Diccionario textos_originales")
        print(textos_originales)

    elif extension == ".xlsx":
        textos_originales = Excel_process.leer_doc(input_path, output_path, color_to_exclude,  textos_traducidos_final=None, action="leer")
        print("Diccionario textos_originales")
        print(textos_originales)

    elif extension == ".txt":
        textos_originales = TXT_process.leer_doc(input_path, output_path,  textos_traducidos_final=None, action="leer")
        print("Diccionario textos_originales")
        print(textos_originales)

    elif extension == ".html":
        textos_originales = HTML_process.leer_doc(input_path, output_path, textos_traducidos_final=None, action="leer")
        print("Diccionario textos_originales")
        print(textos_originales)

    # Filtrar entradas que no se enviarán a la IA (espacios o vacías)
    textos_para_traducir = Modify_Diccionarios.filtrar_textos_relevantes(textos_originales)
    print("Diccionario textos_para_traducir")
    print(textos_para_traducir)

    # Generar bloques
    bloques = Modify_Diccionarios.separar_texto_bloques(textos_para_traducir)

    # Traducción de bloques con el modelo de IA
    bloques_traducidos = Aplicar_Modelo.aplicar_modelo_IA(bloques, origin_language, destination_language, extension, add_prompt, model, api_key_file, numintentos, use_embedding)

    # Unir bloques traducidos y generar el diccionario de textos traducidos
    textos_traducidos = Modify_Bloques.join_blocks(bloques_traducidos)

    print("Diccionario textos_traducidos")
    print(textos_traducidos)

    # Ajustar y limpiar el texto traducido
    textos_traducidos_final = Validar_Bloques.eliminar_placeholders(textos_traducidos)
    textos_traducidos_final = Modify_Diccionarios.ajuste_post_traduccion_dict(textos_para_traducir, textos_traducidos_final)
    print("Diccionario textos_traducidos_final + ajuste")
    print(textos_traducidos_final)

    # Reconstruir y reemplazar texto traducido en el documento original
    if extension == ".pptx":
        PPTX_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final, action="reemplazar")

    elif extension == ".docx":
        DOCX_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final, action="reemplazar")

    elif extension == ".pdf":
        PDF_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final, action="reemplazar")

    elif extension == ".xlsx":
        Excel_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final, action="reemplazar")

    elif extension == ".txt":
        TXT_process.leer_doc(input_path, output_path, textos_traducidos_final, action="reemplazar")

    elif extension == ".html":
        HTML_process.leer_doc(input_path, output_path, textos_traducidos_final, action="reemplazar")

    print(f'Se ha dejado el documento traducido en la ruta especificada: {output_path}')
