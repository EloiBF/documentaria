from pptx import Presentation
from pptx.dml.color import RGBColor
from docx import Document
from docx.shared import RGBColor
from pdf2docx import Converter
import re
from bs4 import BeautifulSoup
import chardet
from groq import Groq
import zipfile
from lxml import etree
from docx import Document
from io import BytesIO
import shutil
import os
import string



# Funciones para asignar un código a cada parte del texto con formato distinto
def generate_numeric_code(counter):
    return f"{counter:06d}"

# Función para no enviar a traducir textos de un color concreto, y mantenerlos como están
def color_to_rgb(color_to_exclude):
    # Verificar si color_hex es None o está vacío
    if color_to_exclude is None or len(color_to_exclude) != 7 or not color_to_exclude.startswith('#'):
        return None
    else:
        # Si pasa la validación, convertir el color hexadecimal a RGB
        color_to_exclude = color_to_exclude.lstrip('#')
        return RGBColor(int(color_to_exclude[:2], 16), int(color_to_exclude[2:4], 16), int(color_to_exclude[4:], 16))


# Arreglamos símbolos de puntuación al leer el texto del documento
def ajuste_pre_traduccion(diccionario):
    """
    Ajusta los textos en un diccionario para añadir espacios después de ciertos símbolos de puntuación
    cuando el siguiente texto no comienza con un espacio.

    :param diccionario: Un diccionario donde las claves son identificadores y los valores son textos a ajustar.
    :return: Un nuevo diccionario con los textos ajustados.
    """
    
    def es_simbolo_puntuacion(char):
        return char in string.punctuation and char not in string.whitespace
    
    def ajustar_texto(texto):
        if texto is None:
            return texto
        
        # Definir los símbolos que deben ser seguidos por un espacio
        simbolos = {',', ';', ':', '.', '!', '?'}
        
        # Reemplazar los símbolos al final de cada texto
        partes = texto.split('\n')
        partes_ajustadas = []
        
        for i, parte in enumerate(partes):
            # Procesar cada línea por separado
            nueva_parte = []
            longitud = len(parte)
            j = 0
            
            while j < longitud:
                char = parte[j]
                
                if char in simbolos:
                    nueva_parte.append(char)
                    
                    # Verificar si el siguiente carácter es un espacio o símbolo
                    if j + 1 < longitud and parte[j + 1] not in string.whitespace:
                        nueva_parte.append(' ')
                
                else:
                    nueva_parte.append(char)
                
                j += 1
            
            parte_ajustada = ''.join(nueva_parte)
            partes_ajustadas.append(parte_ajustada)
        
        return '\n'.join(partes_ajustadas)
    
    if not isinstance(diccionario, dict):
        raise ValueError("Entrada no válida. Debe proporcionar un diccionario.")

    textos_ajustados = {}
    for key, texto in diccionario.items():
        if texto:  # Verifica si el texto no es None ni vacío
            textos_ajustados[key] = ajustar_texto(texto)
    return {k: v for k, v in textos_ajustados.items() if v.strip() != ""}


# Funciones para seleccionar textos relevantes y separar el texto en bloques para enviar a traducir --> Genera un diccionario nuevo
def filtrar_textos_relevantes(textos):  # Quita textos que son solo espacios, numeros, etc
    return {code: texto for code, texto in textos.items() if texto.strip() and not re.fullmatch(r'[\s\W\d]+', texto)}

# Modifica el diccionario, editando algunas entradas para evitar que se corten palabras
def unir_textos_fragmentados(textos):  # Hay casos en que una palabra tiene letras con diferente formato, esta formula junta los dos textos para unificar la palabra y le da el primer código
    codigos = sorted(textos.keys())
    nuevo_textos = {}
    buffer_texto = ""
    buffer_codigo = ""
    texto_separador = {}

    for i in range(len(codigos)):
        codigo = codigos[i]
        texto = textos[codigo]

        if buffer_texto:
            if (len(buffer_texto) <= 3 or len(texto) <= 3) and buffer_texto[-1].isalpha() and texto and texto[0].isalpha() and texto[0].islower():
                texto_separador[buffer_codigo] = len(buffer_texto)  # Guardar la longitud del primer texto
                buffer_texto += texto
                textos[codigo] = ""  # Vaciar el texto en el diccionario original
            else:
                nuevo_textos[buffer_codigo] = buffer_texto
                buffer_texto = texto
                buffer_codigo = codigo
        else:
            buffer_texto = texto
            buffer_codigo = codigo

    if buffer_texto:
        nuevo_textos[buffer_codigo] = buffer_texto

    return nuevo_textos, texto_separador

def separar_texto_bloques(textos, max_chars_per_block=2000):
    """Separar el texto en bloques basados en un número máximo de caracteres por bloque,
       intentando dividir por signos de puntuación y, si no es posible, por palabras en mayúscula."""

    def split_text_into_blocks(textos, max_chars_per_block):
        blocks = []
        current_block = ""
        current_chars = 0

        # Crear una lista de pares (código, texto) a partir del diccionario de textos
        items = list(textos.items())
        
        for code, text in items:
            # Añadir el código y el texto al bloque actual
            new_text = f"(_CDTR_{code}){text}"
            
            # Si añadir el nuevo texto excede el límite de caracteres
            if current_chars + len(new_text) > max_chars_per_block:
                # Intentar cortar por signos de puntuación
                last_punctuation = max(
                    [m.end() for m in re.finditer(r'[.!?…]', current_block)] or [0]
                )
                
                if last_punctuation > 0:
                    # Cortar el bloque en la última posición del signo de puntuación
                    blocks.append(current_block[:last_punctuation])
                    # Continuar el bloque actual con el texto restante
                    current_block = current_block[last_punctuation:].strip()
                else:
                    # Intentar cortar por la siguiente palabra en mayúscula si no hay signos de puntuación
                    next_capital_word = re.search(r'\b[A-Z][a-z]*\b', current_block)
                    
                    if next_capital_word:
                        # Cortar el bloque en la posición de la siguiente palabra en mayúscula
                        capital_pos = next_capital_word.start()
                        blocks.append(current_block[:capital_pos].strip())
                        # Continuar el bloque actual con el texto restante
                        current_block = current_block[capital_pos:].strip()
                    else:
                        # Si no hay signos de puntuación ni palabras en mayúscula, cortar en el límite exacto
                        blocks.append(current_block)
                        current_block = ""
                
                current_chars = len(current_block)
            
            # Añadir el nuevo texto al bloque
            current_block += new_text
            current_chars += len(new_text)

        # Añadir el último bloque si no está vacío
        if current_block:
            blocks.append(current_block)

        return blocks

    # Convertir el diccionario de textos en bloques basados en el número máximo de caracteres por bloque
    bloques = split_text_into_blocks(textos, max_chars_per_block)
    
    return bloques



# APLICACIÓN DEL MODELO IA DE TRADUCCIÓN -- Entran bloques y salen bloques traducidos    # PODRÍAMOS INCLUIR FUNCIONES DE EMBEDDING AQUÍ
# Se usan las funciones de model_translator.py, que se puede usar para traducir cualquier texto

import re

def verificar_codigos(original, traducido):
    """Verifica que todos los códigos en el texto original estén presentes en el texto traducido.
    También verifica que los caracteres después del último código en el texto original estén presentes
    en el texto traducido después del último código correspondiente."""
    
    patron_codigo = r'\(_CDTR_\d{6}\)'
    
    # Encontrar todos los códigos en el texto original y traducido
    codigos_originales = re.findall(patron_codigo, original)
    codigos_traducidos = re.findall(patron_codigo, traducido)
    
    # Convertir listas a conjuntos para verificar presencia de códigos
    codigos_originales_set = set(codigos_originales)
    codigos_traducidos_set = set(codigos_traducidos)
    
    # Códigos faltantes en la traducción
    codigos_faltantes = codigos_originales_set - codigos_traducidos_set
    
    if codigos_faltantes:
        print(f'[ERROR] Códigos faltantes en la traducción: {codigos_faltantes}')
        return False
    
    # Verificar caracteres después del último código
    ultimo_codigo_original_match = re.search(patron_codigo, original[::-1])
    ultimo_codigo_original = ""
    if ultimo_codigo_original_match:
        ultimo_codigo_original = ultimo_codigo_original_match.group()[::-1]
    
    if ultimo_codigo_original:
        # Encontrar la posición del último código en el texto original
        pos_ultimo_codigo_original = original.rfind(ultimo_codigo_original) + len(ultimo_codigo_original)
        # Obtener los caracteres después del último código en el texto original
        caracteres_despues_ultimo_codigo_original = original[pos_ultimo_codigo_original:]
        
        # Encontrar la posición del último código en el texto traducido
        pos_ultimo_codigo_traducido = traducido.rfind(ultimo_codigo_original) + len(ultimo_codigo_original)
        # Obtener los caracteres después del último código en el texto traducido
        caracteres_despues_ultimo_codigo_traducido = traducido[pos_ultimo_codigo_traducido:]
        
        if caracteres_despues_ultimo_codigo_original and caracteres_despues_ultimo_codigo_original != caracteres_despues_ultimo_codigo_traducido:
            print(f'[ERROR] Los caracteres después del último código en el original no están presentes en la traducción.')
            return False

    return True




def join_blocks(bloques_traducidos):
    traduccion_completa = "".join(bloques_traducidos)
    translated_texts = re.findall(r"\(_CDTR_([A-Za-z0-9]{6})\)(.*?)(?=\(_CDTR_[A-Za-z0-9]{6}\)|$)", traduccion_completa, re.DOTALL)
    return {code: text for code, text in translated_texts}


# Funciones para limpiar el texto traducido
def eliminar_codigos(data):
    """
    Elimina els codis (_CDTR_00000, etc.) d'un text o d'un diccionari.

    :param data: Pot ser un text (str) o un diccionari (dict) on cal eliminar els codis.
    :return: El text o diccionari sense codis.
    """
    # Expressió regular per eliminar els codis amb o sense parèntesis
    patron = r"\(?_?CDTR[_A-Za-z0-9]{1,}\)?|\(?__?CDTR[_A-Za-z0-9]{1,}\)?|CDTR[_A-Za-z0-9]{1,}"
    
    if isinstance(data, str):
        # Si 'data' és un text, eliminem els codis del text
        return re.sub(patron, "", data)
    
    elif isinstance(data, dict):
        # Si 'data' és un diccionari, eliminem els codis per a cada valor del diccionari
        return {key: re.sub(patron, "", value) for key, value in data.items()}
    
    else:
        raise TypeError("L'entrada per eliminar codis ha de ser un text o un diccionari.")



# Limpiamos espacios y puntos que ha añadido de más la traducción
def ajuste_post_traduccion(entrada_original, entrada_traducida):
    """
    Ajusta los textos traducidos en un diccionario para que coincidan con el texto original
    en cuanto a espacios y símbolos al inicio y al final del texto.

    :param entrada_original: Un diccionario de textos originales.
    :param entrada_traducida: Un diccionario de textos traducidos.
    :return: Un diccionario de textos traducidos ajustados.
    """
    
    def ajustar_texto(texto_original, traduccion):
        if texto_original is None or traduccion is None:
            return traduccion

        def obtener_simbolos_y_espacios(texto):
            """Devuelve los caracteres antes y después del primer y último carácter alfanumérico en el texto."""
            primera_letra_numero = re.search(r'[A-Za-z0-9]', texto)
            ultima_letra_numero = re.search(r'[A-Za-z0-9](?!.*[A-Za-z0-9])', texto)
            
            if primera_letra_numero:
                primera_pos = primera_letra_numero.start()
                espacios_y_simbolos_inicio = texto[:primera_pos]
            else:
                espacios_y_simbolos_inicio = texto

            if ultima_letra_numero:
                ultima_pos = ultima_letra_numero.start()
                espacios_y_simbolos_final = texto[ultima_pos + 1:]
            else:
                espacios_y_simbolos_final = texto

            return espacios_y_simbolos_inicio, espacios_y_simbolos_final
        
        def ajustar_inicio_y_fin(texto_original, traduccion):
            espacios_y_simbolos_inicio_original, espacios_y_simbolos_final_original = obtener_simbolos_y_espacios(texto_original)
            espacios_y_simbolos_inicio_traduccion, espacios_y_simbolos_final_traduccion = obtener_simbolos_y_espacios(traduccion)

            # Ajustar el inicio del texto traducido
            traduccion = espacios_y_simbolos_inicio_original + traduccion[len(espacios_y_simbolos_inicio_traduccion):]
            
            # Ajustar el final del texto traducido
            traduccion = traduccion[:-(len(espacios_y_simbolos_final_traduccion))] + espacios_y_simbolos_final_original
            
            return traduccion

        return ajustar_inicio_y_fin(texto_original, traduccion)
    
    if not isinstance(entrada_original, dict) or not isinstance(entrada_traducida, dict):
        raise ValueError("Entrada no válida. Debe proporcionar diccionarios para ambos parámetros.")

    textos_ajustados = {}
    for key, texto_original in entrada_original.items():
        traduccion = entrada_traducida.get(key)
        if traduccion is not None:
            textos_ajustados[key] = ajustar_texto(texto_original, traduccion)
    
    return {k: v for k, v in textos_ajustados.items() if v.strip() != ""}


def separar_palabras_fragmentadas(textos_traducidos, texto_separador, textos_originales): # Una vez tenemos la el diccionario traducido, separamos las palabras unificadas con sus dos códigos, en base al num de caracteres del primer texto.
    textos_traducidos_ok = {}
    nuevos_codigos = {}
    counter = max([int(c) for c in textos_originales.keys()]) + 1

    for codigo, texto_traducido in textos_traducidos.items():
        if codigo in texto_separador:
            longitud = texto_separador[codigo]
            if len(texto_traducido) > longitud:
                primer_texto = texto_traducido[:longitud]
                segundo_texto = texto_traducido[longitud:]

                textos_traducidos_ok[codigo] = primer_texto

                # Encontrar el siguiente código disponible en el texto original
                siguiente_codigo = None
                for cod in sorted(textos_originales.keys()):
                    if cod > codigo and textos_originales[cod].strip() == "":
                        siguiente_codigo = cod
                        break

                # Si no hay un siguiente código disponible, crear uno nuevo
                if siguiente_codigo is None:
                    siguiente_codigo = generate_numeric_code(counter)
                    counter += 1

                textos_traducidos_ok[siguiente_codigo] = segundo_texto
                nuevos_codigos[codigo] = siguiente_codigo
            else:
                textos_traducidos_ok[codigo] = texto_traducido
        else:
            textos_traducidos_ok[codigo] = texto_traducido

    return textos_traducidos_ok

# Lectura/Reemplazo de PPTX
def procesar_ppt(input_path,output_path, textos_originales, color_to_exclude, textos_traducidos_final, action): 
    doc = Presentation(input_path)

    exclude_color_rgb = color_to_rgb(color_to_exclude)

    textos_originales = {}
    counter = 1  # Inicializar el contador desde 1

    # Recopilar textos y asignar códigos - Genera el diccionario "textos_originales"
    for slide in doc.slides:
        for shape in slide.shapes: 

            if shape.has_text_frame: # Acceder a figuras y cuadros de texto
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        if run.text: # Verificamos que existe la figura
                            if run.text.strip(): # Verificamos que tiene texto (no vacía)
                                if exclude_color_rgb == None or run.font.color is None or not hasattr(run.font.color, 'rgb') or run.font.color.rgb != exclude_color_rgb:
                                    code = generate_numeric_code(counter) # Volvemos a generar un código para cada texto para cruzar el formato con la traducción
                                    counter += 1
                                    if action == "leer":
                                        textos_originales[code] = run.text
                                    elif action == "reemplazar" and code in textos_traducidos_final:
                                        run.text = textos_traducidos_final[code]

            elif shape.has_table: # Acceder a tablas
                table = shape.table
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.text_frame.paragraphs:
                            for run in paragraph.runs:
                                if run.text: # Verificamos que existe la figura
                                    if run.text.strip(): # Verificamos que tiene texto (no vacía)
                                        if exclude_color_rgb == None or run.font.color is None or not hasattr(run.font.color, 'rgb') or run.font.color.rgb != exclude_color_rgb:
                                            code = generate_numeric_code(counter)
                                            counter += 1
                                            if action == "leer":
                                                textos_originales[code] = run.text
                                            elif action == "reemplazar" and code in textos_traducidos_final:
                                                run.text = textos_traducidos_final[code]

            elif shape.has_chart:  # Acceder a gráficos
                chart = shape.chart
                # Título del gráfico
                element = chart.chart_title
                if element.has_text_frame:
                    if element.text_frame.text.strip():
                        code = generate_numeric_code(counter)
                        counter += 1
                        if action == "leer":
                            textos_originales[code] = element.text_frame.text
                        elif action == "reemplazar" and code in textos_traducidos_final:
                            element.text_frame.text = textos_traducidos_final[code]

            elif shape.has_chart:  # Acceder a gráficos
                chart = shape.chart
                for serie in chart:
                    element = serie.point.data_labels
                    if element.has_text_frame:
                        if element.text_frame.text.strip():
                            code = generate_numeric_code(counter)
                            counter += 1
                            if action == "leer":
                                textos_originales[code] = element.text_frame.text
                            elif action == "reemplazar" and code in textos_traducidos_final:
                                element.text_frame.text = textos_traducidos_final[code]

    if action == "leer":
        return textos_originales
    elif action == "reemplazar":
        return doc.save(output_path)

# Lectura/Reemplazo DOCX
def procesar_docx(input_path,output_path, textos_originales, color_to_exclude, textos_traducidos_final, action): 
    doc = Document(input_path)

    exclude_color_rgb = color_to_rgb(color_to_exclude)

    textos_originales = {}
    counter = 1  # Inicializar el contador desde 1

    # Recopilar textos y asignar códigos - Genera el diccionario "textos_originales"
    for para in doc.paragraphs:
        for run in para.runs:
            if run.text: # Verificamos que existe la figura
                if run.text.strip(): # Verificamos que tiene texto (no vacía)
                    if exclude_color_rgb == None or run.font.color is None or not hasattr(run.font.color, 'rgb') or run.font.color.rgb != exclude_color_rgb:
                        code = generate_numeric_code(counter) # Volvemos a generar un código para cada texto para cruzar el formato con la traducción
                        counter += 1
                        if action == "leer":
                            textos_originales[code] = run.text
                            print(run.text)
                        elif action == "reemplazar" and code in textos_traducidos_final:
                            run.text = textos_traducidos_final[code]
                            
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        if run.text: # Verificamos que existe la figura
                            if run.text.strip(): # Verificamos que tiene texto (no vacía)
                                if exclude_color_rgb == None or run.font.color is None or not hasattr(run.font.color, 'rgb') or run.font.color.rgb != exclude_color_rgb:
                                    code = generate_numeric_code(counter)
                                    counter += 1
                                    if action == "leer":
                                        textos_originales[code] = run.text
                                    elif action == "reemplazar" and code in textos_traducidos_final:
                                        run.text = textos_traducidos_final[code]

    # Guardar documento temporal
    if action == 'reemplazar':
        input_path = input_path+'_temp.docx'
        doc.save(input_path)

    # Procesar shapes (cuadros de texto y formas) en el XML
    with zipfile.ZipFile(input_path, 'r') as docx_zip:
        # Extraemos el archivo `document.xml` para modificarlo
        with docx_zip.open('word/document.xml') as document_xml:
            tree = etree.parse(document_xml)
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

            # Buscar cuadros de texto (w:txbxContent) y otras figuras (formas)
            cuadros_texto = tree.xpath('//w:txbxContent//w:t', namespaces=namespaces)
            for element in cuadros_texto:
                if action == "leer":
                    code = generate_numeric_code(counter)
                    counter += 1
                    textos_originales[code] = element.text
                elif action == "reemplazar":
                    code = generate_numeric_code(counter)
                    counter += 1
                    if code in textos_traducidos_final:
                        element.text = textos_traducidos_final[code]

            # Buscar otras formas incrustadas (shapes)
            formas = tree.xpath('//w:drawTextBox//w:t', namespaces=namespaces)
            for element in formas:
                if action == "leer":
                    code = generate_numeric_code(counter)
                    counter += 1
                    textos_originales[code] = element.text
                elif action == "reemplazar":
                    code = generate_numeric_code(counter)
                    counter += 1
                    if code in textos_traducidos_final:
                        element.text = textos_traducidos_final[code]

    # Si estamos en modo reemplazar, creamos un nuevo archivo .docx con los cambios
    if action == "reemplazar":
        # Crear un archivo temporal
        temp_zip_path = output_path + '_temp.zip'
        with zipfile.ZipFile(input_path, 'r') as docx_zip:
            with zipfile.ZipFile(temp_zip_path, 'w') as temp_zip:
                # Copiamos todos los archivos originales, excepto `document.xml`
                for item in docx_zip.infolist():
                    if item.filename != 'word/document.xml':
                        temp_zip.writestr(item, docx_zip.read(item.filename))
                # Escribimos el nuevo `document.xml` modificado
                with BytesIO() as buffer:
                    tree.write(buffer, xml_declaration=True, encoding='UTF-8')
                    buffer.seek(0)
                    temp_zip.writestr('word/document.xml', buffer.read())

        # Renombrar el archivo temporal como el archivo de salida final
        shutil.move(temp_zip_path, output_path)
        os.remove(input_path)

    return textos_originales if action == "leer" else None

# Lectura/Reemplazo PDF
def procesar_pdf(input_path, output_path, textos_originales, color_to_exclude, textos_traducidos_final, action): 
    # Conversor de PDF a WORD
    def pdf_to_word(input_path, word_path):
        # Convertir el PDF a Word
        cv = Converter(input_path)
        cv.convert(word_path, start=0, end=None)
        cv.close()
    # Convertir el PDF a Word
    word_path = input_path.replace('.pdf', '.docx')
    pdf_to_word(input_path, word_path)

    return procesar_docx(word_path,output_path, textos_originales, color_to_exclude, textos_traducidos_final, action)

def procesar_txt(input_path, output_path, action, textos_traducidos_final=None):
    """Leer un archivo TXT, detectar su codificación, y dividir el texto en bloques de 10 palabras."""
    textos_originales = {}
    
    # Detectar la codificación del archivo
    with open(input_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
    
    # Leer el archivo usando la codificación detectada
    with open(input_path, 'r', encoding=encoding) as file:
        text = file.read()
    
    words = text.split()
    num_words = len(words)
    counter = 1
    
    # Dividir el texto en bloques de 10 palabras
    for i in range(0, num_words, 10):
        block = ' '.join(words[i:i+10])
        code = generate_numeric_code(counter)
        counter += 1
        if action == "leer":
            textos_originales[code] = block
        elif action == "reemplazar" and textos_traducidos_final and code in textos_traducidos_final:
            text = text.replace(block, textos_traducidos_final[code])
    
    # Guardar el archivo modificado si la acción es reemplazar
    if action == "reemplazar":
        with open(output_path, 'w', encoding=encoding) as file:
            file.write(text)
    
    # Retornar el diccionario de textos originales si la acción es leer
    return textos_originales if action == "leer" else None


def procesar_html(input_path, output_path, action, textos_traducidos_final=None):
    """Leer un archivo HTML, extraer el texto, y reemplazarlo si es necesario."""
    textos_originales = {}

    # Detectar la codificación del archivo
    with open(input_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']

    # Leer el archivo HTML usando la codificación detectada
    with open(input_path, 'r', encoding=encoding) as file:
        soup = BeautifulSoup(file, 'html.parser')

    counter = 1

    # Iterar sobre los elementos del HTML y procesar el texto
    for element in soup.find_all(text=True):
        text = element.strip()
        if text:
            code = generate_numeric_code(counter)
            counter += 1
            if action == "leer":
                textos_originales[code] = text
            elif action == "reemplazar":
                # Buscar el texto traducido usando el código generado
                if code in textos_traducidos_final:
                    new_text = textos_traducidos_final[code]
                    element.replace_with(new_text)

    # Guardar el archivo modificado si la acción es reemplazar
    if action == "reemplazar":
        with open(output_path, 'w', encoding=encoding) as file:
            file.write(str(soup))

    # Retornar el diccionario de textos originales si la acción es leer
    return textos_originales if action == "leer" else None


# Procesar documento según si es PPT, DOCX o PDF
def procesar_documento(extension, input_path ,output_path, textos_originales, color_to_exclude, textos_traducidos_final, action):
    if extension == ".pptx":
        return procesar_ppt(input_path, output_path, textos_originales, color_to_exclude, textos_traducidos_final, action)
    elif extension == ".docx":
        return procesar_docx(input_path, output_path, textos_originales, color_to_exclude, textos_traducidos_final, action)
    elif extension == ".pdf":
        return procesar_pdf(input_path, output_path, textos_originales, color_to_exclude, textos_traducidos_final, action) 
    elif extension in ['.txt']:
        return procesar_txt(input_path, output_path, action, textos_traducidos_final) 
    elif extension in ['.html']:
        return procesar_html(input_path, output_path, action, textos_traducidos_final) 
