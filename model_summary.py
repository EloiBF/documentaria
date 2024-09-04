from groq import Groq

def summarize_text(texto, file_type=None, model='llama3-70b-8192', api_key_file='API_KEY.txt', num_words=None , summary_language="auto", add_prompt=""):
    try:
        with open(api_key_file, 'r') as fichero:
            api_key = fichero.read().strip()
        client = Groq(api_key=api_key)

        if summary_language == "auto":
            summary_language == "the same language as given text"

        if file_type == None:
            prompt = f"""Explain me the content of the text in a summarized way strictly following this rules:
             - Focus on the most important topics in text
             - Use aprox {num_words} words for the whole summary
             - Do not add any extra comment, annotation or introduction to the response. Print only the summarized text.
             - Summary must be generated in {summary_language}
            Additional rules that must be followed:
            {add_prompt}
             Text to summarize is:{texto}"""

        elif file_type in ['.pptx', '.docx', '.pdf','.txt', '.html']:
            prompt = f"""Explain me the content of the text in a summarized way strictly following this rules:
             - Focus on the most important topics in text
             - Use aprox {num_words} words for the whole summary
             - Do not add any extra comment, annotation or introduction to the response. Print only the summarized text.
             - Ignore codes (_CDTR_00000) as if they were not in the text.
             - Summary must be generated in {summary_language}
            Additional rules that must be followed:
            {add_prompt}
             
             Text to summarize is:{texto}"""

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

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

