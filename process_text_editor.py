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
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import os
import sys
from pptx import Presentation
from pptx.dml.color import RGBColor
from docx import Document
from docx.shared import RGBColor
from pdf2docx import Converter
import time
import re
from pathlib import Path
import zipfile
from lxml import etree
from docx import Document
from io import BytesIO
import shutil
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import zipfile
from lxml import etree

class Modify_Diccionarios:

    # Generar clave del diccionario para cada texto que se lee
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

    # Funciones para seleccionar textos relevantes y separar el texto en bloques para enviar a traducir

    def filtrar_textos_relevantes(diccionario):
        # Filtrar textos que no estén vacíos o sólo contengan espacios en blanco
        return {code: texto for code, texto in diccionario.items() if len(texto.strip()) > 0}

    import re

    def separar_texto_bloques(diccionario, max_chars_per_block=300, min_chars_per_block=30, max_codes_per_block=5):
        """
        Separar el texto en bloques basados en un número máximo y mínimo de caracteres por bloque,
        siempre separando por el cierre de un </ph>, intentando además dividir por signos de puntuación y,
        si no es posible, por palabras en mayúscula. Limita el número de códigos <ph> por bloque a un máximo de 5.
        """

        # Generar un texto concatenado de todas las claves y valores del diccionario, encerrando el texto entre <ph> y </ph>
        full_text = "".join([f"<ph>{text}</ph>" for text in diccionario.values()])

        blocks = []
        current_pos = 0
        total_length = len(full_text)

        while current_pos < total_length:
            # Definir el límite superior e inferior para el bloque actual
            max_block_end = min(current_pos + max_chars_per_block, total_length)
            min_block_end = min(current_pos + min_chars_per_block, total_length)

            # Buscar la última posición de un </ph> antes del límite máximo
            last_placeholder_pos = max([m.end() for m in re.finditer(r'</ph>', full_text[current_pos:max_block_end])] or [0])

            # Buscar la última posición de un signo de puntuación antes del límite máximo
            last_punctuation_pos = max([m.end() for m in re.finditer(r'[.!?…]', full_text[current_pos:max_block_end])] or [0])

            # Verificar si el siguiente texto comienza con mayúscula
            next_capital_pos = re.search(r'\b[A-Z]', full_text[max_block_end:])

            # Priorizar terminar el bloque en la puntuación si existe
            if last_punctuation_pos > min_block_end:
                block_end = current_pos + last_punctuation_pos
            # Si no hay puntuación, cortar en el cierre de </ph>
            elif last_placeholder_pos > min_block_end:
                block_end = current_pos + last_placeholder_pos
            # Si no hay cierre de </ph>, cortar en la siguiente mayúscula
            elif next_capital_pos:
                block_end = max_block_end + next_capital_pos.start()
            else:
                block_end = max_block_end

            # Asegurarse de que el bloque incluya todo el contenido del último <ph>...</ph> si empieza dentro del bloque
            temp_block = full_text[current_pos:block_end]
            open_ph_pos = temp_block.rfind('<ph>')
            close_ph_pos = temp_block.rfind('</ph>')

            if open_ph_pos > close_ph_pos:
                # Si hay un <ph> abierto sin cerrar dentro del bloque, extendemos el bloque hasta encontrar el cierre
                next_close_ph = re.search(r'</ph>', full_text[block_end:])
                if next_close_ph:
                    block_end += next_close_ph.end()

            # Extraer el bloque temporalmente
            temp_block = full_text[current_pos:block_end].strip()

            # Contar el número de códigos <ph> en el bloque temporal
            num_codes = len(re.findall(r'<ph>.*?</ph>', temp_block))

            # Si el número de códigos excede el máximo permitido, ajustar el block_end
            if num_codes > max_codes_per_block:
                code_positions = [m.end() for m in re.finditer(r'</ph>', temp_block)]
                block_end = current_pos + code_positions[max_codes_per_block - 1]

            # Añadir el bloque a la lista
            block = full_text[current_pos:block_end].strip()
            blocks.append(block)

            # Actualizar la posición actual
            current_pos = block_end

        # Ajustar el penúltimo bloque si el último bloque es demasiado corto
        if len(blocks) > 1 and len(blocks[-1]) < min_chars_per_block:
            blocks[-2] += " " + blocks[-1]
            blocks.pop()

        return blocks


    # Ajustamos espacios i símbolos de cada entrada del diccionario para que sean idénticos al diccionario original
    def ajuste_post_traduccion_dict(diccionario_original, diccionario_traduccion):
        diccionario_ajustado = {}
        
        for clave, texto_original in diccionario_original.items():
            traduccion = diccionario_traduccion.get(clave)
            
            if texto_original is None or traduccion is None:
                diccionario_ajustado[clave] = traduccion
                continue

            # Extraer los espacios al inicio y final del texto original
            inicio_original_match = re.match(r'^\s*', texto_original)
            final_original_match = re.search(r'\s*$', texto_original)

            inicio_original = inicio_original_match.group(0) if inicio_original_match else ""
            final_original = final_original_match.group(0) if final_original_match else ""

            # Limpiar espacios al inicio y final de la traducción
            contenido_traduccion = traduccion.strip()

            # Concatenar los espacios del original con la traducción limpia
            texto_ajustado = inicio_original + contenido_traduccion + final_original

            diccionario_ajustado[clave] = texto_ajustado

        return diccionario_ajustado

class Modify_Bloques:
    
    # Función para juntar los bloques
    def join_blocks(bloques_traducidos):
        # Unir todos los bloques traducidos en un solo string
        traduccion_completa = "".join(bloques_traducidos)
        
        # Buscar todos los textos entre <ph> y </ph>
        translated_texts = re.findall(r"<ph>(.*?)</ph>", traduccion_completa, re.DOTALL)
        
        # Crear un diccionario con índices numéricos como claves y los textos como valores
        return {str(i): text.strip() for i, text in enumerate(translated_texts, 1)}

class Validar_Bloques:
    def verificar_placeholders(original, traducido):
        """
        Verifica que los placeholders en el texto original y traducido cumplan con las siguientes condiciones:
        1. Hay el mismo número de <ph> y </ph> en el texto original y la traducción.
        2. Un <ph> siempre debe cerrarse con un </ph>. No puede haber otro <ph> antes.
        3. Siempre debe empezar el bloque de texto por <ph> y acabar por </ph>.
        4. Los placeholders deben estar en el mismo orden en ambos textos.
        """
        def contar_y_verificar_placeholders(texto):
            apertura = texto.count('<ph>')
            cierre = texto.count('</ph>')
            if apertura != cierre:
                print(f'[ERROR] Número desigual de etiquetas de apertura y cierre: {apertura} <ph>, {cierre} </ph>')
                return False
            if not texto.startswith('<ph>') or not texto.endswith('</ph>'):
                print('[ERROR] El texto no comienza con <ph> o no termina con </ph>')
                return False
            patron = r'<ph>(?:(?!</ph>).)*?</ph>'
            bloques = re.findall(patron, texto)
            if len(bloques) != apertura:
                print('[ERROR] Algunos placeholders no están correctamente cerrados')
                return False
            return True

        # Verificar el texto original
        if not contar_y_verificar_placeholders(original):
            print('[ERROR] El texto original no cumple con los requisitos de los placeholders')
            return False

        # Verificar el texto traducido
        if not contar_y_verificar_placeholders(traducido):
            print('[ERROR] El texto traducido no cumple con los requisitos de los placeholders')
            return False

        # Verificar que los placeholders estén en el mismo orden
        placeholders_original = re.findall(r'<ph>', original)
        placeholders_traducido = re.findall(r'<ph>', traducido)
        
        if len(placeholders_original) != len(placeholders_traducido):
            print('[ERROR] El número de placeholders en la traducción no coincide con el original')
            return False

        return True

    def placeholders_por_espacios(data):
        """
        Reemplaza los placeholders <ph>...</ph> con espacios en un texto.

        :param data: Debe ser un texto (str) del cual reemplazar los placeholders.
        :return: El texto con los placeholders reemplazados por espacios.
        """
        if isinstance(data, str):
            # Reemplazamos los placeholders por espacios
            data = re.sub(r'<ph>.*?</ph>', " ", data)
            data = re.sub(r'\s+', " ", data)  # Reemplazar múltiples espacios por uno solo
            return data.strip()
        else:
            raise TypeError("La entrada para reemplazar placeholders debe ser un texto.")


    def eliminar_placeholders(data):
        """
        Elimina los placeholders <ph>...</ph> de un texto o de un diccionario.

        :param data: Puede ser un texto (str) o un diccionario (dict) del cual eliminar los placeholders.
        :return: El texto o diccionario sin los placeholders.
        """
        if isinstance(data, str):
            # Si 'data' es un texto, eliminamos los placeholders del texto
            return re.sub(r'<ph>.*?</ph>', "", data)
        
        elif isinstance(data, dict):
            # Si 'data' es un diccionario, eliminamos los placeholders para cada valor del diccionario
            return {key: re.sub(r'<ph>.*?</ph>', "", value) for key, value in data.items()}
        
        else:
            raise TypeError("La entrada para eliminar placeholders debe ser un texto o un diccionario.")

class PPTX_process: 

    # Lectura/Reemplazo de PPTX
    def leer_doc(input_path,output_path, color_to_exclude, textos_traducidos_final, action): 
        doc = Presentation(input_path)

        exclude_color_rgb = Modify_Diccionarios.color_to_rgb(color_to_exclude)

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
                                    code = Modify_Diccionarios.generate_numeric_code(counter) # Volvemos a generar un código para cada texto para cruzar el formato con la traducción
                                    counter += 1
                                    if action == "leer":
                                        textos_originales[code] = run.text
                                    elif action == "reemplazar" and code in textos_traducidos_final and (exclude_color_rgb == None or run.font.color is None or not hasattr(run.font.color, 'rgb') or run.font.color.rgb != exclude_color_rgb):
                                        run.text = textos_traducidos_final[code]

                elif shape.has_table: # Acceder a tablas
                    table = shape.table
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.text_frame.paragraphs:
                                for run in paragraph.runs:
                                    if run.text: # Verificamos que existe la figura
                                        if run.text.strip(): # Verificamos que tiene texto (no vacía)
                                            code = Modify_Diccionarios.generate_numeric_code(counter)
                                            counter += 1
                                            if action == "leer":
                                                textos_originales[code] = run.text
                                            elif action == "reemplazar" and code in textos_traducidos_final and (exclude_color_rgb == None or run.font.color is None or not hasattr(run.font.color, 'rgb') or run.font.color.rgb != exclude_color_rgb):
                                                    run.text = textos_traducidos_final[code]

                elif shape.has_chart:  # Acceder a gráficos
                    chart = shape.chart
                    # Título del gráfico
                    element = chart.chart_title
                    if element.has_text_frame:
                        if element.text_frame.text.strip():
                            code = Modify_Diccionarios.generate_numeric_code(counter)
                            counter += 1
                            if action == "leer":
                                textos_originales[code] = element.text_frame.text
                            elif action == "reemplazar" and code in textos_traducidos_final and (exclude_color_rgb == None or run.font.color is None or not hasattr(run.font.color, 'rgb') or run.font.color.rgb != exclude_color_rgb):
                                element.text_frame.text = textos_traducidos_final[code]

                elif shape.has_chart:  # Acceder a gráficos
                    chart = shape.chart
                    for serie in chart:
                        element = serie.point.data_labels
                        if element.has_text_frame:
                            if element.text_frame.text.strip():
                                code = Modify_Diccionarios.generate_numeric_code(counter)
                                counter += 1
                                if action == "leer":
                                    textos_originales[code] = element.text_frame.text
                                elif action == "reemplazar" and code in textos_traducidos_final and (exclude_color_rgb == None or run.font.color is None or not hasattr(run.font.color, 'rgb') or run.font.color.rgb != exclude_color_rgb):
                                    element.text_frame.text = textos_traducidos_final[code]

        if action == "leer":
            return textos_originales
        elif action == "reemplazar":
            return doc.save(output_path)
        
    def procesar_original(dict): # Por si tenemos que hacer ajustes específicos por tipo de documento
        return dict
    
    def reconstruir_original(dict_traducido,dict_original): # Por si tenemos que hacer ajustes específicos por tipo de documento
        return dict_traducido

class DOCX_process:
    def correcciones_docx(input_path, temp_output_path):
        """
        Procesa el archivo DOCX, unifica los runs con el mismo formato,
        y trata correctamente las tablas y listas. Crea un archivo DOCX temporal con los cambios.
        """
        namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        def unir_runs(tree):
            """
            Unifica los 'runs' consecutivos que tienen el mismo formato (tanto a nivel de run como de párrafo),
            y mantiene separados los textos en tablas y listas.
            """
            # Buscar todas las tablas
            tablas = tree.xpath('//w:tbl', namespaces=namespaces)
            
            for tabla in tablas:
                # Procesar cada celda de la tabla por separado
                celdas = tabla.xpath('.//w:tc', namespaces=namespaces)
                for celda in celdas:
                    process_paragraphs_in_container(celda)  # Procesar runs dentro de la celda

            # Buscar todas las listas (párrafos con numeración)
            listas = tree.xpath('//w:numPr', namespaces=namespaces)
            for lista in listas:
                parrafo = lista.xpath('./ancestor::w:p[1]', namespaces=namespaces)
                if parrafo:
                    process_paragraphs_in_container(parrafo[0])  # Procesar runs dentro del párrafo de la lista

            # Procesar todos los párrafos que no sean parte de tablas o listas
            parrafos = tree.xpath('//w:p[not(ancestor::w:tbl)]', namespaces=namespaces)
            for parrafo in parrafos:
                if not parrafo.xpath('.//w:numPr', namespaces=namespaces):  # Excluir listas
                    process_paragraphs_in_container(parrafo)  # Procesar los runs del párrafo

        def process_paragraphs_in_container(container):
            """
            Procesa los 'runs' dentro de un contenedor (parágrafo, celda de tabla o lista),
            unificando los que tienen el mismo formato y separando correctamente las entradas.
            """
            runs = container.xpath('.//w:r', namespaces=namespaces)
            previous_run = None

            for run in runs:
                texto_actual = ''.join(run.xpath('.//w:t/text()', namespaces=namespaces))
                formato_run_actual = etree.tostring(run.xpath('./w:rPr', namespaces=namespaces)[0], method='c14n') \
                    if run.xpath('./w:rPr', namespaces=namespaces) else None

                if previous_run is not None:
                    # Obtener el formato del run anterior
                    formato_run_anterior = etree.tostring(previous_run.xpath('./w:rPr', namespaces=namespaces)[0], method='c14n') \
                        if previous_run.xpath('./w:rPr', namespaces=namespaces) else None

                    # Unir los runs solo si tienen el mismo formato y están en el mismo contenedor
                    if formato_run_actual == formato_run_anterior:
                        previous_run.xpath('.//w:t', namespaces=namespaces)[0].text += texto_actual
                        run.getparent().remove(run)  # Eliminar el run actual porque lo hemos unido al anterior
                    else:
                        previous_run = run
                else:
                    previous_run = run

        try:
            # Crear un archivo temporal para aplicar las correcciones
            with zipfile.ZipFile(input_path, 'r') as docx_zip:
                temp_zip_path = temp_output_path + '_temp.zip'

                with zipfile.ZipFile(temp_zip_path, 'w') as temp_zip:
                    # Leer y procesar el archivo document.xml
                    with docx_zip.open('word/document.xml') as document_xml:
                        tree = etree.parse(document_xml)
                        unir_runs(tree)  # Unificar los runs respetando tablas y listas

                    # Crear el nuevo archivo .docx con los cambios aplicados
                    for item in docx_zip.infolist():
                        if item.filename == 'word/document.xml':
                            with BytesIO() as buffer:
                                tree.write(buffer, xml_declaration=True, encoding='UTF-8')
                                buffer.seek(0)
                                temp_zip.writestr(item.filename, buffer.read())
                        else:
                            temp_zip.writestr(item, docx_zip.read(item.filename))

            # Renombrar el archivo temporal como el archivo de salida final
            shutil.move(temp_zip_path, temp_output_path)
            print(f"Correcciones aplicadas y guardadas en {temp_output_path}")

        except zipfile.BadZipFile:
            print(f"El archivo {input_path} no es un archivo ZIP válido o está corrupto.")
        except FileNotFoundError:
            print(f"El archivo {input_path} no se encuentra.")
        except Exception as e:
            print(f"Ha ocurrido un error inesperado: {e}")


    @staticmethod
    def leer_doc(temp_path, output_path, color_to_exclude, textos_traducidos_final, action):
               
        exclude_color_rgb = Modify_Diccionarios.color_to_rgb(color_to_exclude)

        textos_originales = {}
        counter = 1  # Inicializar el contador desde 1

        # Función para procesar un archivo XML y actualizar el contador
        def process_xml(tree, counter):
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

            textos = tree.xpath('//w:t', namespaces=namespaces)
            if action == "leer":
                for texto in textos:
                    texto_str = texto.text.strip() if texto.text else ''
                    code = Modify_Diccionarios.generate_numeric_code(counter)
                    counter += 1
                    textos_originales[code] = texto_str
            elif action == "reemplazar":
                for texto in textos:
                    texto_str = texto.text.strip() if texto.text else ''
                    code = Modify_Diccionarios.generate_numeric_code(counter)
                    counter += 1
                    if code in textos_traducidos_final:
                        texto.text = textos_traducidos_final[code]
            return counter

        try:
            # Corregir el documento antes de proceder a leer o reemplazar
            temp_corrected_path = temp_path + "_corrected.docx"
            DOCX_process.correcciones_docx(temp_path, temp_corrected_path)

            # Ahora trabajamos con el archivo corregido
            with zipfile.ZipFile(temp_corrected_path, 'r') as docx_zip:
                with docx_zip.open('word/document.xml') as document_xml:
                    tree = etree.parse(document_xml)
                    counter = process_xml(tree, counter)

                # Procesar encabezados y pies de página
                headers_footers = {}
                for item in docx_zip.infolist():
                    if item.filename.startswith('word/header') or item.filename.startswith('word/footer'):
                        with docx_zip.open(item.filename) as xml_file:
                            header_footer_tree = etree.parse(xml_file)
                            counter = process_xml(header_footer_tree, counter)
                            headers_footers[item.filename] = header_footer_tree

            # Si estamos en modo reemplazar, creamos un nuevo archivo .docx con los cambios
            if action == "reemplazar":
                temp_zip_path = output_path + '_temp.zip'
                with zipfile.ZipFile(temp_corrected_path, 'r') as docx_zip:
                    with zipfile.ZipFile(temp_zip_path, 'w') as temp_zip:
                        # Copiamos todos los archivos originales, excepto `document.xml` y header/footer files
                        for item in docx_zip.infolist():
                            if item.filename == 'word/document.xml':
                                with BytesIO() as buffer:
                                    tree.write(buffer, xml_declaration=True, encoding='UTF-8')
                                    buffer.seek(0)
                                    temp_zip.writestr('word/document.xml', buffer.read())
                            elif item.filename in headers_footers:
                                with BytesIO() as buffer:
                                    headers_footers[item.filename].write(buffer, xml_declaration=True, encoding='UTF-8')
                                    buffer.seek(0)
                                    temp_zip.writestr(item.filename, buffer.read())
                            else:
                                temp_zip.writestr(item, docx_zip.read(item.filename))

                # Renombrar el archivo temporal como el archivo de salida final
                shutil.move(temp_zip_path, output_path)

            if action == "leer":
                print(f"Diccionario textos_originales: {textos_originales}")
                return textos_originales
            else:
                return None
        
        except zipfile.BadZipFile:
            print(f"El archivo {temp_path} no es un archivo ZIP válido o está corrupto.")
        except FileNotFoundError:
            print(f"El archivo {temp_path} no se encuentra.")
        except Exception as e:
            print(f"Ha ocurrido un error inesperado: {e}")

    def procesar_original(dict): # Por si tenemos que hacer ajustes específicos por tipo de documento
        return dict
    
    def reconstruir_original(dict_traducido,dict_original): # Por si tenemos que hacer ajustes específicos por tipo de documento
        return dict_traducido

class PDF_process:

    # Lectura/Reemplazo PDF
    def leer_doc(input_path, output_path, textos_originales, color_to_exclude, textos_traducidos_final, action): 
        # Conversor de PDF a WORD
        def pdf_to_word(input_path, word_path):
            # Convertir el PDF a Word
            cv = Converter(input_path)
            cv.convert(word_path, start=0, end=None)
            cv.close()
        # Convertir el PDF a Word
        word_path = input_path.replace('.pdf', '.docx')
        pdf_to_word(input_path, word_path)

        return DOCX_process.leer_doc(word_path,output_path, textos_originales, color_to_exclude, textos_traducidos_final, action)

    def procesar_original(dict):
        return DOCX_process.procesar_original(dict)
    
    def reconstruir_original(dict_traducido,dict_original):
        return DOCX_process.reconstruir_original(dict_traducido,dict_original) 

class Excel_process:
    def leer_doc(input_path, output_path, color_to_exclude, textos_traducidos_final, action):
        wb = load_workbook(input_path, keep_vba=True)  # keep_vba=True si el archivo contiene macros
        exclude_color_rgb = Modify_Diccionarios.color_to_rgb(color_to_exclude)

        textos_originales = {}
        counter = 1

        for sheet in wb.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str):
                        cell_value = cell.value.strip()
                        if cell_value:
                            code = Modify_Diccionarios.generate_numeric_code(counter)
                            counter += 1
                            cell_color_rgb = None
                            if cell.fill and isinstance(cell.fill, PatternFill):
                                cell_color_rgb = cell.fill.start_color.rgb[-6:]
                                if cell_color_rgb:
                                    cell_color_rgb = tuple(int(cell_color_rgb[i:i+2], 16) for i in (0, 2, 4))
                            if action == "leer":
                                textos_originales[code] = cell_value
                            elif action == "reemplazar" and code in textos_traducidos_final and (exclude_color_rgb is None or cell_color_rgb != exclude_color_rgb):
                                cell.value = textos_traducidos_final[code]

        if action == "leer":
            return textos_originales
        elif action == "reemplazar":
            wb.save(output_path)

    def procesar_original(dict):  # Por si tenemos que hacer ajustes específicos por tipo de documento
        return dict

    def reconstruir_original(dict_traducido, dict_original):  # Por si tenemos que hacer ajustes específicos por tipo de documento
        return dict_traducido

