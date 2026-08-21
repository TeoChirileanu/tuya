# Comenzi Tuya — referință tehnică (citire ȘI scriere)

Cu **local key** (din `devices.json`) se pot trimite comenzi direct pe LAN, fără
cloud — protocolul Tuya local permite scrierea oricărui DP writable. Prin cloud
avem doar **Read** (așa e permisiunea proiectului). Deci: monitorizarea merge de
oriunde, comenzile doar din rețeaua locală.

## Cum arată o comandă (tinytuya)

```python
import json, tinytuya

devices = {d["id"]: d for d in json.load(open(r"c:\repos\tuya\config\devices.json"))}

def device(dev_id):
    d = devices[dev_id]
    return tinytuya.Device(d["id"], d["ip"], d["key"], version=float(d["version"]))

centrala = device("bff7d8c541f12e011b5csd")   # v3.5 @ 192.168.1.214
contor   = device("bf8506716a850a2588yqqf")   # v3.4 @ 192.168.1.230

centrala.set_value(3, 45)       # ACM la 45°C
centrala.set_value(106, "P1")   # treaptă de putere P1
centrala.set_value(2, "eco")    # mod ECO
status = centrala.status()      # citire
```

## Centrală JNOD BM326E — DP-uri (bff7d8c541f12e011b5csd)

Confirmate prin corelarea log-urilor cu ecranele din app (pozele `dosar/setari-*.jpeg`):

| DP | Semnificație | Tip / valori | R/W | Comandă exemplu |
|---|---|---|---|---|
| 1 | Pornit/oprit centrală | bool | **RW** | `set_value(1, True/False)` |
| 2 | Heating Mode | `comfortable` / `eco` | **RW** | `set_value(2, "eco")` |
| 3 | ACM setpoint (DHW Temp. Set) | int, 30–55°C | **RW** | `set_value(3, 43)` |
| 4 | ACM temperatură actuală | int °C | RO | — |
| 5 | Încălzire setpoint (HeatingTemp. Set) | int, 30–80°C | **RW** | `set_value(5, 45)` |
| 6 | Tur încălzire actual | int °C | RO | — |
| 13 | heat_sink_mode | bool | RW [?] | writable (testat no-op); rol neconfirmat — nu umbla |
| 17 | Unitate temperatură | `c` / `f` | RW | `set_value(17, "c")` |
| 20 | Cod eroare (fault) | int, 0 = OK | RO | — |
| 101 | Variabilă internă auto-gestionată (observat 10/15/30; centrala o rescrie singură) | int | RW* | scrierea se acceptă dar controllerul o suprascrie — nu e canal de limitare putere |
| 103 | **Limită maximă ACM** (probabil — coincide cu maximul sliderului DHW din app, 55°C) | int | **RW** | `set_value(103, 55)`; testat 55→54→55 OK |
| 105 | Temperatură internă (probabil radiator triac/heat-sink — crește în timpul arderii, 21→31°C) | int | RO* | acceptă write dar e senzor — nu scrie |
| 106 | **Power Set** | `P1` / `P2` / `P3` | **RW** | `set_value(106, "P2")` |
| 107 | Running Mode | `heating` / `bathroom`(DHW) / `auto` | **RW** | `set_value(107, "auto")` |
| 108 | Stare regim curent | ex. `heating` | RO | — |
| 111 | Stare elemente | `stand_by` / `OFF` / … | RO | — |
| 112 | Stare mașină de stări elemente | `OFF` / `stand_by` / `heat` | RO | oglindește ciclul de reglaj |
| 113 | Regim | `heat` | RO [?] | — |
| 109/110/104/123/124 | [?] necunoscute (109=23, 110=4, 104=0, 123=false, 124=1 — constante) | — | RW* [?] | acceptă no-op write; valori niciodată văzute schimbându-se — posibil parametri service, NU modifica |

*Notă test 13.08: toate DP-urile nesigure ACCEPTĂ scrieri locale (protocolul nu
refuză nimic) — deci prudența e la noi, nu în firmware. Testat fără efecte
adverse: no-op pe toate, dp101 comutat+revert, dp103 55→54→55.

`Temp. Differ Set` (diferențial 5–30°C, în app) — DP-ul exact încă neidentificat,
probabil unul din 109/110. Se confirmă schimbând valoarea în app și urmărind log-ul.

## Contor trifazat — DP-uri (bf8506716a850a2588yqqf)

| DP | Semnificație | Tip | R/W | Notă |
|---|---|---|---|---|
| 1 | Index total | int, ÷100 = kWh | RO | |
| 6 / 7 / 8 | Faza A / B / C | base64: V÷10, mA, W | RO | vin doar push, la incrementul indexului |
| 16 | **Releu / întrerupător intern** | bool | **RW** | ⚠️ vezi mai jos |

> ⚠️ **dp16 = releul din contor. `set_value(16, False)` TAIE CURENTUL LA TOATĂ
> CASA.** Repornirea cere `set_value(16, True)` — dar dacă WiFi-ul cade odată cu
> curentul (router nealimentat), comanda de repornire nu mai are pe unde ajunge →
> deplasare fizică la contor. **INTERZIS PERMANENT — confirmat de proprietar
> (13.08.2026): a pățit-o, a trebuit resetare fizică de la contor.**

## Reguli de execuție (ce fac / ce nu fac)

1. **Execut comenzi doar la cererea ta explicită**, una câte una, cu confirmare
   înainte pentru orice schimbă starea (temperaturi, moduri, on/off).
2. **Nu ating niciodată** dp16 (contor) și nu opresc centrala iarna fără
   confirmare dublă (risc îngheț instalație).
3. **P3 pe dp106**: doar test scurt (10–15 min) cu monitorul pornit — nominal
   26 kW pe branșament de 12 kW / 25A (vezi RECLAMATIE.md).
4. Orice comandă apare în **operation record** din app Smart Life — nimic nu e
   invizibil pentru tine.
5. Identificarea DP-urilor [?] se face pasiv: schimbi tu ceva din app / de pe
   panou, eu corelez cu log-ul. Fără scrieri experimentale oarbe pe DP-uri
   necunoscute — pot fi parametri de service.

## Setare putere maximă 30–100% (din PANOU, nu din app!)

Descoperită în video-urile de service JNOD (canal YouTube @xiehuihong, extrasă
cadru cu cadru din [Max Power setting](https://youtu.be/WAOWLE287IM)):

1. **Oprește centrala** din buton (standby — pe display rămân doar 2 puncte)
2. Apasă (lung) **butonul de meniu** (mijloc) → display: `PP:00` (cere parolă)
3. Cu **▲/▼** introdu parola **11** → `PP:11`, confirmă cu butonul de meniu
4. Navighează parametrii până la **`P`** → afișează `P100` (100%)
5. Cu **▲/▼** setează procentul dorit, pași de 1%, interval **30–100%**
6. Ieși cu butonul de pornire

**Pentru branșamentul de 12 kW:** setează **P 40** (=10,4 kW) sau **P 45**
(=11,7 kW) → apoi **P3 din app** devine sigur: sarcină echilibrată pe 3 faze,
~15–17 A/fază, sub C25 și sub puterea aprobată. Configurația optimă.

Alte video-uri utile de pe canal: [P1/P2/P3](https://youtu.be/yhoxHd7QS40) ·
[Temp differ](https://youtu.be/w47RFDziFik) · [Heating element temp sensor](https://youtu.be/rICPRdRtsT8) ·
[Anti-Legionella](https://youtu.be/XhEQRFkqB-w) · [Instalare](https://youtu.be/JngaftK4-rU) ·
[Restore defaults](https://youtu.be/bZQAfB4Mh3s)

## Comenzi utile gata de dat (exemple concrete)

| Vrei | Comanda mea |
|---|---|
| „setează ACM la 40" | `centrala.set_value(3, 40)` |
| „treci pe eco peste noapte" | `centrala.set_value(2, "eco")` |
| „doar apă caldă, fără calorifere" | `centrala.set_value(107, "bathroom")` |
| „încălzire mai domoală, tur 40" | `centrala.set_value(5, 40)` |
| „test P3 15 minute" | `set_value(106, "P3")` → monitor → revert `"P2"` |
| „oprește centrala" | `centrala.set_value(1, False)` (cu confirmare) |
