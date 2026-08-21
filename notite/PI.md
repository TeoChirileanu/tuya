# Instalare pe Raspberry Pi (înlocuiește laptopul)

Scop: monitorizare non-stop la Chiril, fără laptop. Pi lângă router, cablu
Ethernet, alimentare din priză, SSH de la distanță pentru administrare.

## 1. Hardware de comandat

| Piesă | De ce |
|---|---|
| **Raspberry Pi 3 A+** sau **3B+** | 3B+ are Ethernet nativ (recomandat); 3 A+ e mai ieftin dar doar WiFi |
| **Sursă 5V / 2,5A micro-USB** | obligatorie — routerul Archer AX10 NU are port USB |
| **microSD 32GB „high endurance"** | scrierile continue de log uzează cardurile obișnuite |
| Carcasă | opțional |
| Cablu Ethernet | Pi → port LAN router |

## 2. Sistem de operare

Raspberry Pi OS **Lite** (64-bit) — fără desktop. În Raspberry Pi Imager,
la rotița de setări, activează din start: hostname `pi-chiril`, **SSH cu cheie
publică** (lipește cheia de pe Legion), utilizator, fus orar Europe/Bucharest.

## 3. Rețea

1. Router → **DHCP → Rezervare adresă IP**: leagă MAC-ul Pi-ului de o adresă
   fixă (ex. `192.168.1.10`), ca la contor și centrală.
2. Verifică pe pagina **Internet** a routerului adresa WAN. Dacă începe cu
   `10.` sau `100.64.` ești în spatele CGNAT și port forwarding NU funcționează
   (atunci singura variantă e tunel invers printr-un VPS).
3. Router → **NAT Forwarding → Virtual Servers**: port extern `2222` → intern
   `22` pe IP-ul Pi-ului. Portul nestandard reduce zgomotul de scanări.
4. Router → **DDNS**: activează TP-Link DDNS (gratuit) → obții ceva de forma
   `chiril.tplinkdns.com`. Necesar fiindcă IP-ul public de la Digi e dinamic.

## 4. Securizare SSH (obligatoriu — portul e expus pe internet)

În `/etc/ssh/sshd_config`:
```
PasswordAuthentication no
PermitRootLogin no
KbdInteractiveAuthentication no
```
apoi `sudo systemctl restart ssh`. În plus:
```bash
sudo apt-get install -y fail2ban    # blochează IP-urile care încearcă la nesfârșit
```
Autentificare doar cu cheie. Fără asta, un port SSH expus e găsit de scanere în
câteva ore.

## 5. Instalare scripturi

> **Dacă Pi-ul are deja repo-ul clonat de dinainte de reorganizare** (CSV-urile
> stăteau direct în `/opt/tuya`), la primul `git pull` mută-le, altfel pagina de
> probe pierde istoricul:
> ```bash
> sudo systemctl stop tuya-monitor tuya-paznic   # ÎNTÂI: altfel scriu mai departe
> cd /opt/tuya && git pull                       #        în vechea cale (fd deschis)
> mkdir -p data logs config
> mv -n *.csv data/ 2>/dev/null; mv -n health.log logs/ 2>/dev/null
> mv -n devices.json tinytuya.json config/ 2>/dev/null
> ./pi/install.sh          # rescrie unitatile systemd (src/) si repornește serviciile
> ```

```bash
sudo git clone https://github.com/TeoChirileanu/tuya.git /opt/tuya
sudo chown -R $USER:$USER /opt/tuya
# copiază devices.json și tinytuya.json de pe laptop (NU sunt în git):
#   ssh pi-chiril "mkdir -p /opt/tuya/config"
#   scp config/devices.json config/tinytuya.json pi-chiril:/opt/tuya/config/
cd /opt/tuya && ./pi/install.sh
```

Instalează tinytuya, pune serviciile systemd și le pornește:

| Serviciu | Rol |
|---|---|
| `tuya-monitor` | citește contorul + centrala, scrie CSV (singura conexiune la contor) |
| `tuya-paznic` | comută P1/P2/P3 sub plafonul de 11 kW, citind CSV-ul monitorului |
| `tuya-publish.timer` | din oră în oră regenerează pagina și o publică pe GitHub Pages |

systemd înlocuiește watchdog-ul de pe Windows: `Restart=always` repornește
automat orice serviciu căzut, inclusiv după pană de curent.

## 6. Publicare automată

Pi-ul trebuie să poată face push. Deploy key cu drept de scriere, limitată la
acest repo (nu token de cont):
```bash
ssh-keygen -t ed25519 -C "pi-chiril" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub     # -> GitHub -> repo Settings -> Deploy keys -> Add, bifează Allow write
git -C /opt/tuya remote set-url origin git@github.com:TeoChirileanu/tuya.git
```
De atunci, pagina de probe se actualizează singură din oră în oră.

## 7. Utilizare de pe Legion

```bash
ssh -p 2222 teo@chiril.tplinkdns.com        # administrare
journalctl -u tuya-monitor -f               # log live
tail -f /opt/tuya/data/contor_$(date +%Y%m%d).csv
```

Pentru **citit măsurătorile nu ai nevoie de SSH** — pagina publică se
actualizează automat: <https://teochirileanu.github.io/tuya/>

## 8. Menajarea cardului SD

Serviciul rulează cu `TUYA_CENTRALA_POLL=30` (în loc de 10s pe laptop), adică
de 3 ori mai puține scrieri. Dacă vrei și mai puțin, pune 60 în
`/etc/systemd/system/tuya-monitor.service`.
