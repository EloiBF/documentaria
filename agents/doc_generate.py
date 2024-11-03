import re
from docx import Document
from docx.shared import RGBColor, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE
from pptx import Presentation
from pptx.util import Inches
from pptx.dml.color import RGBColor as PPTXRGBColor
from groq import Groq

class DocxProcessor:
    def __init__(self):
        self.doc = Document()
        self._create_styles()

    def _create_styles(self):
        styles = self.doc.styles
        h1_style = styles.add_style('H1', WD_STYLE_TYPE.PARAGRAPH)
        h1_style.font.size = Pt(18)
        h1_style.font.bold = True

        h2_style = styles.add_style('H2', WD_STYLE_TYPE.PARAGRAPH)
        h2_style.font.size = Pt(16)
        h2_style.font.bold = True

    def create_document(self, content, output_path='output.docx'):
        self._process_content(content)
        self._clean_document()
        self.doc.save(output_path)
        return output_path

    def _process_content(self, content):
        lines = content.splitlines()
        current_table = None
        for line in lines:
            if "[TABLE]" in line:
                current_table = []
            elif "[/TABLE]" in line:
                if current_table:
                    self._create_table(current_table)
                current_table = None
            elif current_table is not None:
                current_table.append(line)
            else:
                self._process_line(line)

    def _process_line(self, line):
        if "[PAGEBREAK]" in line:
            self.doc.add_page_break()
            line = line.replace("[PAGEBREAK]", "")
        
        p = self.doc.add_paragraph()
        self._process_formatting(p, line)

    def _get_color(self, color_name):
        # Mapa de colores por nombre, devuelve instancias de RGBColor directamente
        color_mapping = {
            'red': RGBColor(0xFF, 0x00, 0x00),
            'green': RGBColor(0x00, 0xFF, 0x00),
            'blue': RGBColor(0x00, 0x00, 0xFF),
            'yellow': RGBColor(0xFF, 0xFF, 0x00),
            'orange': RGBColor(0xFF, 0xA5, 0x00),
            'purple': RGBColor(0x80, 0x00, 0x80),
            'black': RGBColor(0x00, 0x00, 0x00),
            'white': RGBColor(0xFF, 0xFF, 0xFF),
            'grey': RGBColor(0x80, 0x80, 0x80)
        }

        # Verificar si el color es un valor hexadecimal de 6 dígitos
        if re.match(r'^[0-9A-Fa-f]{6}$', color_name):
            r = int(color_name[0:2], 16)
            g = int(color_name[2:4], 16)
            b = int(color_name[4:6], 16)
            return RGBColor(r, g, b)

        # Si es un nombre de color, buscarlo en el mapa
        return color_mapping.get(color_name.lower(), RGBColor(0x00, 0x00, 0x00))

    def _process_formatting(self, paragraph, text):
        # Diccionario de formatos
        formats = {
            'BOLD': False,
            'ITALIC': False,
            'COLOR': None
        }

        pattern = r'\[(.*?)\]'
        matches = list(re.finditer(pattern, text))
        last_end = 0

        # Procesar los matches encontrados
        for match in matches:
            start, end = match.span()
            tag = match.group(1)

            # Agregar texto antes del tag encontrado
            if last_end < start:
                paragraph.add_run(text[last_end:start])

            # Procesar el tag
            if tag.startswith('COLOR:'):
                color_value = tag.split(':')[1]
                formats['COLOR'] = self._get_color(color_value)
            elif tag == 'BOLD':
                formats['BOLD'] = True
            elif tag == 'ITALIC':
                formats['ITALIC'] = True
            elif tag == 'H1':
                paragraph.style = 'H1'
            elif tag == 'H2':
                paragraph.style = 'H2'

            last_end = end

        # Agregar texto después del último tag
        if last_end < len(text):
            run = paragraph.add_run(text[last_end:])
            if formats['COLOR']:

                run.font.color.rgb = RGBColor.from_string('0000FF') ###############################################     
            
            if formats['BOLD']:
                run.bold = True
            if formats['ITALIC']:
                run.italic = True

    def _create_table(self, table_data):
        if not table_data:
            return

        rows = [row.split(";") for row in table_data]
        table = self.doc.add_table(rows=len(rows), cols=len(rows[0]))
        table.style = 'Table Grid'

        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                table.cell(i, j).text = cell.strip()

    def _clean_document(self):
        for paragraph in self.doc.paragraphs:
            paragraph.text = self._remove_bracketed_text(paragraph.text)

    def _remove_bracketed_text(self, content):
        return re.sub(r'\[.*?\]', '', content).strip()

class PptxProcessor:
    def __init__(self):
        self.prs = Presentation()

    def create_presentation(self, content, output_path='output.pptx'):
        self._process_content(content)
        self.prs.save(output_path)
        return output_path

    def _process_content(self, content):
        slides = content.split("[PAGEBREAK]")
        for slide_content in slides:
            self._create_slide(slide_content.strip())

    def _create_slide(self, content):
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[5])
        text_frame = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(5)).text_frame
        
        lines = content.splitlines()
        for line in lines:
            self._process_line(text_frame, line)

    def _process_line(self, text_frame, text):
        p = text_frame.add_paragraph()
        # Diccionario de formatos iniciales
        formats = {
            'BOLD': False,
            'ITALIC': False,
            'COLOR': None
        }

        # Patrón para encontrar etiquetas de formato
        pattern = r'\[(.*?)\]'
        matches = list(re.finditer(pattern, text))
        last_end = 0

        # Procesar las etiquetas encontradas
        for match in matches:
            start, end = match.span()
            tag = match.group(1)

            # Agregar el texto antes del tag encontrado
            if last_end < start:
                run = p.add_run()
                run.text = text[last_end:start]

                # Aplicar formatos si los hay
                if formats['BOLD']:
                    run.font.bold = True
                if formats['ITALIC']:
                    run.font.italic = True
                if formats['COLOR']:
                    run.font.color.rgb = formats['COLOR']

            # Procesar el tag
            if tag.startswith('COLOR:'):
                color_value = tag.split(':')[1]
                formats['COLOR'] = self._get_color(color_value)
            elif tag == 'BOLD':
                formats['BOLD'] = True
            elif tag == 'ITALIC':
                formats['ITALIC'] = True
            elif tag == 'H1':
                p = text_frame.add_paragraph()
                p.text = ""
                p.font.size = Pt(24)
                p.font.bold = True
            elif tag == 'H2':
                p = text_frame.add_paragraph()
                p.text = ""
                p.font.size = Pt(20)
                p.font.bold = True

            last_end = end

        # Agregar texto después del último tag
        if last_end < len(text):
            run = p.add_run()
            run.text = text[last_end:]
            if formats['BOLD']:
                run.font.bold = True
            if formats['ITALIC']:
                run.font.italic = True
            if formats['COLOR']:
                run.font.color.rgb = formats['COLOR']

    def _get_color(self, color_name):
        color_mapping = {
            'red': PPTXRGBColor(255, 0, 0),
            'green': PPTXRGBColor(0, 255, 0),
            'blue': PPTXRGBColor(0, 0, 255),
            'yellow': PPTXRGBColor(255, 255, 0),
            'orange': PPTXRGBColor(255, 165, 0),
            'purple': PPTXRGBColor(128, 0, 128),
            'black': PPTXRGBColor(0, 0, 0),
            'white': PPTXRGBColor(255, 255, 255),
            'grey': PPTXRGBColor(128, 128, 128)
        }

        # Verificar si el color es un valor hexadecimal de 6 dígitos
        if re.match(r'^[0-9A-Fa-f]{6}$', color_name):
            r = int(color_name[0:2], 16)
            g = int(color_name[2:4], 16)
            b = int(color_name[4:6], 16)
            return PPTXRGBColor(r, g, b)

        # Si es un nombre de color, buscarlo en el mapa
        return color_mapping.get(color_name.lower(), PPTXRGBColor(0, 0, 0))



def generate_content(prompt, file_type, api_key_file='API_KEY.txt', model='llama-3.1-70b-versatile'):
    try:
        with open(api_key_file, 'r') as file:
            api_key = file.read().strip()

        client = Groq(api_key=api_key)

        formatting_codes = [
            ("[H1]", "[/H1]"),  # Título principal en negrita
            ("[H2]", "[/H2]"),  # Subtítulo en negrita
            ("[BOLD]", "[/BOLD]"),  # Texto en negrita
            ("[ITALIC]", "[/ITALIC]"),  # Texto en cursiva
            ("[COLOR:color_name]", "[/COLOR]"),  # Texto en color
            ("[PAGEBREAK]", ""),  # Salto de página
            ("[TABLE]", "[/TABLE]")  # Tabla
        ]

        formatting_codes_str = "\n".join([f"- {code[0]}: {code[1]}" for code in formatting_codes])

        full_prompt = f"""
        Generate structured content for a {file_type} document based on the following prompt:
        - Use the formatting codes provided below where appropriate. Always add start and end codes.
        Here are the formatting codes and their meanings:
        {formatting_codes_str}
        - For page or slide breaks, simply use [PAGEBREAK].
        - Do not use other formatting codes not provided.
        - For presentations (pptx), include a title for each slide with appropriate formatting (H1).
        - For text documents (docx), include title after a pagebreak and paragraphs with appropriate formatting.
        - You can combine multiple formatting codes, for example: [BOLD][COLOR:red]This is bold and red text[/COLOR][/BOLD]
        - Available colors: red, green, blue, yellow, orange, purple, black, white, grey
        - For tables, use the format:
          [TABLE]
          Header1;Header2
          Row1Col1;Row1Col2
          Row2Col1;Row2Col2
          [/TABLE]
        - Example of formatted output:
          [H1]Exploring the World of Science[/H1]
          [BOLD]Science is a way of learning about the world around us.[/BOLD]
          [ITALIC]This is a bulleted list item.[/ITALIC]
          [COLOR:blue]- Item 1[/COLOR]
          [COLOR:green]- Item 2[/COLOR]
          [PAGEBREAK]
          [TABLE]
          Animals;Habitat
          Lion;Savannah
          Tiger;Forest
          Whale;Ocean
          [/TABLE]
        Do not add any comment rather than the content asked, also do not repeat the prompt or any instruction.
        Always write content in the same language as given instructions.
        These are the given instructions for the content:
        {prompt}
        """

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": full_prompt}],
            model=model
        )
        content = chat_completion.choices[0].message.content.strip()
        return content

    except Exception as e:
        raise RuntimeError(f"Error generating content: {e}")

def generate_and_create_file(prompt, file_type, output):
    content = generate_content(prompt, file_type)
    print(content)

    if file_type.lower() == 'docx':
        processor = DocxProcessor()
        return processor.create_document(content, output)
    elif file_type.lower() == 'pptx':
        processor = PptxProcessor()
        return processor.create_presentation(content, output)
    else:
        raise ValueError("Tipo de archivo no soportado. Usa 'docx' o 'pptx'.")