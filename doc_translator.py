from groq import Groq
import re

# Cargamos las funciones de procesado de documento, que se usan para editar o traducir
from process_text_editor import filtrar_textos_relevantes
from process_text_editor import separar_texto_bloques
from process_text_editor import verificar_codigos
from process_text_editor import join_blocks
from process_text_editor import codigos_por_espacios
from process_text_editor import ajuste_post_traduccion
from process_text_editor import ajuste_pre_traduccion
from process_text_editor import procesar_documento
from process_text_editor import incluir_placehold_inicial_final
from process_text_editor import seleccionar_texto_placeholder
from process_text_editor import eliminar_codigos
from process_text_editor import unir_textos_fragmentados
from process_text_editor import separar_palabras_fragmentadas



# Obtenir les paraules abans i despres de cada bloc perquè la traducció no quedi tallada
def obtenir_context(bloques, num_caracters=50):
    """
    Retorna per a cada bloc els últims caràcters del bloc anterior i els primers del bloc següent, sense tallar paraules.

    :param bloques: Llista de blocs de text.
    :param num_caracters: Nombre de caràcters a obtenir del final i principi de cada bloc.
    :return: Llista de tuples (context_anterior, context_seguent) per a cada bloc.
    """
    context = []

    for i, bloque in enumerate(bloques):
        # Obtenim el final del bloc anterior
        if i > 0:
            anterior = bloques[i-1]
            anterior = eliminar_codigos(anterior)
            final_anterior = anterior[-num_caracters:]
            final_anterior = re.sub(r'\s\S*$', '', final_anterior)  # Eliminem paraules tallades
        else:
            final_anterior = ''  # No hi ha bloc anterior pel primer bloc

        # Obtenim el principi del bloc següent
        if i < len(bloques) - 1:
            seguent = bloques[i+1]
            seguent = eliminar_codigos(seguent)
            principi_seguent = seguent[:num_caracters]
            principi_seguent = re.sub(r'\s\S*$', '', principi_seguent)  # Eliminem paraules tallades
        else:
            principi_seguent = ''  # No hi ha bloc següent per l'últim bloc

        context.append((final_anterior, principi_seguent))

    return context

# Funció genèrica per traduir amb la IA, li passes un text i retorna la traducció. MODEL I PROMPT
# Función genérica para traducir con IA, con soporte para contexto
def modelo_traduccion_sin_placeholders(texto, origin_language, destination_language, add_prompt, file_type, context_anterior="", context_seguent="", model='llama-3.1-70b-versatile', api_key_file='API_KEY.txt'):
    """
    Traduce el texto utilizando el cliente de Groq con el contexto anterior y siguiente.

    """
    try:
        # Inicializa el cliente de Groq
        with open(api_key_file, 'r') as fichero:
            api_key = fichero.read().strip()
        client = Groq(api_key=api_key)

        # Genera el texto sin placeholders
        texto = codigos_por_espacios(texto)

        # Genera el prompt base para la traducción según el tipo de archivo
        if file_type == None:
            base_prompt = f"""
            Translation Instructions:
            - Do not add any comments, annotations, or changes outside the translation.
            - Preserve all punctuation, symbols, numbers, line breaks, and white spaces exactly as they appear in the original text.            
            - Ensure the translation is grammatically correct and coherent in {destination_language}, including proper usage of punctuation, symbols, and apostrophes.
            - Translate every word, including those starting with capital letters, unless they are clearly proper nouns that should not be translated.
            - Aim to maintain a similar text length in the translation to match the original as closely as possible.
            - The text is part of a larger document. Use the context provided by the surrounding words to ensure an accurate and natural translation.

            Text to translate:
            """
        elif file_type in ['.pptx', '.docx', '.pdf', '.txt', '.html']:
            base_prompt = f"""
            Translation Instructions:
            - Do not add any comments, annotations, or changes outside the translation.
            - Ensure the translation is grammatically correct and coherent in {destination_language}, including proper usage of punctuation, symbols, and apostrophes.
            - Preserve all punctuation, symbols, numbers, line breaks, and white spaces exactly as they appear in the original text.
            - Translate every word, including those starting with capital letters, unless they are clearly proper nouns that should not be translated.
            - Aim to maintain a similar text length in the translation to match the original as closely as possible.
            - The text is part of a larger document. Use the context provided by the surrounding words to ensure an accurate and natural translation.
            """
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Construye el prompt completo
        prompt = base_prompt

        if context_anterior:
            prompt += f"Words before the text (use as context):\n{context_anterior}\n"

        if origin_language == "auto":
            prompt += f"Translate the text to {destination_language}.\nText to translate:\n{texto}"
        else:
            prompt += f"Translate the text from {origin_language} to {destination_language}.\nText to translate:\n{texto}"

        if context_seguent:
            prompt += f"\nWords after the text (use as context):\n{context_seguent}"

        if add_prompt:
            prompt += f"\n\nAdditional translation instructions: {add_prompt}"

        # Llama a la API de Groq para traducir el texto
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model
        )

        traduccion = chat_completion.choices[0].message.content.strip()
        #print(prompt)

        return traduccion

    except Exception as e:
        raise RuntimeError(f"Error during translation: {e}")

# Possibilitat d'aplicar una altra iteració del model, o d'un model especialitzat per corregir la traducció

# Funció perquè el model Revisi la traducció. Jo faria servir models específics segons els llenguatges d'entrada i sortida.
def modelo_traduccion_con_placeholders(original_text, translated_text, origin_language, destination_language, add_prompt, file_type, model='llama-3.1-70b-versatile', api_key_file='API_KEY.txt'):
    try:
        # Inicializa el cliente de Groq
        with open(api_key_file, 'r') as fichero:
            api_key = fichero.read().strip()
        client = Groq(api_key=api_key)

        # Genera el prompt base para la revisión de la traducción con énfasis en los puntos de corte
        base_prompt = f"""
        Follow these rules:
        - Translate text with placeholders
        - Keep the placeholders (e.g., _CDTR_XX) intact, do not alter it even if there are other instructions.
        - Maintain punctuation and spaces intact.
        - If there are errors in translation, correct it in the placeholder version.
        - Ensure verb tenses are correct given the original text and sentence context.
        - Ensure proper grammar, syntax, coherence and punctuation in {destination_language}. Use same vocabulary style as original text.
        - Do not introduce any new information or alter the original meaning.
        - Only return the corrected translation without additional feedback or comments.

        For your context, translated text with placeholders is:
        {translated_text}

        Text to translate keeping exact placeholders:
        {original_text}
        """

        # Instrucciones adicionales, si son necesarias
        if add_prompt:
            base_prompt += f"\nAdditional review instructions: {add_prompt}"

        # Llama a la API de Groq para revisar el texto
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": base_prompt,
                }
            ],
            model=model
        )

        revisio = chat_completion.choices[0].message.content.strip()

        return revisio

    except Exception as e:
        raise RuntimeError(f"Error during revision: {e}")

def aplicacion_modelo_bloques(bloques, origin_language, destination_language, extension, add_prompt="", numintentos=10):
    bloques_traducidos = []
    ultimas_palabras_traducidas = ""  # Almacena las últimas palabras traducidas del bloque anterior

    # Iterar sobre cada bloque para traducir
    for i, bloque in enumerate(bloques):
        reintentos = 0
        context_anterior = ultimas_palabras_traducidas  # El contexto anterior ahora es la última traducción (ya traducido)
        context_seguent = ""

        if i < len(bloques) - 1:
            # Si no es el último bloque, obtenemos el contexto del siguiente bloque
            context_seguent = bloques[i+1][:50]  # Solo obtenemos las primeras palabras del siguiente bloque

        while reintentos < numintentos:
            try:
                # Traducimos el bloque actual junto con el contexto anterior traducido
                traduccion = modelo_traduccion_sin_placeholders(bloque, origin_language, destination_language, add_prompt, extension, context_anterior=context_anterior, context_seguent=context_seguent)
                print(f'Bloque original: {bloque}')
                print(f'Bloque traducido sin: {traduccion}')

                # Podemos pasarle otro prompt de revisión del lenguaje, mejor con un modelo específico... ver como hacerlo
                traduccion = modelo_traduccion_con_placeholders(bloque, traduccion, origin_language, destination_language, add_prompt, extension)

                # Verificamos que los códigos se hayan preservado en la traducción
                if verificar_codigos(bloque, traduccion):
                    print(f'Bloque traducido con placeholders: {traduccion}')
                    
                    # Si pasa la validación, pillamos el texto entre placeholder de inicio y fin
                    traduccion = seleccionar_texto_placeholder(traduccion)

                    bloques_traducidos.append(traduccion)

                    # Guardamos las últimas palabras traducidas para usarlas en el siguiente bloque
                    ultimas_palabras_traducidas = " ".join(traduccion.split()[-5:])  # Últimas 5 palabras del bloque actual traducido
                    break  # Salimos del bucle si la traducción es válida
                else:
                    print(f'[ERROR] Bloque original: {bloque}')
                    print(f'[ERROR] Bloque traducido: {traduccion}')
                    raise ValueError("Error por traducción no válida")

            except Exception as e:
                print(f'Error en la traducción del bloque. {e}. Reintentando...')
                reintentos += 1

        else:
            print(f'No se pudo traducir correctamente el bloque después de {numintentos} intentos')
            bloques_traducidos.append(bloque)
    
    return bloques_traducidos

def traducir_doc(input_path, output_path, origin_language, destination_language, extension, color_to_exclude, add_prompt):
    print(f"Starting translation process for {input_path}")

    # Procesar el documento para obtener textos originales
    textos_originales = procesar_documento(extension, input_path, output_path, {}, color_to_exclude, textos_traducidos_final=None, action="leer") 
    print("Diccionario textos_originales tal cual")
    print(textos_originales)

    # Arreglamos algunas cosas como comas sin espacio posterior
    textos_originales = ajuste_pre_traduccion(textos_originales)
    print("Diccionario textos_originales ajustado")
    print(textos_originales)

    # Unir textos fragmentados y luego filtrar textos irrelevantes (se quitan las entradas del diccionario que están en blanco o que no se tiene que enviar a traducir)
    textos_para_traducir, entradas_eliminadas = unir_textos_fragmentados(textos_originales)
    print(entradas_eliminadas)
    textos_para_traducir = filtrar_textos_relevantes(textos_para_traducir)

    print("Diccionario textos_para_traducir")
    print(textos_para_traducir)

    # Generación de bloques
    bloques = separar_texto_bloques(textos_para_traducir)
    bloques = incluir_placehold_inicial_final(bloques)

    # Traducción de bloques con el modelo - se coge el texto entre placeholder inicial y final y se valida que cuadren placeholders
    bloques_traducidos = aplicacion_modelo_bloques(bloques, origin_language, destination_language, extension, add_prompt)

    # Traducir los textos recopilados en bloques
    textos_traducidos = join_blocks(bloques_traducidos)

    print("Diccionario textos_traducidos")
    print(textos_traducidos)

    # Limpiar el texto traducido y separar las palabras fragmentadas
    textos_traducidos_final = eliminar_codigos(textos_traducidos)
    textos_traducidos_final = ajuste_post_traduccion(textos_para_traducir, textos_traducidos_final)
    print("Diccionario textos_traducidos_final + ajuste")

    # Separar los textos traducidos --> Generamos el diccionario con los textos traducidos y su código   
    textos_traducidos_final = separar_palabras_fragmentadas(textos_traducidos_final, entradas_eliminadas, textos_originales)
    print("Diccionario textos_traducidos_final + separar palabras")
    print(textos_traducidos_final)

    # Generar documento traducido
    procesar_documento(extension, input_path, output_path, textos_originales, color_to_exclude, textos_traducidos_final, action="reemplazar") 
    
    print(f'Se ha dejado el documento traducido en la ruta especificada: {output_path}')