from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import logging
from translator import traducir_doc

# Configurar el logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear la aplicación FastAPI
app = FastAPI()

# Modelo para la solicitud de traducción
class TranslationRequest(BaseModel):
    file_path: str
    result_file_path: str
    origin_language: str
    language: str
    color_to_exclude: str = None
    add_prompt: str = None

# Endpoint para la traducción
@app.post("/translate")
def translate_file(request: TranslationRequest):
    try:
        logger.info(f"Starting translation: {request.file_path} to {request.result_file_path} from {request.origin_language} to {request.language}")
        
        # Eliminar el archivo de salida si ya existe
        if os.path.exists(request.result_file_path):
            os.remove(request.result_file_path)

        # Llamar a la función de traducción
        traducir_doc(
            input_path=request.file_path,
            output_path=request.result_file_path,
            origin_language=request.origin_language,
            destination_language=request.language,
            extension=os.path.splitext(request.file_path)[1].lower(),
            color_to_exclude=request.color_to_exclude,
            add_prompt=request.add_prompt
        )

        return {"status": "success", "message": "Translation completed successfully."}
    
    except Exception as e:
        logger.error(f"Error during translation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during translation: {str(e)}")
