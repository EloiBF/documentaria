fabrIA.cat

TRADUCTOR PPT, WORD Y PDF amb IA especialitzat en la traducció de documents al català

Utilitza Llama 3, a través d'un servidor inference gratuit (limitat) amb Groq.

S'HA D'AFEGIR A la carpeta ARREL DEL PROJECTE UN TXT QUE ES DIU API_KEY.txt amb la clau de la API de groq, es pot aconseguir aquí: https://console.groq.com/keys


Es pot provar amb el document de test/in (tant a través de la web app.py com amb el run_tet_document_translator)



A futur

- Millora disseny web
- Muntar servidor
- Millorar traducció en word i pdf
- Evitar que la IA inclogui cap comentari addicional a part de la traducció (prompting)

- Model de negoci: Traducció d'un document mensual, pla de pagament per més. Extres --> embeddings amb llenguatge sectorial / revisió per traductors professionals
- Client potencial: empreses i administració pública catalana

Avantatge competitiva:
Enfocar-nos amb el català,, que tradueixi perfecte (gpt 4 no ho fa del tot)
S'ha de poder entrenar el model o generar embeddings de varis idiomes al català. (Utilitzant Viquipèdia)
Per cada bloc de text que s'envia, es poden generar exemples a través dels embedding per millorar la precisió.






