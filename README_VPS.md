# GameLife Valutazioni — installazione sul tuo VPS

Questo pacchetto contiene **tutto** il necessario: il programma di ricerca prezzi
(con il browser interno che supera Cloudflare di GameLife), il database e
l'interfaccia web protetta da password. Gira **da solo** sul tuo server, **senza
Emergent**.

> ⚠️ **Importante:** serve un **VPS / Cloud Server** (es. *Aruba Cloud Server* o
> qualunque VPS Linux). **Non funziona** su hosting condiviso Aruba (PHP/MySQL):
> lì non è possibile eseguire il browser necessario a leggere i prezzi.

---

## Cosa ti serve
- Un VPS Linux (Ubuntu 22.04 consigliato) con almeno **2 GB di RAM**.
- Accesso SSH al VPS (utente root o sudo).
- Il tuo dominio/sottodominio se vuoi l'indirizzo tipo `https://valutazioni.tuosito.it`
  (facoltativo ma consigliato).

---

## 1) Installa Docker sul VPS
Collegati in SSH ed esegui:

```bash
curl -fsSL https://get.docker.com | sh
```

Verifica:
```bash
docker --version
docker compose version
```

## 2) Copia il progetto sul VPS
Carica l'intera cartella del progetto (quella che contiene `Dockerfile`,
`docker-compose.yml`, le cartelle `backend/` e `frontend/`) nel VPS, ad esempio in
`/opt/valutazioni`. Puoi usare `scp`, `git clone`, o l'upload del tuo provider.

## 3) Imposta password e chiave segreta
Apri `docker-compose.yml` e modifica **due valori** dentro `environment:`:

- `APP_PASSWORD` → la password iniziale per entrare (poi la cambi dall'app, in *Impostazioni*).
- `SECRET_KEY` → una stringa lunga e casuale (serve a firmare gli accessi).
  Generane una con:
  ```bash
  openssl rand -base64 32
  ```

## 3a) Configura le fonti di valutazione
Crea un file `.env` accanto a `docker-compose.yml`. Inserisci le credenziali qui,
mai in `docker-compose.yml` o nel codice: il file è locale al server e ignorato da Git.

Per le valutazioni CeX/WeBuy Italia tramite Apify:

```dotenv
APIFY_API_TOKEN=il-tuo-token-apify
```

Per gli annunci eBay automatici servono le credenziali **Production** da
[developer.ebay.com](https://developer.ebay.com/):

```dotenv
EBAY_CLIENT_ID=il-tuo-client-id
EBAY_CLIENT_SECRET=il-tuo-client-secret
EBAY_MARKETPLACE_ID=EBAY_IT
```

Puoi inserirle tutte nello stesso `.env`. Non copiare `backend/.env` nell'immagine:
Docker esclude i file `.env` dal build e Compose passa i token al container a runtime.
Il token Apify avvia lo scraper CeX Italia e legge il valore `trade_in_cash`.
eBay restituisce articoli usati a prezzo fisso, cioè Compralo Subito.

GameLife è escluso dalla ricerca per default (`GAMELIFE_ENABLED=false`) perché
il server di produzione può essere bloccato dal sito. La ricerca continua con
CeX ed eBay e la schermata indica che GameLife è disattivato. Riattivalo solo se
l'accesso torna disponibile e autorizzato, impostando `GAMELIFE_ENABLED=true`
nel `.env` del VPS. Per contenere l'uso del piano Apify gratuito, CeX viene
interrogato una sola volta per ogni ricerca, usando il titolo inserito senza
varianti aggiuntive.

## 4) Avvia
Dalla cartella del progetto:

```bash
docker compose up -d --build
```

La prima build scarica tutto e prepara l'interfaccia: può richiedere alcuni minuti.
Controlla che sia partito:

```bash
docker compose ps
docker compose logs -f app   # Ctrl+C per uscire dai log
```

## 5) Apri l'app
Vai su: **`http://IP_DEL_TUO_VPS:8001`**
Inserisci la password (`APP_PASSWORD`) → sei dentro. 🎉

- La cronologia e i prezzi vengono salvati nel database (volume `mongo_data`), quindi
  restano anche dopo un riavvio.
- Per **cambiare la password** quando vuoi: nell'app tocca l'icona ⚙️ *Impostazioni*.

## Aggiornare una versione già pubblicata
La cartella locale contiene la nuova versione. Sul VPS aggiorna i file nella stessa
directory dove si trova il `docker-compose.yml` pubblicato, senza eliminare il volume
MongoDB e senza sovrascrivere il `.env` del server.

1. Prima crea un backup del database, dal VPS e dentro la cartella del progetto:
  ```bash
  docker compose exec -T mongo mongodump --db gamelife --archive --gzip > backup-gamelife-$(date +%F).archive.gz
  ```
2. Dal computer che contiene questa copia del progetto, invia i file aggiornati.
  Sostituisci `utente` e `IP_VPS` con i tuoi dati:
  ```bash
  rsync -av \
    --exclude='.git/' \
    --exclude='.env' \
    --exclude='**/.env' \
    --exclude='**/.env.*' \
    --exclude='**/node_modules/' \
    --exclude='**/.expo/' \
    --exclude='**/.metro-cache/' \
    ./ utente@IP_VPS:/opt/valutazioni/
  ```
  Se il progetto sul VPS non è in `/opt/valutazioni`, usa la sua directory effettiva.
  Non aggiungere `--delete`: così non elimini per errore file o configurazioni del server.
3. Sul VPS verifica che il suo `.env` contenga i token `APIFY_API_TOKEN` e, se
  configurate, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` ed `EBAY_MARKETPLACE_ID`.
4. Ricostruisci e ricrea solo l'applicazione:
  ```bash
  docker compose up -d --build app
  docker compose ps
  docker compose logs --tail=100 app
  ```

Il comando non rimuove MongoDB né il volume `mongo_data`: cronologia, password e dati
salvati restano sul server. Dopo il riavvio prova l'accesso e una ricerca prima di
considerare concluso l'aggiornamento.

---

## 6) (Consigliato) Dominio + HTTPS
Per avere `https://valutazioni.tuosito.it` (necessario se il pulsante è su un sito
HTTPS), metti **Nginx** davanti all'app come reverse proxy e attiva un certificato
gratuito Let's Encrypt.

Esempio rapido (Ubuntu):
```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
```

Crea `/etc/nginx/sites-available/valutazioni` con:
```nginx
server {
    server_name valutazioni.tuosito.it;
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Poi:
```bash
sudo ln -s /etc/nginx/sites-available/valutazioni /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d valutazioni.tuosito.it
```
Ricordati di puntare il record DNS `valutazioni` all'IP del VPS.

> Suggerimento sicurezza: dopo aver messo Nginx, puoi far ascoltare l'app solo in
> locale cambiando in `docker-compose.yml` la riga porte in
> `"127.0.0.1:8001:8001"` e ricreando con `docker compose up -d`.

---

## Comandi utili
```bash
docker compose restart app     # riavvia l'app
docker compose down            # ferma tutto
docker compose up -d --build   # ricostruisce dopo modifiche
docker compose logs -f app     # guarda i log
```

## Aggiungere il pulsante "Valutazioni" al sito
Vedi il file **`prestashop-valutazioni-button.html`**: contiene il codice del
pulsante dorato e le istruzioni per inserirlo nel menù di PrestaShop, puntando
all'indirizzo del tuo VPS (es. `https://valutazioni.tuosito.it`).
