from langchain.text_splitter import RecursiveCharacterTextSplitter
from process_text_reader import read_document
from groq import Groq


def split_text(text, chunk_size=1000, chunk_overlap=200):
    """
    Divide el texto en fragmentos utilizando LangChain.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_text(text)
    return chunks


def summarize_text(texto, file_type=None, model='llama-3.1-70b-versatile', api_key_file='API_KEY.txt', num_words=None, summary_language="auto", add_prompt=""):
    """
    Genera un resumen para un texto específico.
    """
    try:
        with open(api_key_file, 'r') as fichero:
            api_key = fichero.read().strip()
        client = Groq(api_key=api_key)

        if summary_language == "auto":
            summary_language = "the same language as given text"

        if file_type is None:
            prompt = f"""Explain me the content of the text in a summarized way strictly following these rules:
            - Focus on the most important topics in text
            - Use approx {num_words} words for the whole summary
            - Do not add any extra comment, annotation, or introduction to the response. Print only the summarized text.
            - Summary must be generated in {summary_language}
            Additional rules that must be followed:
            {add_prompt}
            Text to summarize is: {texto}"""

        elif file_type in ['.pptx', '.docx', '.pdf', '.txt', '.html']:
            prompt = f"""Explain me the content of the text in a summarized way strictly following these rules:
            - Focus on the most important topics in text
            - Use approx {num_words} words for the whole summary
            - Do not add any extra comment, annotation, or introduction to the response. Print only the summarized text.
            - Ignore codes (_CDTR_00000) as if they were not in the text.
            - Summary must be generated in {summary_language}
            Additional rules that must be followed:
            {add_prompt}
            Text to summarize is: {texto}"""

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model
        )
        traduccion = chat_completion.choices[0].message.content.strip()
        return traduccion

    except Exception as e:
        raise RuntimeError(f"Error during translation: {e}")


def generate_summary(text, num_words, summary_language, file_type, add_prompt, old_summary=""):
    """
    Genera un resumen del texto utilizando el modelo especificado y maneja bloques si es necesario.
    """
    blocks = split_text(text)
    summary = ""

    for i, block in enumerate(blocks):
        if i > 0:
            block = old_summary + block  # Añade el contexto del bloque anterior.
        partial_summary = summarize_text(block, file_type=file_type, num_words=num_words, summary_language=summary_language, add_prompt=add_prompt)
        summary += partial_summary + "\n"

    return summary.strip()


def resumir_doc(input_path, num_words, summary_language, add_prompt):
    """
    Función principal para resumir un documento y guardar el resumen en un archivo TXT.
    """
    try:
        # Leer el documento y obtener el tipo de archivo
        text, file_type = read_document(input_path)

        # Generar el resumen
        summary = generate_summary(text, num_words, summary_language, file_type, add_prompt, old_summary="Resumen anterior: ")

        return summary  # Retorna el resumen

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return None  # Retorna None en caso de error


# Ejemplo de uso
if __name__ == "__main__":
    input_path = "documento_largo.pdf"
    num_words = 500
    summary_language = "es"
    add_prompt = "Make sure the summary is precise and structured."

    resumen = resumir_doc(
        input_path=input_path,
        num_words=num_words,
        summary_language=summary_language,
        add_prompt=add_prompt
    )

    if resumen:
        print("Resumen generado:")
        print(resumen)
    else:
        print("No se pudo generar el resumen.")
