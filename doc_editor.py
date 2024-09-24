from groq import Groq
import re

# Cargamos las funciones de procesado de documento, que se usan para editar o traducir
from process_text_editor import Modify_Diccionarios, Modify_Bloques, DOCX_process, PPTX_process, Excel_process, PDF_process, TXT_process, HTML_process

# Funcions específiques de l'edició de documents. Prompting i model IA.

class Aplicar_Modelo:

    #  Función genérica para traducir con IA, con soporte para contexto
    def modelo_edición(texto, add_prompt, model='llama-3.1-70b-versatile', api_key_file='API_KEY.txt'):
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
            Edit text following instructions given.
            Ensure placeholders <ph> and </ph> are maintained identic in text.
            Text to edit is {texto} 
            """

            if add_prompt:
                base_prompt += f"\n\nInstructions to edit text are: {add_prompt}"

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


    def aplicar_modelo_IA(bloques, extension, add_prompt="", numintentos=50):
        """
        Aplica el modelo de traducción y revisión a los bloques. Verifica los placeholders después de cada paso.
        """
        bloques_traducidos = []

        # Iterar sobre cada bloque para traducir
        for bloque in bloques:
            reintentos = 0
            traduccion_valida = False

            while reintentos < numintentos:
                try:
                    # Traducimos el bloque actual
                    traduccion = Aplicar_Modelo.modelo_edición(bloque, add_prompt)

                    # Verificamos que los placeholders se mantengan en la traducción
                    if Validar_Bloques.verificar_placeholders(bloque, traduccion):
                        print(f'BLOQUE ORIGINAL: {bloque}')
                        print(f'TRADUCCIÓN: {traduccion}')

                        # Si pasa la validación, añadimos el bloque revisado
                        bloques_traducidos.append(traduccion)
                        traduccion_valida = True
                        break  # Salimos del bucle si la revisión es válida
                    else:
                        print(f'[ERROR] Bloque original: {bloque}')
                        print(f'[ERROR] Bloque traducido: {traduccion}')
                        raise ValueError("Error por placeholders incorrectos en traducción")

                except Exception as e:
                    print(f'Error en la traducción/revisión del bloque. {e}. Reintentando...')
                    reintentos += 1

            if not traduccion_valida:
                print(f'No se pudo traducir ni revisar correctamente el bloque después de {numintentos} intentos')
                bloques_traducidos.append(bloque)  # Si no fue posible, se añade el bloque original

        return bloques_traducidos


# Función final que lee el documento y realiza la traducción. Genera el diccionario original, lo ajusta, recibe el traducido, lo ajusta y reemplaza los textos con los valores del traducido final
def editar_doc(input_path, output_path, extension, color_to_exclude, add_prompt):
    
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
        textos_originales = Excel_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final=None, action="leer")
        print("Diccionario textos_originales")
        print(textos_originales)

    elif extension == ".txt":
        textos_originales = TXT_process.leer_doc(input_path, output_path, textos_traducidos_final=None, action="leer")
        print("Diccionario textos_originales")
        print(textos_originales)

    elif extension == ".html":
        textos_originales = HTML_process.leer_doc(input_path, output_path, textos_traducidos_final=None, action="leer")
        print("Diccionario textos_originales")
        print(textos_originales)


    # Filtramos entradas del diccionario que no se envían a la IA (espacios o vacías), al reconstruir el docu no se habran modificado
    textos_para_traducir = Modify_Diccionarios.filtrar_textos_relevantes(textos_originales)
    print("Diccionario textos_para_traducir")
    print(textos_para_traducir)


    # Generación de bloques

    bloques = Modify_Diccionarios.separar_texto_bloques(textos_para_traducir)

    # Traducción de bloques con el modelo
    bloques_traducidos = Aplicar_Modelo.aplicar_modelo_IA(bloques, extension, add_prompt)

    # Traducir los textos recopilados en bloques --> Obtenemos un diccionario con los textos traducidos
    textos_traducidos = Modify_Bloques.join_blocks(bloques_traducidos)

    print("Diccionario textos_traducidos")
    print(textos_traducidos)

    # Limpiar el texto traducido por si se ha quedado algun código de formato y separar las palabras fragmentadas
    textos_traducidos_final = Validar_Bloques.eliminar_placeholders(textos_traducidos)
    textos_traducidos_final = Modify_Diccionarios.ajuste_post_traduccion_dict(textos_para_traducir,textos_traducidos_final)
    print("Diccionario textos_traducidos_final + ajuste")
    print(textos_traducidos_final)

    # Reconstruir diccionario original (tal y como se lee) y substituir el texto
    if extension == ".pptx":
        PPTX_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final, action = "reemplazar")

    elif extension == ".docx":
        DOCX_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final, action = "reemplazar")

    elif extension == ".pdf":
        PDF_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final, action = "reemplazar")

    elif extension == ".xlsx":
        Excel_process.leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final, action = "reemplazar")

    elif extension == ".txt":
        TXT_process.leer_doc(input_path, output_path, textos_traducidos_final, action="reemplazar")

    elif extension == ".html":
        HTML_process.leer_doc(input_path, output_path, textos_traducidos_final, action="reemplazar")

    print(f'Se ha dejado el documento traducido en la ruta especificada: {output_path}')
