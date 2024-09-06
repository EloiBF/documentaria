from groq import Groq

# Funció genèrica per traduir amb la IA, li passes un text i retorna la traducció

def translate_text(texto, origin_language, destination_language, add_prompt, file_type, model='llama-3.1-70b-versatile', api_key_file='API_KEY.txt'):
    """
    Traduce el texto utilizando el cliente de Groq.

    :param texto: Texto a traducir.
    :param origin_language: Idioma de origen del texto. Usa "auto" para detección automática.
    :param destination_language: Idioma al que se traducirá el texto.
    :param model: Modelo de traducción a utilizar.
    :param api_key_file: Archivo que contiene la API key de Groq.
    :param add_prompt: Instrucciones adicionales para la traducción.
    :param file_type: Tipo de archivo (ppt, docx, pdf, txt, html).
    :return: Texto traducido.
    """
    try:
        # Inicializa el cliente de Groq
        with open(api_key_file, 'r') as fichero:
            api_key = fichero.read().strip()
        client = Groq(api_key=api_key)

        # Genera el prompt base para la traducción según el tipo de archivo
        if file_type == None:
            base_prompt = f"""
            Follow this rules:
            - Provide only the translated text without any additional comments or annotations. I don't want your feedback, only the pure translation, do not introduce "
            - Ensure that the translation is grammatically correct in {destination_language}, with special attention to the correct use of apostrophes in articles and pronouns.
            - Translate all words, including those starting with a capital letter, unless they appear to be proper names.
            - Keep similar text lenght when translating.

            Text to translate:
            """

        elif file_type in ['.pptx', '.docx', '.pdf','.txt', '.html']:
            base_prompt = f"""
            Follow this rules:
            - Your task is to translate text while strictly preserving codes (_CDTR_00000) in their exact positions, including at the start or end of the text. 
            - Provide only the translated text without any additional comments or annotations. I don't want your feedback, only the pure translation, do not introduce "
            - Ensure that the translation is grammatically correct in {destination_language}, with special attention to the correct use of apostrophes in articles and pronouns.
            - Translate all words, including those starting with a capital letter, unless they appear to be proper names.
            - Keep similar text lenght when translating.

            Text to translate:
            """
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Construye el prompt completo
        if origin_language == "auto":
            prompt = f"Translate text to {destination_language}.\n{base_prompt}\n{texto}"
        else:
            prompt = f"Translate text from {origin_language} to {destination_language}.\n{base_prompt}\n{texto}"

        if add_prompt:
            prompt += f"\nAdditional translation instructions: {add_prompt}"

        # Llama a la API de Groq para traducir el texto
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=model
        )

        traduccion = chat_completion.choices[0].message.content.strip()

        # AFEGIR AQUÍ LA VALIDACIÓ DE LA RESPOSTA. UTILITZANT UN MODEL MÉS ESPECIALITZAT PEL CATALÀ, I EL PROPI MODEL LLAMA 3.1 PER ALTRES IDIOMES.
        # AL VALIDAR LA RESPOSTA ELS MODELS FUNCIONEN MILLOR, SÓN CAPAÇOS DE CORREGIR ERRORS (model Reflection vídeo DOTCSV)

        return traduccion

    except Exception as e:
        raise RuntimeError(f"Error during translation: {e}")
