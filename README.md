# Obecní radar

Vlastní náhrada služby GovRadar. Sleduje úřední desky a portály a zobrazuje
všechny záznamy na webu s filtry. Uložený filtr umí posílat novinky e-mailem.
Běží zdarma na GitHubu: sběr dat obstarává GitHub Actions, web GitHub Pages.

## Jak to funguje

1. Každé 2 hodiny se spustí GitHub Action (`.github/workflows/radar.yml`) a stáhne
   všechny zdroje. U nových záznamů přečte i text příloh (PDF, DOCX, ODT) a
   rozpozná zmíněné obce: všech 1 144 obcí Středočeského kraje a obce
   Podřipska v Ústeckém kraji.
2. Data se uloží do větve `data` v tomto repozitáři a web se znovu nasadí.
3. Web zobrazuje všechny záznamy s filtry: zdroj, obce, klíčová slova, období
   a hledání v názvu. K dispozici jsou předvolby **Dřínov** a **Všechno**,
   případně vlastní výběr.
4. Tlačítko **Odebírat e-mailem** vytvoří z aktuálního filtru odběr. Odběr
   pak dostává jen nové záznamy, které filtru odpovídají, a to ihned, jednou
   denně, nebo jednou týdně.

## Sledované zdroje

| Zdroj | Stav | Poznámka |
|---|---|---|
| DESÚ – úřední deska | ✅ | v GovRadaru |
| CENIA – EIA záměry | ✅ | v GovRadaru; obce z údaje „Umístění“ záměru |
| Středočeský kraj – úřední deska | ⛔ | v GovRadaru; **web blokuje servery mimo ČR**, viz níže |
| Ústecký kraj – úřední deska | ✅ | v GovRadaru; otevřená data (OFN) |
| Správa železnic – veřejné zakázky | ✅ | v GovRadaru; XML export profilu zadavatele |
| ŘSD – úřední deska | ⛔ | **web blokuje servery mimo ČR** |
| Správa železnic – úřední deska | 🔧 | web má neúplný řetězec certifikátů, připravuje se |
| Ministerstvo dopravy – úřední deska | 🔧 | web je chráněný proti robotům, připravuje se |
| CENIA – SEA koncepce | ✅ | |
| MěÚ Kralupy n. Vlt. (ORP, stavební úřad) | ✅ | ORP pro Dřínov |
| Státní pozemkový úřad – úřední deska | 🔧 | web SPÚ momentálně nefunguje (chyba 504) |
| SFŽP – dotační výzvy | ✅ | |
| MMR – národní dotace | ✅ | nové programy a výzvy |
| ÚZSVM – nabídka majetku pro obce | ✅ | |

Klíčová slova a oblasti GovRadaru (KD8) jsou přepsané v `config/govradar_kd8.json`.

### Zdroje blokované pro GitHub

Středočeský kraj a ŘSD nepovolují připojení ze zahraničních serverů, a GitHub
Actions běží v USA. Možná řešení:
1. **Self-hosted runner** (zdarma) na počítači nebo NASu, který stojí v ČR,
   např. na obecním úřadě. Tyto dva zdroje by pak sbíral on.
2. Malý český VPS (zhruba 100 Kč/měsíc) jako self-hosted runner.

## Pravidla vyhledávání (web i e-mail se řídí stejnými)

- Klíčové slovo musí začínat na začátku slova („transevropsk“ najde „transevropské“).
- Slovo psané malými písmeny se hledá bez ohledu na velikost písmen.
- Slovo s velkým písmenem (zkratky VRT, ZÚR, D8) rozlišuje velikost písmen.
  Zkratka do 4 znaků se hledá jen jako celé slovo, takže „VRT“ nenajde „vrtaček“.
- Obce se rozpoznávají včetně běžného skloňování (Dřínov, Dřínově, Dřínovem).
  Názvy obcí, které jsou zároveň běžnými slovy nebo jmény, mohou dát falešnou shodu.
- Skeny bez textové vrstvy se prohledat nedají. Záznam se pak označí štítkem
  „příloha bez textu“.

## Nastavení (jednorázově)

1. **GitHub Pages:** Settings → Pages → Source: *GitHub Actions*.
2. **Klíč pro šifrování e-mailů:** Settings → Secrets and variables → Actions →
   *New repository secret* `SUBSCRIPTIONS_PRIVATE_KEY`. Vložte do něj celý
   obsah soukromého klíče, včetně řádků `-----BEGIN/END PRIVATE KEY-----`.
   Veřejný klíč je v `config/public_key.pem`. Nový pár vytvoří příkaz
   `python tools/generate_keys.py klic.pem`, starší odběry pak ale přestanou
   jít dešifrovat.
3. **SMTP**, tedy odkud se e-maily posílají: secrets `SMTP_HOST`, `SMTP_PORT`
   (výchozí 587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` a volitelně
   `SMTP_SECURITY` (`starttls` jako výchozí, `ssl` nebo `none`).
4. První sběr: Actions → *Obecní radar – sběr a web* → *Run workflow*. Jinak
   proběhne sám do 2 hodin.

## Přidání e-mailového odběru

1. Na webu nastavte filtr a klikněte na **Odebírat e-mailem**.
2. Vyplňte název, e-mail a frekvenci. Web e-mail zašifruje veřejným klíčem,
   takže ve veřejném repozitáři zůstane nečitelný.
3. Vygenerovanou položku vložte do pole `subscriptions` v `config/subscriptions.json`.
   Odkaz „Otevřít soubor na GitHubu“ vás přesměruje přímo do editoru.

Odběr pošle jen záznamy, které přibudou po jeho vytvoření. Denní souhrn
odchází při prvním běhu po 7:00, týdenní v pondělí. Když nic nového není,
e-mail se nepošle.

## Lokální spuštění

```bash
pip install -r requirements.txt
python -m collector.main --data data --no-email
tools/build_site.sh data _site && python -m http.server -d _site 8000
```

Číselník obcí a sousedů Dřínova z RÚIAN se obnoví příkazem
`python tools/build_municipalities.py`.

## Plán

- **Fáze 2 (hotovo):** zdroje GovRadaru a schválené zdroje navíc; rozpoznávání
  všech obcí Středočeského kraje.
- **Fáze 3:** úřední desky obcí kraje. Začne se obcemi, které publikují desku
  jako otevřená data (OFN). Parser `collector/sources/ofn.py` je na to připravený.
