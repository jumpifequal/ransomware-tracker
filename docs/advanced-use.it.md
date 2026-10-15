[README](../README.it.md) · [Esempi d'uso](examples.it.md) · [Uso avanzato](advanced-use.it.md) · [Prompt e comandi](prompts-and-commands.md) (in inglese)

# Uso avanzato

## Forzare una modalità o una fonte

La tua istruzione prevale sull'instradamento automatico. Esempi: "Usa la modalità Trend e solo i dati storici." "Interroga solo Ransomfeed e RansomLook." Il coverage gate controlla le fonti dell'ambito di minaccia selezionato.

## Interrogare lo storico incluso, offline

```bash
python scripts/historical_query.py claims --country IT --start 2024-01-01 --end 2024-12-31 --group-by quarter
python scripts/historical_query.py claims --group-by sector
python scripts/historical_query.py wallets --family <nome>
python scripts/historical_query.py eurepoc --keyword <testo> --country <testo> --start <YYYY-MM-DD> --end <YYYY-MM-DD>
python scripts/historical_query.py repository --strain <nome> --sector <testo> --location <testo> --start-year 2020 --end-year 2024
```

> **Controlla le etichette dei paesi.** In `historical_query.py` il filtro `--country` confronta il testo senza distinguere maiuscole e minuscole, quindi un codice breve può corrispondere a più etichette. Le rivendicazioni incluse mescolano anche codici e nomi completi. Per esempio, raggruppando per paese le rivendicazioni del 2025 compaiono sia `AT` sia `Austria`. Una prova con `--country IT --group-by country` su tutti gli anni ha trovato `IT` (76), `Italy` (1) e anche `Kuwait` e `Switzerland` (1 ciascuno), perché questi nomi contengono le lettere "it". Prova entrambe le forme, raggruppa per paese per vedere le etichette e leggi il risultato. In `filter_records.py`, `--country` è un confronto esatto sul valore normalizzato.

## Quando una fonte è bloccata o irraggiungibile

Stampa la richiesta esatta, così l'agente può ripeterla con un altro canale di trasporto:

```bash
python scripts/request_manifest.py ransomware.live month <YYYY> <M>
```

*Output reale (abbreviato):* `{"ok":true,"source":"ransomware.live","operation":"month","url":"https://api.ransomware.live/v2/victims/2026/9", ... "transport":"native-web-fallback", ...}`

Costruisci le query di recupero tramite indice di ricerca:

```bash
python scripts/search_index_fallback.py ransomware.live victim --victim "Example Corp"
```

*Output reale (abbreviato):* `{"ok":true,"source":"ransomware.live", ... "queries":["site:ransomware.live \"Example Corp\"", ...],"channel":"Search index", ...}`

Diagnostica la rete. Un resolver DNS pubblico è solo una sonda. Non viene mai usato per instradare le richieste.

```bash
python scripts/diagnose_source.py ransomware.live month <YYYY> <M>
python scripts/network_diagnostics.py api.ransomware.live --probe-public-dns
```

## Vedere il coverage gate rifiutare una conclusione anticipata

Il gate legge dallo standard input un registro JSON. Questo registro contiene una sola fonte, quindi il gate segnala le lacune ed esce con codice 3.

```bash
echo '[{"source":"ransomware.live","attempted":true,"state":"OK","attempted_paths":["api"],"available_paths":["api","web_api"],"exhausted":false}]' \
  | python scripts/coverage_gate.py
```

*Output reale (abbreviato):* `{"ok":false,"scope":"ransomware","required_sources":["ransomware.live","Ransomfeed", ...],"gaps":[{"source":"ransomware.live","reason":"safe retrieval paths remain","untried_paths":["web_api"]},{"source":"Ransomfeed","reason":"missing ledger entry"}, ...]}`

## Costruire la tabella di stato dalle prove

```bash
echo '[{"source":"ransomware.live","attempted":true,"state":"OK","channel":"API","note":"data acquired","evidence":{"success":true}},
       {"source":"Cybernews","attempted":true,"state":"BLOCKED","channel":"Web","note":"HTTP 403","evidence":{"http_status":403}},
       {"source":"VULONE","attempted":false}]' | python scripts/source_status.py
```

*Output reale:*

```json
[{"Source":"ransomware.live","Status":"🟢 OK","Channel":"API","Note":"data acquired"},{"Source":"Cybernews","Status":"🟠 BLOCKED","Channel":"Web","Note":"HTTP 403"}]
```

La terza fonte non è stata tentata e non è rilevante per questo registro, quindi non genera una riga. Uno stato senza prove dell'esecuzione corrente viene rifiutato.

## Attori, settori e aggregati

- **Identità degli attori.** `scripts/actor_identity.py` ha i comandi `resolve` e `compare`, che leggono prove in JSON dallo standard input. Un nome senza alias verificato resta `UNRESOLVED`. Lo stesso nome usato da attori diversi diventa `ENTITY_COLLISION`. Le etichette non si uniscono mai per somiglianza.
- **Arricchimento del settore.** La skill cerca un settore sul web solo quando la tua richiesta lo richiede e il record non lo ha. Se le prove sono deboli o in conflitto, il settore resta sconosciuto.
- **Aggregati.** La skill non somma i conteggi di tracker diversi. Mostra una serie coerente, oppure mostra le fonti affiancate con la differenza.
- **Esportazione.** Chiedi l'output in JSON quando vuoi riusare i risultati.
