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
    return f"{counter}"

# Función para no enviar a traducir textos de un color concreto, y mantenerlos como están
def color_to_rgb(color_to_exclude):
    # Verificar si color_hex es None o está vacío
    if color_to_exclude is None or len(color_to_exclude) != 7 or not color_to_exclude.startswith('#'):
        return None
    else:
        # Si pasa la validación, convertir el color hexadecimal a RGB
        color_to_exclude = color_to_exclude.lstrip('#')
        return RGBColor(int(color_to_exclude[:2], 16), int(color_to_exclude[2:4], 16), int(color_to_exclude[4:], 16))


# Modifica el diccionario, editando algunas entradas para evitar que se corten palabras
def unir_textos_fragmentados(textos):
    """
    Une los textos fragmentados en el diccionario, combinando las entradas donde
    una entrada tiene un solo carácter y la siguiente contiene el resto de la palabra.
    
    :param textos: Diccionario con los textos traducidos que pueden estar fragmentados.
    :return: Un nuevo diccionario con los textos combinados y un diccionario para identificar entradas eliminadas.
    """
    codigos = sorted(textos.keys(), key=lambda x: int(x))
    nuevo_textos = {}
    entradas_eliminadas = {}
    
    i = 0
    while i < len(codigos) - 1:  # Cambiamos el rango para evitar desbordamiento
        codigo_actual = codigos[i]
        codigo_siguiente = codigos[i + 1]
        texto_actual = textos[codigo_actual]
        texto_siguiente = textos[codigo_siguiente]
        
        if len(texto_actual) == 1 and texto_siguiente and texto_siguiente[0].isalpha() and texto_siguiente[0].islower():
            # Combinar textos
            nuevo_textos[codigo_actual] = texto_actual + texto_siguiente
            entradas_eliminadas[codigo_siguiente] = texto_siguiente
            i += 2  # Saltar la siguiente entrada
        else:
            nuevo_textos[codigo_actual] = texto_actual
            i += 1
    
    # Manejar la última entrada si no se combinó
    if i < len(codigos):
        ultimo_codigo = codigos[-1]
        nuevo_textos[ultimo_codigo] = textos[ultimo_codigo]

    return nuevo_textos, entradas_eliminadas

def separar_palabras_fragmentadas(textos_unidos, entradas_eliminadas):
    textos_separados = {}
    
    for codigo, texto in textos_unidos.items():
        if texto is None:
            # Si el texto es None, lo dejamos tal cual (o puedes cambiarlo por un texto vacío si prefieres)
            textos_separados[codigo] = None
            continue
        
        if any(int(codigo) < int(cod_eliminado) < int(codigo) + 2 for cod_eliminado in entradas_eliminadas):
            # Este texto fue unido, necesitamos separarlo
            primer_caracter = texto[0]
            resto_texto = texto[1:]
            
            textos_separados[codigo] = primer_caracter
            
            # Encontrar el código correcto para el resto del texto
            codigo_siguiente = str(int(codigo) + 1)
            if codigo_siguiente in entradas_eliminadas:
                texto_eliminado = entradas_eliminadas[codigo_siguiente]
                # Si el texto eliminado no es None, guardamos el resto del texto
                textos_separados[codigo_siguiente] = resto_texto if texto_eliminado is not None else None
            else:
                # Si el código siguiente no está en entradas_eliminadas, dejamos el resto del texto como None o vacío
                textos_separados[codigo_siguiente] = None
        else:
            # Este texto no fue unido, lo copiamos tal cual
            textos_separados[codigo] = texto
    
    return textos_separados


# Funciones para seleccionar textos relevantes y separar el texto en bloques para enviar a traducir --> Genera un diccionario nuevo

# Filtramos del diccionario original, las entradas que no contienen letras (se quedan igual en el docu)
def filtrar_textos_relevantes(diccionario):
    # Filtrar textos que contengan al menos una letra
    return {code: texto for code, texto in diccionario.items() if re.search(r'[a-zA-Z]', texto)}

# Juntamos todos los textos de los diccionarios y los separamos por bloques, evitando cortar frases.
def separar_texto_bloques(diccionario, max_chars_per_block=1000, min_chars_per_block=30, max_codes_per_block=20):
    """Separar el texto en bloques basados en un número máximo y mínimo de caracteres por bloque,
    intentando dividir por signos de puntuación y, si no es posible, por palabras en mayúscula.
    Limita el número de códigos por bloque a un máximo de 5."""

    # Generar un texto concatenado de todas las claves y valores del texto
    full_text = "".join([f"(_CDTR_{code}){text}" for code, text in diccionario.items()])

    blocks = []
    current_pos = 0
    total_length = len(full_text)

    while current_pos < total_length:
        # Definir el límite superior e inferior para el bloque actual
        max_block_end = min(current_pos + max_chars_per_block, total_length)
        min_block_end = min(current_pos + min_chars_per_block, total_length)

        # Buscar la última posición de un placeholder (_CDTR_XXXXX) antes del límite máximo
        last_placeholder_pos = max([m.start() for m in re.finditer(r'\(_CDTR_\d+\)', full_text[current_pos:max_block_end])] or [0])

        # Buscar la última posición de un signo de puntuación antes del límite máximo
        last_punctuation_pos = max([m.end() for m in re.finditer(r'[.!?…]', full_text[current_pos:max_block_end])] or [0])

        if last_punctuation_pos > min_block_end:
            block_end = current_pos + last_punctuation_pos
        else:
            # Si no hay signos de puntuación dentro del límite, buscar la última letra mayúscula
            last_capital_pos = max([m.end() for m in re.finditer(r'\b[A-Z][a-z]*\b', full_text[current_pos:max_block_end])] or [0])

            if last_capital_pos > min_block_end:
                block_end = current_pos + last_capital_pos
            else:
                # Si no hay letras mayúsculas dentro del límite, buscar la última palabra
                last_word_pos = full_text.rfind(' ', current_pos, max_block_end)

                if last_word_pos > min_block_end:
                    block_end = last_word_pos
                else:
                    block_end = max_block_end

        # Ajustar block_end para no cortar un placeholder (_CDTR_XXXXX) por la mitad
        if last_placeholder_pos > 0 and last_placeholder_pos < block_end - current_pos:
            block_end = current_pos + last_placeholder_pos

        # Extraer el bloque temporalmente
        temp_block = full_text[current_pos:block_end].strip()

        # Contar el número de códigos en el bloque temporal
        num_codes = len(re.findall(r'\(_CDTR_\d+\)', temp_block))

        # Si el número de códigos excede el máximo permitido, ajustar el block_end
        if num_codes > max_codes_per_block:
            code_positions = [m.start() for m in re.finditer(r'\(_CDTR_\d+\)', temp_block)]
            block_end = current_pos + code_positions[max_codes_per_block]

        # Añadir el bloque a la lista
        block = full_text[current_pos:block_end].strip()
        blocks.append(block)

        # Actualizar la posición actual
        current_pos = block_end

    # Ajustar el penúltimo bloque si el último bloque es demasiado corto
    if len(blocks) > 1 and len(blocks[-1]) < min_chars_per_block:
        blocks[-2] += blocks[-1]
        blocks.pop()

    return blocks



# Añadimos placeholders de inicio y fin para evitar recoger textos adicionales que pueda meter la IA
def incluir_placehold_inicial_final(bloques):
    # Crear una nueva lista con los bloques modificados
    bloques_modificados = [f"(_CDTR_ST){bloque}(_CDTR_ND)" for bloque in bloques]
    return bloques_modificados

# Función para seleccionar el texto entre placeholder de inicio y fin
def seleccionar_texto_placeholder(texto):
    # Usar una expresión regular para capturar el texto entre los placeholders
    match = re.search(r'\(_CDTR_ST\)(.*?)\(_CDTR_ND\)', texto)
    if match:
        # Devolver el texto encontrado entre los placeholders
        return match.group(1)
    return None  # Si no se encuentra el patrón, devolver None

# APLICACIÓN DEL MODELO IA DE TRADUCCIÓN -- Entran bloques y salen bloques traducidos    # PODRÍAMOS INCLUIR FUNCIONES DE EMBEDDING AQUÍ
# Se usan las funciones de model_translator.py, que se puede usar para traducir cualquier texto

def verificar_codigos(original, traducido):
    """Verifica que todos los códigos en el texto original estén presentes en el texto traducido.
    También verifica que los códigos de inicio (_CDTR_ST) y final (_CDTR_ND) estén presentes,
    y que los caracteres después del último código en el texto original estén presentes en el texto traducido.
    Además, verifica que no haya códigos duplicados en ninguno de los textos.
    """
    
    # Patrones para los códigos
    patron_codigo_numerico = r'\(_CDTR_\d+\)'  # Cualquier código con número (_CDTR_X) donde X es un número
    patron_codigo_inicio = r'\(_CDTR_ST\)'     # Placeholder de inicio
    patron_codigo_final = r'\(_CDTR_ND\)'      # Placeholder de final
    
    # Verificar que los placeholders de inicio y fin existan en ambos textos
    if not (re.search(patron_codigo_inicio, original) and re.search(patron_codigo_inicio, traducido)):
        print(f'[ERROR] Falta el placeholder de inicio (_CDTR_ST) en alguno de los textos.')
        return False
    
    if not (re.search(patron_codigo_final, original) and re.search(patron_codigo_final, traducido)):
        print(f'[ERROR] Falta el placeholder de final (_CDTR_ND) en alguno de los textos.')
        return False
    
    # Encontrar todos los códigos numéricos en el texto original y traducido
    codigos_originales = re.findall(patron_codigo_numerico, original)
    codigos_traducidos = re.findall(patron_codigo_numerico, traducido)
    
    # Convertir listas a conjuntos para verificar la presencia de todos los códigos
    codigos_originales_set = set(codigos_originales)
    codigos_traducidos_set = set(codigos_traducidos)
    
    # Verificar si hay códigos duplicados en el texto original
    if len(codigos_originales) != len(codigos_originales_set):
        print(f'[ERROR] Hay códigos duplicados en el texto original.')
        return False
    
    # Verificar si hay códigos duplicados en el texto traducido
    if len(codigos_traducidos) != len(codigos_traducidos_set):
        print(f'[ERROR] Hay códigos duplicados en el texto traducido.')
        return False
    
    # Verificar si hay códigos faltantes en la traducción
    codigos_faltantes = codigos_originales_set - codigos_traducidos_set
    if codigos_faltantes:
        print(f'[ERROR] Códigos faltantes en la traducción: {codigos_faltantes}')
        return False
    
    return True

def join_blocks(bloques_traducidos):
    # Unir todos los bloques traducidos en un solo string
    traduccion_completa = "".join(bloques_traducidos)
    # Buscar todos los códigos CDTR con 1 o más dígitos/letras y capturar el texto entre ellos
    # Ignoramos los códigos de inicio (_CDTR_ST) y final (_CDTR_ND), que ya han sido eliminados previamente.
    translated_texts = re.findall(r"\(_CDTR_([A-Za-z0-9]+)\)(.*?)(?=\(_CDTR_[A-Za-z0-9]+\)|$)", traduccion_completa, re.DOTALL)
    # Retornar un diccionario con el código como clave y el texto asociado como valor
    return {code: text.strip() for code, text in translated_texts}

# Funciones para limpiar el texto traducido y poder enviar bloques sin placeholders para una mejor traducción de ejemplo
def codigos_por_espacios(data):
    """
    Reemplaza los códigos del tipo (_CDTR_00000) o similares con espacios en un texto, una lista o un diccionario.

    :param data: Puede ser un texto (str), una lista o un diccionario del cual reemplazar los códigos.
    :return: El texto, lista o diccionario con los códigos reemplazados por espacios.
    """
    # Expresión regular para encontrar los códigos del tipo (_CDTR_00000) o variaciones
    patron = r"\(?_?CDTR[_A-Za-z0-9]*\)?"
    
    if isinstance(data, str):
        # Si 'data' es un texto, reemplazamos los códigos por espacios
        return re.sub(patron, " ", data)
    
    elif isinstance(data, list):
        # Si 'data' es una lista, aplicamos la función recursivamente a cada elemento
        return [codigos_por_espacios(elemento) for elemento in data]
    
    elif isinstance(data, dict):
        # Si 'data' es un diccionario, aplicamos la función a cada valor
        return {clave: codigos_por_espacios(valor) for clave, valor in data.items()}
    
    else:
        raise TypeError("La entrada debe ser un texto, una lista o un diccionario.")

# Funciones para limpiar el texto traducido de codigos por si acaso
def eliminar_codigos(data):
    """
    Elimina los códigos del tipo (_CDTR_00000) o similares de un texto o de un diccionario.

    :param data: Puede ser un texto (str) o un diccionario (dict) del cual eliminar los códigos.
    :return: El texto o diccionario sin los códigos.
    """
    # Expresión regular para eliminar los códigos del tipo (_CDTR_00000) o variaciones
    patron = r"\(?_?CDTR[_A-Za-z0-9]*\)?"
    
    if isinstance(data, str):
        # Si 'data' es un texto, eliminamos los códigos del texto
        return re.sub(patron, "", data)
    
    elif isinstance(data, dict):
        # Si 'data' es un diccionario, eliminamos los códigos para cada valor del diccionario
        return {key: re.sub(patron, "", value) for key, value in data.items()}
    
    else:
        raise TypeError("La entrada para eliminar códigos debe ser un texto o un diccionario.")

# Ajustamos espacios i símbolos de cada entrada del diccionario para que sean idénticos al diccionario original
def ajuste_post_traduccion(entrada_original, entrada_traducida):
    """
    Ajusta los textos traducidos para que coincidan con el texto original en cuanto a 
    espacios y símbolos al inicio y al final. Además, agrega un espacio después de un
    símbolo de puntuación seguido de una letra o número, a menos que sea el último carácter.
    """
    
    def ajustar_texto(texto_original, traduccion):
        if texto_original is None or traduccion is None:
            return traduccion

        # Extraer los caracteres al inicio y final del texto original
        inicio_original_match = re.match(r'^\W*', texto_original)
        final_original_match = re.search(r'\W*$', texto_original)

        inicio_original = inicio_original_match.group(0) if inicio_original_match else ""
        final_original = final_original_match.group(0) if final_original_match else ""

        # Extraer el contenido de la traducción desde la primera hasta la última letra/número
        contenido_traduccion_match = re.search(r'\w.*\w', traduccion)
        if contenido_traduccion_match:
            contenido_traduccion = contenido_traduccion_match.group(0)
        else:
            contenido_traduccion = traduccion  # Si no se encuentra, usamos la traducción original

        # Insertar un espacio después de los símbolos de puntuación seguidos de letras o números
        contenido_traduccion_ajustado = re.sub(r'([.,:;!?])([a-zA-Z0-9])', r'\1 \2', contenido_traduccion)

        # Concatenar la parte inicial y final del original con el contenido limpio de la traducción,
        # asegurando que no haya duplicación de espacios.
        return inicio_original + contenido_traduccion_ajustado.strip() + final_original

    if not isinstance(entrada_original, dict) or not isinstance(entrada_traducida, dict):
        raise ValueError("Entrada no válida. Debe proporcionar diccionarios para ambos parámetros.")

    # Aplicar el ajuste a cada texto en el diccionario
    textos_ajustados = {
        key: ajustar_texto(texto_original, entrada_traducida.get(key))
        for key, texto_original in entrada_original.items()
        if entrada_traducida.get(key)
    }
    
    return {k: v for k, v in textos_ajustados.items() if v.strip() != ""}

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
