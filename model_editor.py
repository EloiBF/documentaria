from groq import Groq

# Funció genèrica per traduir amb la IA, li passes un text i retorna la traducció

def prompt_text(texto, add_prompt, file_type, model='llama3-70b-8192', api_key_file='API_KEY.txt'):
    try:
        # Inicializa el cliente de Groq
        with open(api_key_file, 'r') as fichero:
            api_key = fichero.read().strip()
        client = Groq(api_key=api_key)

                # Genera el prompt base para la traducción según el tipo de archivo
        if file_type == None:
            prompt = f"""
        You are a multilingual text editor. Follow this rules:
        - Provide only the edited text without any additional comments or annotations. I don't want your feedback, only the pure edition, do not introduce"
        - Keep similar text lenght when editing. 
        - Do not duplicate or translate text if it is not asked, even if instructions are in other language.
        Additional rules that must be followed:
        {add_prompt}
        Text to edit:
        {texto}
        """

        if file_type in ['.pptx', '.docx', '.pdf','.txt', '.html']:
            prompt = f"""
        You are a multilingual text editor. Follow this rules:
        - Your task is to edit text while strictly preserving codes (_CDTR_00000) in their exact positions, including at the start or end of the text. 
        - Provide only the asked text without any additional comments or annotations. I don't want your feedback, only the pure edition, do not introduce"
        - Keep similar text lenght when editing.
        - Do not duplicate or translate text if it is not asked, even if instructions are in other language.

        Additional rules that must be followed:
        {add_prompt}
        Text to edit:
        {texto}
        """
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Llama a la API de Groq para editar el texto
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