import os
from groq import Groq


# Funcions específiques per transcriure àudio


def transcribe_audio(audio_file, output_path , language, add_prompt='', model='distil-whisper-large-v3-en', api_key_file='API_KEY.txt'):
    try:
        # Inicialitza el client de Groq
        with open(api_key_file, 'r') as fichero:
            api_key = fichero.read().strip()
        client = Groq(api_key=api_key)

        # Verifica que el fitxer d'àudio existeix
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"El fitxer d'àudio {audio_file} no existeix.")

        # Obre i llegeix el fitxer d'àudio
        with open(audio_file, "rb") as file:
            # Crea la transcripció del fitxer d'àudio
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_file), file.read()),  # Nom i contingut del fitxer d'àudio
                model=model,  # Model utilitzat per a la transcripció
                prompt='Transcribe in the same language of audio file',  # Prompt addicional opcional
                response_format="json",  # Format de la resposta (en aquest cas, JSON)
                language=None if language == "auto" else language,  # Defineix l'idioma o None per a detecció automàtica
                temperature=0.1  # Temperatura per a la generació de text (ajust opcional)
            )
            # Retorna el text transcrit
            transcribed_text = transcription.text.strip()

            # Guarda la transcripció en un fitxer .txt
            base_filename = os.path.splitext(audio_file)[0]
            text_filename = f"{base_filename}.txt"
            with open(text_filename, "w") as text_file:
                text_file.write(transcribed_text)
            
            return transcribed_text
    
    except Exception as e:
        raise RuntimeError(f"Error durant la transcripció: {e}")
