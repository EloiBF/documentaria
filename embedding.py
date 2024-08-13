import os
import sys
import torch
from transformers import AutoTokenizer, AutoModel
import chromadb
import docx
import fitz
import re


class DocumentProcessor:
    def __init__(self):
        self.docs = []

        # Cargar el modelo de embeddings de Hugging Face
        self.tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        self.model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

        # Inicializar el cliente de ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DIRECTORY)
        self.coleccion_documentos = self.chroma_client.create_collection(
            name="coleccion_documentos",
            get_or_create=True
        )

    def generar_embeddings(self, texto):
        # Tokenizar y obtener embeddings usando el modelo de Hugging Face
        inputs = self.tokenizer(texto, return_tensors='pt', truncation=True, padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().tolist()
        return embeddings

    def extraer_texto_pdf(self, ruta_pdf):
        texto = ""
        doc = fitz.open(ruta_pdf)
        for pagina in doc:
            texto += pagina.get_text("text")
        return texto

    def extraer_texto_word(self, ruta_word):
        doc_ejemplo = docx.Document(ruta_word)
        texto = "\n".join([p.text for p in doc_ejemplo.paragraphs])
        return texto

    def cargar_documentos_con_traduccion(self, ruta, doc_id, idioma):
        query_embedding = self.generar_embeddings(doc_id)
        resultados = self.coleccion_documentos.query(
            query_embeddings=query_embedding,
            n_results=5,
            where={"doc_id": doc_id},
            include=["metadatas", "embeddings"]
        )
        if not resultados['metadatas'][0]:
            if ruta.endswith('.pdf'):
                texto = self.extraer_texto_pdf(ruta)
                print(f"Cargando archivo PDF desde: {ruta}")
            elif ruta.endswith('.doc') or ruta.endswith('.docx'):
                texto = self.extraer_texto_word(ruta)
                print(f"Cargando archivo de Word desde: {ruta}")
            else:
                print(f'{ruta} Documento no válido debe ser en formato PDF, Word')

            parrafos = texto.split("\n")

            regexp = re.compile(r'^[0-9\W]+$')
            ids = []
            embeddings = []
            metadatas = []

            for i, (parrafo) in enumerate(zip(parrafos)):
                if not parrafo[0].strip():  # mirar que el parrafo tenga texto
                    print("texto no enviado: " + parrafo[0])
                elif regexp.match(parrafo[0]):  # mirar que el texto del parrafo no sean solo números o carácteres especiales
                    print("Parrafo no traducible: " + parrafo[0])
                else:
                    embeddings_original = self.generar_embeddings(parrafo)
                    ids.append(f"{doc_id}_"+idioma+f"_{i}")
                    embeddings.append(embeddings_original)
                    metadatas.append({"text": parrafo[0], "doc_id": doc_id, "idioma": idioma, "parrafo_index": i})

            self.coleccion_documentos.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            print("Coleccion en idioma: "+idioma+" creada exitosamente.")

    # Soporta .docx y .pdf como documentos de ejemplo por el momento
    # Los documentos de ejemplo a cargar, tienen que empezar por: ({3letras_de_codigo_idioma}_nombre_documento), de momento: CAT, CAS, FRA, ALE, ING
    def cargar_documentos(self):
        for archivo in os.listdir(PATH_DOCS_EJEMPLOS):
            ruta_archivo = os.path.join(PATH_DOCS_EJEMPLOS, archivo)
            idioma = archivo.split("_")[0]
            self.cargar_documentos_con_traduccion(ruta_archivo, archivo, idioma)


if __name__ == "__main__":
    processor = DocumentProcessor()
    processor.cargar_documentos()
