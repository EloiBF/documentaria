DocumentarIA.cat

INCLOURE FITXER APY_KEY.txt al contenidor agents/

Versió MVP 1.7

Estructura simplificada Docker, 3 contenidors:
- website --> s'encarrega de carregar el front i gestionar crides a les API de agents (traducció, generar fitxers etc)
- agents --> APIs connectades amb la IA per generar fitxers (poden fer crides a embedding)
- embedding --> generació de DB de embeddings (actualment sqlite), i búsqueda d'exemples per donar contingut contextual als prompts

website funciona amb django. agents i embedding son APIs amb flask (app.py controla la API)



Next steps per arribar a la MVP 2.0

- Configurar embeddings en frontal per poder pujar fitxers d'exemple cada cop que s'executa un servei
- Configurar serveis per incloure embeddings en el prompt (traducció i generació de fitxers de moment)
- Mirar seguretat web per pujar a servidor
- Millorar configuració variabes i rutes (arxiu config o com sigui millor)
- Claus API, de moment free version groq -- veure si es pot escalar de forma gratuita
- Millora de les funcionalitats:
    - afegir possibilitat de descàrrega en csv o xlsx de resultats d'anàlisi
    - modificar noms dels fitxers descarregats (generar amb timestamp al nom pero treure-ho en la descàrrega) 
    - millorar generació de fitxers (prompting més avançat, valorar langchain)

