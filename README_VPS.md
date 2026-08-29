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
