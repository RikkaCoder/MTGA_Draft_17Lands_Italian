# Localizzazione italiana

## Architettura

La localizzazione è confinata al livello di presentazione. La logica di Draft, i
punteggi, gli identificatori, i dati 17Lands e gli export per MTG Arena continuano
a usare i valori canonici inglesi.

- `src/i18n/translator.py` carica i cataloghi JSON, applica la lingua corrente e
  il fallback, formatta parametri, plurali semplici, numeri e percentuali.
- `src/i18n/card_names.py` risolve esclusivamente il nome da mostrare all'utente.
- `src/i18n/locales/it_IT.json` contiene il catalogo italiano predefinito.
- `src/i18n/locales/en_US.json` contiene il catalogo inglese e costituisce il
  fallback.
- `Settings.language` persiste `it_IT` o `en_US` in `config.json`. I file creati
  da versioni precedenti, privi della proprietà, ricevono il valore predefinito
  `it_IT` durante la validazione.

Le sezioni `advisor`, `generated`, `roles`, `tags`, `types`, `colors` e `stats`
dei cataloghi costituiscono il glossario centralizzato. I termini Magic usati
nell'interfaccia devono essere aggiunti o corretti lì, non nei widget.

## Aggiungere o modificare una stringa

1. Scegliere una chiave gerarchica stabile, per esempio
   `advisor.recommended_pick`.
2. Aggiungere la stessa chiave a `it_IT.json` e `en_US.json`.
3. Usare `tr("advisor.recommended_pick")` nel codice di presentazione.
4. Per valori dinamici usare segnaposto nominati, per esempio
   `tr("deck.main_deck", count=40)`.
5. Per un plurale semplice definire un oggetto con `one` e `other` e passare
   `count=` a `tr`.

Se una chiave non esiste nella lingua attiva, viene cercata in inglese. Se manca
anche nel catalogo inglese, viene restituita la chiave stessa e l'anomalia è
registrata una sola volta nei log; l'interfaccia non va in crash.

## Cambiare o aggiungere una lingua

La lingua si cambia da **File → Preferenze → Lingua**. La scelta viene salvata
immediatamente. Le finestre aperte in seguito usano subito la nuova lingua; per
riallineare tutti i widget già aperti è necessario riavviare l'applicazione.

Per aggiungere una lingua:

1. copiare `en_US.json` in `src/i18n/locales/<locale>.json`;
2. tradurre i valori senza cambiare le chiavi o i segnaposto;
3. aggiungere il locale ammesso al validatore di `Settings.language` e alla
   mappa mostrata nella finestra Preferenze;
4. se Arena offre la localizzazione, aggiungere la relativa tabella alla mappa
   `ARENA_LOCALE_TABLES`;
5. estendere i test di catalogo e fallback.

## Nomi ufficiali delle carte

Il resolver apre il database locale di MTG Arena in modalità SQLite di sola
lettura. La struttura verificata sul database Arena usato durante lo sviluppo è:

- tabella `Cards`, con `GrpId` e `TitleId`;
- tabella `Localizations_enUS`, con `LocId`, `Formatted`, `Loc`;
- tabella `Localizations_itIT`, con `LocId`, `Formatted`, `Loc`.

`Cards.TitleId` viene unito a `Localizations_enUS.LocId` e
`Localizations_itIT.LocId`. Il risultato è indicizzato sia per `GrpId` sia per
nome canonico inglese. Questo permette a stili alternativi, ristampe e più Arena
ID di convergere sul nome ufficiale. Le facce separate da ` // ` vengono risolte
singolarmente. Apostrofi, accenti e caratteri Unicode sono conservati senza
normalizzazioni distruttive.

La priorità effettiva è:

1. nome ufficiale nel database locale Arena, prima tramite Arena ID e poi tramite
   nome canonico inglese;
2. nome canonico inglese come fallback.

I dataset già presenti nel progetto non forniscono un mapping italiano distinto,
quindi non viene inventato né scaricato alcun nome. Il nome localizzato non viene
mai scritto nei dati della carta e non viene usato per scoring, lookup, immagini
o export.

## Limiti conosciuti

- Senza un database locale di Arena contenente `Localizations_itIT`, i nomi delle
  carte restano in inglese.
- Alcune carte digital-only possono non avere una localizzazione italiana
  ufficiale; anche in questo caso viene mostrato il nome inglese.
- Gli export e i nomi richiesti dalle integrazioni restano canonici inglesi per
  compatibilità.
- Il cambio lingua non ricostruisce i widget già aperti: riavviare l'app per un
  aggiornamento completo della schermata corrente.
- I log tecnici destinati agli sviluppatori restano in inglese.

## Test

Con Poetry:

```bash
poetry install
poetry run pytest
```

I test specifici sono in `tests/test_i18n.py`,
`tests/test_card_name_localization.py` e
`tests/test_localization_regression.py`. La compilazione sintattica può essere
controllata anche senza dipendenze con:

```bash
python -m compileall -q main.py src tests
```
