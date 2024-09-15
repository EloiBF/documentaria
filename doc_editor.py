from groq import Groq

# Cargamos las funciones de procesado de documento, que se usan para editar o traducir
from process_text_editor import unir_textos_fragmentados
from process_text_editor import filtrar_textos_relevantes
from process_text_editor import separar_texto_bloques
from process_text_editor import separar_palabras_fragmentadas
from process_text_editor import verificar_codigos
from process_text_editor import join_blocks
from process_text_editor import eliminar_codigos
from process_text_editor import ajuste_post_traduccion
from process_text_editor import procesar_documento


def aplicación_modelo_bloques(bloques, add_prompt, extension, numintentos=10):
    bloques_traducidos = []

    for bloque in bloques:
        reintentos = 0
        while reintentos < numintentos:
            try:
                traduccion = prompt_text(bloque, add_prompt, extension)

                if verificar_codigos(bloque, traduccion):
                    print(f'Bloque original: {bloque}')
                    print(f'Bloque traducido: {traduccion}')
                    bloques_traducidos.append(traduccion)
                    break
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


    except Exception as e:
        raise RuntimeError(f"Error during revision: {e}")


# Función que aplica todo

def editar_doc(input_path, output_path, extension, color_to_exclude, add_prompt):
    print(f"Starting translation process for {input_path}")

    # Procesar el documento para obtener textos originales
    textos_originales = procesar_documento(extension, input_path, output_path, {}, color_to_exclude, textos_traducidos_final=None, action="leer") 

    print("Diccionario textos_originales")
    print(textos_originales)

    # Unir textos fragmentados y luego filtrar textos irrelevantes
    textos_para_traducir, texto_separador = unir_textos_fragmentados(textos_originales)
    textos_para_traducir = filtrar_textos_relevantes(textos_para_traducir)

    print("Diccionario textos_para_traducir")
    print(textos_para_traducir)

    # Inicializar variable para almacenar textos traducidos
    textos_traducidos = {}

    # Generación de bloques
    bloques = separar_texto_bloques(textos_para_traducir)

    # Traducción de bloques con el modelo
    bloques_traducidos = aplicación_modelo_bloques(bloques, add_prompt, extension)

    # Traducir los textos recopilados en bloques
    textos_traducidos = join_blocks(bloques_traducidos)

    print("Diccionario textos_traducidos")
    print(textos_traducidos)

    # Limpiar el texto traducido y separar las palabras fragmentadas
    textos_traducidos_final = eliminar_codigos(textos_traducidos)
    textos_traducidos_final = ajuste_post_traduccion(textos_traducidos_final, textos_traducidos)

    # Separar los textos traducidos --> Generamos el diccionario con los textos traducidos y su código
    textos_traducidos_final = separar_palabras_fragmentadas(textos_traducidos_final, texto_separador, textos_originales)

    print("Diccionario textos_traducidos_final")
    print(textos_traducidos_final)

    # Generar documento traducido
    procesar_documento(extension, input_path, output_path, textos_originales, color_to_exclude, textos_traducidos_final, action="reemplazar") 
    
    print(f'Se ha dejado el documento traducido en la ruta especificada: {output_path}')