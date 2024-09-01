from groq import Groq

# Funció genèrica per traduir amb la IA, li passes un text i retorna la traducció

def prompt_text(texto, add_prompt, model='llama3-70b-8192', api_key_file='API_KEY.txt'):
    try:
        # Inicializa el cliente de Groq
        with open(api_key_file, 'r') as fichero:
            api_key = fichero.read().strip()
        client = Groq(api_key=api_key)

        # Genera el prompt para la traducción
        prompt = f"""
        Follow this rules:
        - Your task is to  edit text while strictly preserving codes (_CDTR_00000) in their exact positions, including at the start or end of the text. 
        - Provide only the asked text without any additional comments or annotations. I don't want your feedback, only the pure translation, do not introduce"
        - Ensure that the translation is grammatically correct in the same language, with special attention to the correct use of apostrophes in articles and pronouns.
        - Translate all words, including those starting with a capital letter, unless they appear to be proper names.
        - Keep similar text lenght when editing.
        Additional rules that must be followed:
        {add_prompt}
        Text to translate:
        {texto}
        """
        
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