# Tuya munte — contor trifazat + centrală electrică

Extragere date local (LAN) și prin cloud, log CSV pentru reclamația de calitate
tensiune. Dosarul reclamației (nr. înregistrare, ATR, măsurători invocate,
termene): [dosar/RECLAMATIE.md](dosar/RECLAMATIE.md).

## Device-uri

| Nume | Device ID | IP local | Protocol |
|---|---|---|---|
| Contor Chiril (trifazat) | `bf8506716a850a2588yqqf` | 192.168.1.230 | 3.4 |
| Centrala munte | `bff7d8c541f12e011b5csd` | 192.168.1.214 | 3.5 |

Config în `config/`: `tinytuya.json` (chei cloud, regiune `eu` = Central Europe),
`devices.json` (local keys + IP + versiune). Ambele generate — nu edita manual;
`*.json.example` din același folder arată forma. IP-urile sunt DHCP — dacă se
schimbă, rulează `python -m tinytuya scan` **din `config/`** (scrie `devices.json`
în directorul curent) sau fă rezervări DHCP în router.

## Structura repo

| Cale | Conținut |
|---|---|
| `src/` | scripturile Python (monitor, paznic, generator de pagină) |
| `win/` | rulare pe Windows: wrapperele + `install.ps1` (Scheduled Tasks) |
| `pi/` | rulare pe Raspberry Pi: `install.sh` + unități systemd |
| `config/` | `devices.json`, `tinytuya.json` (**secrete**, ignorate) + exemplele lor |
| `data/` | CSV-urile zilnice (contor, centrală, paznic) — locale, ignorate de git |
| `logs/` | jurnalele wrapperelor și watchdog-ului — locale, ignorate de git |
| `dosar/` | **PII**: reclamația, ATR, pozele instalației, inventarul — ignorat de git |
| `notite/` | documentație de lucru: comenzi Tuya, instalare Pi, kit monofazat |
| `docs/` | `index.html` generat — sursa pentru GitHub Pages (public) |
| `outputs/` | artefacte de scraping/lucru — locale, ignorate de git |

## Scripturi

| Script | Ce face |
|---|---|
| `python src/monitor_local.py` | contor event-driven + centrală la 10s → `data/contor_YYYYMMDD.csv`, `data/centrala_YYYYMMDD.csv` |
| `python src/monitor_cloud.py` | contor prin cloud la 10s → `data/cloud_log_YYYYMMDD.csv`; merge de oriunde |
| `python src/paznic.py` | comută P1/P2/P3 sub plafon, citind CSV-ul monitorului → `data/paznic_YYYYMMDD.csv` |
| `python src/gen_pagina.py` | regenerează `docs/index.html` (pagina publică de probe) din `data/contor_*.csv` |

Rulare non-stop: pe Windows `pwsh -File win\install.ps1` (Scheduled Tasks), pe
Raspberry Pi `./pi/install.sh` (systemd) — vezi [notite/PI.md](notite/PI.md).

## Comportament contor (important)

- `status()` local întoarce doar DP 1 (index) și DP 16 (switch).
- Fazele (DP 6/7/8 = A/B/C) vin **doar push**, în rafală, pe programul intern
  al contorului — `updatedps` e ignorat (testat: 12 cereri / 3 min / 0 răspunsuri).
- Cadență observată: legată de incrementul de index (~0,01 kWh) — rar în gol,
  la câteva secunde sub sarcină mare. Suficient pentru ANRE (EN 50160 lucrează
  pe medieri de 10 minute).
- Loggerul local ține socket persistent + heartbeat la 9s și scrie un rând CSV
  la fiecare rafală completă (toate 3 fazele).

## Decodare DP faze (local, base64, 8 octeți)

| Octeți | Semnificație | Factor |
|---|---|---|
| 0–1 | Tensiune (V) | ÷10 |
| 2–4 | Curent (A) | ÷1000 |
| 5–7 | Putere activă (W) | ×1 |

Verificat: `CRoACaYAAck=` → 233,0 V / 2,47 A / 457 W.
Prin **cloud** fazele vin alt format: JSON `{"voltage","electricCurrent","power"(kW)}`.
Index: DP `forward_energy_total` ÷ 100 = kWh.

## DP-uri centrală (local)

`1`=switch, `2`=mode, `3`=set ACM °C, `4`=ACM actual, `5`=set încălzire,
`6`=temp actuală, `111`=stare (stand_by/…), `113`=regim (heat/…).
DP-urile 101–124 apar doar local (nu-s expuse în cloud); se loghează în coloana `extra`.

## Rețea

- Laptopul NU trebuie pe 2.4GHz — merge de pe 5GHz, contează doar același subnet.
- Doar device-urile Tuya cer 2.4GHz pentru ele.
- Semnal contor: -40dBm (bun; era -81dBm inițial). Loggerul se reconectează
  singur dacă totuși pică legătura.

## Limite ANRE / EN 50160 (referință reclamație)

Nominal 230 V ±10% → **207–253 V** (absolut: 195,5–253,0 V).

Observat în **capturi din app Smart Life** (2026-08-12, 19:01–20:08 — dovadă slabă):
- sub sarcină (~5 kW): faza A 178,2 V, faza B 175,2 V — **sub limită**
- în gol: faza C 258,5 V — **peste limită**

**Reprodus și depășit de logger în CSV (dovadă tare):**

| Data/ora | Eveniment | Valori |
|---|---|---|
| 13.08 12:34 | supratensiune în gol | C = **254,8 V** |
| 13.08 20:20 | sub sarcină 6,8 kW | A **179,3 V**, B **176,2 V** — sub limita absolută |
| 14.08 09:51 | ardere centrală (log cloud) | B **173,5 V** la 28,0 A |
| 14.08 09:57 | sarcină 12,6 kW | **toate 3 fazele sub 207 V** (201,0/197,4/205,0), 31,9 A pe B |
| 14.08 10:09 | **record negativ**, doar 3,7 kW | **B = 153,4 V, A = 156,0 V** — cu 42 V sub limita absolută |
| 14.08 10:52 | supratensiune în gol | C = **256,9 V** |

Pendulare 153→257 V în aceeași dimineață. Istoricul există și în cloud-ul Tuya
(~7 zile, API device logs) — probă independentă de CSV-ul local.

Tipar de asimetrie (fazele încărcate cad, cea neîncărcată urcă) = probleme pe
nul / branșament subdimensionat. Periculos pentru aparate. CSV-urile cu
timestamp sunt proba.

## De făcut

- [ ] Reset Key pe iot.tuya.com (secretul a apărut în screenshot) → actualizează `config/tinytuya.json`
- [ ] Rezervări DHCP pentru .230 și .214 în router
- [ ] Pentru logging non-stop: rulează `src/monitor_local.py` pe un calculator mereu pornit la munte
