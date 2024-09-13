DocumentarIA.cat

Funcionalitats:
TRADUCCIÓ, EDICIÓ I TRANSCRIPCIÓ AMB IA

Utilitza Llama 3, a través d'un servidor inference gratuit (limitat) amb Groq.

!!!! S'HA D'AFEGIR A la carpeta ARREL DEL PROJECTE UN TXT QUE ES DIGUI API_KEY.txt amb la clau de la API de groq, es pot aconseguir la clau aquí gratis: https://console.groq.com/keys


Es pot provar la web amb els document de test/in
Per engegar la web, fem run al app.py


A futur

- Ordenar codi per unificar "lectura" i "modificació" de documents. Tenir funcions úniques de processat de text que llegeixi per "blocs" o el total del contingut. Actualment el processat de text està duplicat
- Millora disseny web - sobretot pàgines de formulari, progrés i resultat
- Muntar funció que admeti la funcionalitat amb varis fitxers (seria fer un bucle for de les funcions actuals doc_xxx)
- Muntar servidor i infraestructura per poder escalar
- Veure quin proveidor de models IA fer servir, actualment Groq. Veure si podem fer servir models 
- Veure possibilitat de fer LangChain -- millorar catala
- Muntar log in usuaris i BDD per guardar dades
- Muntar BDD per guardar resultats per cada usuari. Guardar documents pot ser molt extensiu en memòria... veiem com ferho.
- Muntar pàgina per resultats del servei de Extract. De moment que sigui una taula que es pugui descarregar en excel.
- Assegurar que la traducció agafa tots els elements, gràfics etc dels documents

- Model de negoci: Oferim prova de serveis amb un límit per usuari, un o pocs fitxers. Després pla de pagament mensual per ús limitat o enterprise per ús a gran escala
- Client potencial: empreses i administració pública catalana







