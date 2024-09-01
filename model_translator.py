from groq import Groq

# Funció genèrica per traduir amb la IA, li passes un text i retorna la traducció

def translate_text(texto, origin_language, destination_language, add_prompt, model='llama3-70b-8192', api_key_file='API_KEY.txt'):
    """
    Traduce el texto utilizando el cliente de Groq.
    
    :param bloque: Texto a traducir.
    :param origin_language: Idioma de origen del texto. Usa "auto" para detección automática.
    :param destination_language: Idioma al que se traducirá el texto.
    :param model: Modelo de traducción a utilizar.
    :param api_key_file: Archivo que contiene la API key de Groq.
    :param add_prompt: Instrucciones adicionales para la traducción.
    :return: Texto traducido.
    """
    try:
        # Inicializa el cliente de Groq
        with open(api_key_file, 'r') as fichero:
            api_key = fichero.read().strip()
        client = Groq(api_key=api_key)

        # Genera el prompt para la traducción
        base_prompt = f"""
        Follow this rules:
        - Your task is to translate text while strictly preserving codes (_CDTR_00000) in their exact positions, including at the start or end of the text. 
        - Provide only the translated text without any additional comments or annotations. I don't want your feedback, only the pure translation, do not introduce "
        - Ensure that the translation is grammatically correct in {destination_language}, with special attention to the correct use of apostrophes in articles and pronouns.
        - Translate all words, including those starting with a capital letter, unless they appear to be proper names.
        - Keep similar text lenght when translating.

        Text to translate:
        """

        if origin_language == "auto":
            prompt = f"Translate text to {destination_language}.\n{base_prompt}{texto}"
        else:
            prompt = f"Translate text from {origin_language} to {destination_language}.\n{base_prompt}{texto}"

        if add_prompt:
            prompt += f"\nAdditional instructions: {add_prompt}"

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
        return traduccion
    
    except Exception as e:
        raise RuntimeError(f"Error during translation: {e}")