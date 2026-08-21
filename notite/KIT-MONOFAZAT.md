# Kit monofazat de monitorizare — listă de cumpărături

Kit independent, separat de instalația trifazată de la Chiril. Măsoară tensiunea
și consumul pe un branșament monofazic existent, loghează local, fără publicare
web. Acces de la distanță prin Tailscale peste 4G.

**Stare: de comandat până la finalul lunii august 2026.**

## Decizia de amplasare

Componentele se despart în două locuri, din cauza gerului de la munte (−20 °C):

```
   AFARĂ (tablou electric)              ÎNĂUNTRU (spațiu încălzit)
   ┌──────────────────────┐             ┌──────────────────────┐
   │ siguranță generală   │             │ mini-UPS             │
   │ (existentă)          │             │ router 4G            │
   │ CONTOR QOLTEC        │  ~~WiFi~~►  │ Raspberry Pi 3B+     │
   │ (DIN, −25…+55 °C)    │  2.4 GHz    │                      │
   └──────────────────────┘             └──────────────────────┘
```

Motivul: Raspberry Pi 3B+ e specificat 0…+50 °C, iar bateriile Li-ion din
mini-UPS și router se degradează permanent dacă sunt încărcate sub 0 °C. O cutie
de policarbonat nu izolează termic — cele ~9 W disipate de electronice ridică
temperatura interioară cu doar ~3 °C față de exterior.

Contorul e Tuya WiFi, deci nu are nevoie de cablu până la Pi.

## Schema electrică

Restul casei se poate închide complet pentru perioade lungi de monitorizare,
iar circuitul kitului rămâne sub tensiune. Deci derivația spre kit se face
**înaintea întrerupătorului general al casei**:

```
BRANȘAMENT MONOFAZIC (L, N, PE)
        │
   [siguranță generală — existentă]
        │
   [CONTOR QOLTEC 50882]  ← se inserează în serie, vede tot ce trece
        │
        ├──────────────────────────────┐
        │                              │
   [RCBO 1P+N 16A/30mA Tip A]     [întrerupător general casă]
        │                              │
   cablu 3×2,5 prin perete        [restul instalației]
        │                          (se închide pe perioade lungi)
   priză aparentă (interior)
        │
   mini-UPS ──┬── 12 V → router 4G
              └── 5 V  → Raspberry Pi 3B+
```

**Ce înseamnă asta pentru măsurare:** cu restul casei închis, contorul vede
doar kitul (~10 W), deci curentul și puterea sunt aproape zero. Tensiunea însă
se citește corect, **nepoluată de consumul propriu** — exact metoda cerută de
EN 50160 pentru calitatea tensiunii la punctul de delimitare. Căderile provocate
de alți consumatori de pe aceeași plecare de joasă tensiune se văd în continuare.

Când casa e pornită, contorul măsoară din nou tot consumul, fără nicio
modificare de cablare. Ambele moduri, aceeași instalație.

Montajul cere electrician: branșamentul se scoate de sub tensiune.

### Trecerea prin perete

Gaura se face lângă tablou, cu **pantă descendentă spre exterior**, cablul se
trage prin tub de protecție, iar ambele capete se etanșează cu silicon. Fără
pantă, apa de ploaie intră în casă pe lângă cablu.


## Coș Farnell — 242,20 lei

Contul e logat, coșul e format. Livrare 34,99 lei (sub pragul de 250 lei fără TVA
pentru livrare gratuită; accesoriile mici la Farnell costă de 3-4× mai mult decât
pe eMAG, deci nu merită completat până la prag).

| Cod | Produs | Preț fără TVA | Stoc |
|---|---|---|---|
| 2842228 | RPI3-MODBP — Raspberry Pi 3 B+, 1 GB RAM | 181,32 lei | 15.238 |
| 2524081 | CBPIBLOX-WHT — carcasă ABS 88,8×64,5×30,5 mm, pentru B+/2B/3B | 25,89 lei | 3.848 |
| | **Subtotal** | **207,21 lei** | |
| | Livrare | 34,99 lei | |
| | **Total** | **242,20 lei** | |

Link-uri: [Pi 3B+](https://ro.farnell.com/raspberry-pi/rpi3-modbp/sbc-board-raspberry-pi-3-model/dp/2842228) ·
[carcasă](https://ro.farnell.com/multicomp-pro/cbpiblox-wht/enclosure-raspberry-pi-b-2b-3b/dp/2524081)

## Coș eMAG — ~423 lei

| Produs | Preț | Observație |
|---|---|---|
| [Contor Qoltec 50882 monofazat Tuya](https://www.emag.ro/contor-de-energie-electric-qoltec-monofazat-cu-ecran-lcd-precizie-clasa-1-0-230v-curent-nominal-5-60-a-conectivitate-wi-fi-tuya-pentru-monitorizare-la-distanta-pe-sina-din-50882/pd/DP3FR5YBM/) | 125,78 lei | ⚠️ era ultimul în stoc |
| [Router 4G 300 Mbps, baterie 5000 mAh, DC 12 V](https://www.emag.ro/router-4g-300mbps-antena-omnidirectionala-transmisie-de-mare-viteza-baterie-5000mah-plug-and-play-lan-wan-alb-qw-6320177/pd/DGLR3RYBM/) | 155,89 lei | |
| [Mini-UPS 10400 mAh, 5 V / 9 V / 12 V](https://www.emag.ro/mini-ups-portabil-10400mah-5v-9v-12v-pentru-routere-camere-difuzoare-negru-futurecircuit100072/pd/DBZ75CYBM/) | 111,32 lei | verifică ieșirea 5 V ≥ 2 A |
| Cablu micro-USB scurt, de calitate | ~20 lei | leagă mini-UPS → Pi |
| Radiatoare Raspberry Pi | ~10 lei | carcasă închisă |
| [RCBO 1P+N 16 A / 30 mA **Tip A** — Noark 107638](https://www.emag.ro/intrerupator-automat-diferential-noark-107638-rcbo-icn-6ka-1-npoli-2-module-caracteristica-b-tip-a-in-16a-in-30ma-noark-107638/pd/D3R9TLMBM/) | 121,18 lei | 2 module, protejează circuitul kitului |
| [Priză aparentă Schuko IP44 cu capac](https://www.emag.ro/priza-schuko-pentru-exterior-ip44-cu-capac-2p-e-16a-montaj-aplicat-maro-65x75x48-mm-pawbol-d3211sbrg1/pd/D251NH3BM/) | 24,25 lei | montaj pe perete, interior |
| Cablu 3×2,5 mm², ~10 m | ~40 lei | de la magazin local, la metru — rolele de 100 m de pe eMAG sunt risipă |
| Tub de protecție + presetupă + silicon | ~25 lei | trecerea prin perete |

**De ce Tip A și nu Tip AC:** mini-UPS-ul e sursă în comutație și poate genera
curent rezidual pulsatoriu continuu, pe care un diferențial Tip AC nu-l detectează
garantat. Alternative mai ieftine, ambele Tip AC — acceptabile, dar inferioare:
[GEYA 1P+N B10, 99 lei](https://www.emag.ro/rcbo-geya-1p-n-b10-30ma-tip-ac-siguranta-automata-diferentiala-cu-protectie-la-supracurent-alb-170/pd/DP4DNM2BM/) ·
[2P 16 A, 62,11 lei](https://www.emag.ro/intrerupator-automat-diferential-2p-16a-30ma-el0009476/pd/D5Z9BHYBM/).

Alternative mini-UPS dacă se termină stocul:
[Rqiurpn 142,25 lei](https://www.emag.ro/mini-ups-portabil-rqiurpn-10400mah-5v-9v-12v-pentru-routere-camere-difuzoare-poe-lan-usb-poate-furniza-energie-simultan-negru-54-mini-ups/pd/DRG5RX2BM/) ·
[Fudisenn 167,54 lei](https://www.emag.ro/ups-portabil-mini-10400mah-5v-9v-12v-fudisennr-potrivit-pentru-telefoane-mobile-difuzoare-camere-de-supraveghere-alarme-de-fum-tablete-ventilatoare-poate-furniza-energie-simultan-negru-a2000467/pd/DFWS673BM/)

## Există deja

- microSD SanDisk High Endurance 64 GB (−25…+85 °C — potrivit)
- cablu Ethernet scurt (Pi → portul LAN al routerului)

## De verificat la fața locului, înainte de comandă

1. **Spațiu în tabloul de afară** — contorul 2 module + RCBO 2 module = **4 module libere**. Dacă nu sunt: [tablou IP65 6 module, 151,46 lei](https://www.emag.ro/tablou-electric-ulisse-150-ip65-neechipat-6-module-sina-din-capac-din-plastic-transparent-150x450x137-mm-fanton-74180/pd/D35NTWYBM/)
2. **Semnal Orange** la locul unde stă routerul (Yoxo merge pe rețeaua Orange)
3. **Curentul maxim al branșamentului** — contorul e 5(60) A; un branșament
   monofazic de 8-10 kW înseamnă 35-45 A, deci intră, dar trebuie confirmat
4. **Priză liberă** în spațiul încălzit, la distanță de WiFi față de contor

## Ce NU cumpărăm și de ce

| Piesă | Motiv |
|---|---|
| Priză schuko pe șină DIN (28,99 lei) | kitul se alimentează prin cablu direct din RCBO, priza stă pe peretele din interior |
| Sursă Farnell T5989DV (37,66 lei) | mini-UPS-ul dă 5 V pe USB |
| PoE HAT | injectorul PoE moare odată cu rețeaua — zero autonomie, exact opusul scopului |
| UPS HAT | ține doar Pi-ul; mini-UPS-ul extern ține și routerul, pe aceeași baterie |
| Raspberry Pi 3 A+ | fără Ethernet; 3B+ permite legătură pe cablu la router |


## Total

| | |
|---|---|
| Farnell (cu livrare) | 242,20 lei |
| eMAG (inclusiv piesele electrice) | ~633 lei |
| **Total kit** | **~876 lei** |
| Abonament Yoxo | ~2-5 €/lună |
| Manoperă electrician | de stabilit |

## Riscul software cunoscut

`monitor_local.py` e scris pentru contorul trifazat (dp6/7/8 = L1/L2/L3). Pentru
Qoltec 50882 monofazat harta DP-urilor e necunoscută. După achiziție:
împerechere în Smart Life → obținere local key → `tinytuya scan` → mapare DP-uri
→ adaptare script. Aceasta este munca software reală a proiectului.
