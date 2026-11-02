> **Veřejná verze:** stáhněte kompletní Windows ZIP z Releases, rozbalte jej a spusťte `Nainstalovat.cmd` (vyžaduje Python 3.12 x64 a internet pro instalaci Python závislostí). Poté použijte `Spustit Music Forge.cmd`. Přibaleny jsou zvukové banky a FluidSynth. Zdrojový kód v repozitáři neobsahuje velké zvukové banky; ty jsou ve vydání. Soukromá analýza hudební knihovny není součástí balíku a karta Průzkum má prázdný seznam. Starší informace o připravené `.venv` a 60 lokálních skladbách níže popisují původní vývojové prostředí.

# Music Forge Next 1.1

Samostatná lokální verze procedurálního hudebního generátoru. Původní `pulse-forge-studio` se nemění. Rozhraní je v češtině. Pro běžnou tvorbu nepotřebuje internet, API klíč, účet ani model AI.

## Spuštění

Dvojklik na **Spustit Music Forge.cmd** otevře aplikaci na **http://localhost:8877/**. Okno serveru ponech otevřené; zavřením server vypneš. Projekt obsahuje připravené lokální Python prostředí pro tento počítač a všechny zvukové banky.

1. Nahoře najdeš **seed** vybraný při spuštění aplikace. Můžeš ho přepsat, tlačítkem ⤨ vybrat nové číslo nebo otevřít knihovnu uložených seedů. Tvorba používá zobrazené číslo; sama ho potají nemění. Pak vyber styl a náladu. Výchozí délka je **3:30**, volitelně **0:20 až 10:00**.
2. Klikni na **Vytvořit skladbu**, nebo nejdřív na třicetisekundový náhled.
3. Přehrávej, posouvej se po průběhu i kliknutím na část aranžmá. Mezerník přepíná přehrávání, pokud právě neupravuješ vstup.
4. V mixu vyměň nástroj, hlasitost, panoramu, mute/solo. Tlačítko se třemi čárkami otevře pět zvukových ovladačů. **Hlasitost, panorama, mute/solo, jas, sytost a prostor reagují okamžitě při přehrávání.** Výměna nástroje a změna obálky automaticky načte pouze danou stopu a prolne ji ve stejném místě skladby. Přehrávání ostatních stop pokračuje. Tlačítko **Připravit export** připravuje soubory; není potřeba pro poslech úprav. Poslechová hlasitost přehrávače funguje okamžitě a nemění export.
5. Exporty jsou v horní liště vedle uložení projektu i pod přehrávačem. Stáhni **WAV 48 kHz / 24 bit / stereo** nebo **Ogg Opus 48 kHz / 160 kb/s CBR / stereo**. Nabídka `•••` nabízí také MIDI a autorské údaje.

Audio i MIDI mají název **`Název skladby (seed).přípona`**. Použije se aktuálně zadané jméno a seed skutečně exportované skladby, i když je ve vstupním poli už připravený jiný seed pro další tvorbu. Diakritika zůstává zachovaná; znaky nepovolené v názvu souboru se odstraní.

**Uložit projekt** stáhne malý JSON s nastavením a seedy. **Otevřít projekt** je načte a zachová seed pro reprodukci. Poté spusť tvorbu pro obnovu zvuku. JSON není audio záloha. Exportované audio ukládej mimo interní `outputs/`, která je pracovní cache.

## Hudba a ovládání

- 58 stylů pokrývá house a taneční elektroniku, future bass, dubstep, D&B, synthwave, pop, instrumentální K-pop, rock, hip hop, jazz, folk, klasiku, filmovou hudbu i ambient.
- 24 nálad. Rychlá volba obsahuje vždy **Radostná, Smutná, Energická, Temná**; ostatní nálady zůstávají v rozbalovacím výběru.
- Osm rolí: bicí, basa, akordy, melodie, odpovědi, atmosféra, arpeggio a přechody. Jednotlivé role mohou mít v klidných stylech nebo částech pauzu.
- Automatické výchozí hlasitosti zohledňují zvuk, roli a vysoké rychlé party: **Silk do 50 %, Glass do 20 %, Orbit do 25 %, Vibraphone do 50 %**. Expressive dechy v basové roli začínají do 20 %. Jde o počáteční doporučení; každý slider lze ručně nastavit v celém rozsahu **0–150 %** a uložené ruční hodnoty mají přednost. Automatický výběr nezařazuje dechové nástroje do basy. Tóny a rytmy se při vyvážení nemění.
- Výchozí kompozice pracuje s osmítaktovým tématem, čtyřtaktovým frázováním, akordovými důrazy, odpověďmi, kontrastem sekcí a obměnou posledního vrcholu. Návraty motivu jsou záměrné; každá nová náhodná nota nepřináší lepší hudbu.
- **Nový motiv** mění hlavní melodii při zachování ostatních not. **Nové zvuky** mění automatickou paletu při zachování partitury. Ručně vybrané nástroje zachová.
- Jas ovlivňuje filtr a harmonické. Náběh a doznění jsou relativní k původnímu presetu; 50 % znamená původní obálku. U bicích se doznění upravuje tvarováním jejich přirozeného dozvuku. Sytost přidává harmonické; prostor přidává reverb a/nebo odrazy. Hlasitost a panorama jsou samostatné.
- Vyvážení hlasitostí respektuje role a aktivitu. Elektronické styly používají ducking basy a doprovodu podle kopáku. Master používá jednu konstantní úpravu hlasitosti a omezení špiček; tiché části se samostatně nezvedají. Nové výchozí rozdíly částí jsou opatrně nastavené podle měření referencí a lze je dál měnit ovladačem **Hlasitost části**.
- Barvy průběhu odpovídají částem stavby skladby. Výchozí jednoduchý pruh ukazuje RMS energii; obrys špiček je volitelný přes **Zobrazit špičky**, při otevření vypnutý. Nejde o původní nebo druhou nahrávku.
- Při změně hlasitosti, panoramy, mute/solo a úrovní částí reaguje rychlý náhled z aktuálních stop. Používá stratifikovaný vzorek PCM a relativní změnu proti poslední přesné křivce. Na pozadí ho vystřídá přesný výpočet celého mixu; náhled nikdy neovlivňuje zvuk ani export. Průběh se nenormalizuje zvlášť pro každou část.
- **Backspace pod kurzorem** obnoví daný slider, číselné pole, výběr nebo přepínač. Není potřeba kliknout ani přesouvat fokus. Hlasitost se vrací k doporučené počáteční úrovni aktuálního presetu a panorama k původní poloze stopy, makra k neutrálnímu presetu (50 % jas/náběh/doznění, 0 % sytost/prostor), úroveň části na 100 %, poslechová hlasitost na 80 % a pozice na začátek. Při psaní názvu či hledání funguje Backspace normálně. Zkratka nezasahuje do Ctrl/Alt/Shift/Meta kombinací ani zakázaných ovladačů.
- Přehrávač skládá synchronizované stopy přes Web Audio. Export používá stejný zvukový graf v OfflineAudioContext; server pouze uloží výsledné PCM do 24bitového WAV a zakóduje Opus 160 kb/s. Poslechová hlasitost přehrávače se do exportu nezapisuje.
- Každé generování má jedno ID požadavku a vlastní výsledek. Opakování stejného požadavku nespustí druhou skladbu. Mezerník nad tlačítkem tvorby ovládá přehrávání. Další karta nemůže vyměnit výsledek právě dokončeného požadavku.
- Port na Windows výhradně vlastní jediný server. Opakované spuštění otevře běžící aplikaci; nevznikne druhý server na stejné adrese.


## Nástroje a původ

Banky obsahují přes 600 samostatně volitelných presetů, variant, efektů a bicích sad; **nejde o 600 odlišných akustických nástrojů ani o kolekci studiových VST**. Zrcadlové bicí sady GeneralUser v banku 120 se do seznamu nezapočítávají dvakrát. Šest pochodových sad MuseScore s nekompatibilní mapou tónů není nabízeno. Expresivní varianty MuseScore mají implementované řízení dynamiky CC2.

- **GeneralUser GS 2.0.3**, S. Christian Collins: 261 melodických/zvukových presetů a 13 bicích sad. Kompletní upstream licence je v `assets/generaluser/LICENSE.txt`.
- **MuseScore General 0.2**, S. Christian Collins, Frank Wen, Michael Cowgill a další: větší multisamplovaná banka včetně orchestrálních nástrojů, variant artikulace a bicích sad. MIT licence a zdroje jednotlivých nahrávek jsou v `assets/musescore/`.
- **Salamander Grand Piano**, Alexander Holm; SF2 adaptace Roberto / FreePats: samostatný klavír Yamaha C5, zdroj s 16 vrstvami úhozu. Použitá SF2 adaptace nezahrnuje všechny pedal/hammer/resonance funkce původní SFZ verze. CC BY 3.0; původní dokumentace v `assets/salamander/readme.txt`. Při zveřejnění nahrávky s tímto klavírem přilož autorský údaj **Salamander Grand Piano — Alexander Holm, CC BY 3.0; SF2 adaptation Roberto / FreePats** a odkaz https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html.
- **32 vlastních syntetických presetů**: harmonicky omezené oscilátory, FM, plucky, široké leady a pady, sub/reese/growl/acid basy, zvony a šumové přechody. Názvy nejsou označením pluginů FL Studia.

Zvukové banky včetně stažených archivů zabírají přibližně **1,83 GB**, pod limitem 5 GB. Přesné velikosti, adresy a SHA-256 stažených souborů jsou v `assets/sources.json`. Celý projekt včetně prostředí, modelů a cache zůstává pod 10 GB; automatická pracovní cache má vlastní rozpočet přibližně 2,2 GiB. Volně přidané soubory mimo označené složky generátoru se nemažou.

## Analýza a její meze

Karta **Průzkum & principy** zpřístupňuje výsledky analýzy **60 náhodně vybraných jedinečných lokálních skladeb**, celkem přibližně 220 minut zvuku. Původní soubory nebyly změněny ani kopírovány do projektu. Pro každou skladbu existuje SHA-256 a úplný záznam v `research/analysis.json`.

Celé nahrávky prošly DSP analýzou energie, spektra, nástupů, sterea, přibližného tempa, tóniny a kandidátů strukturálních změn. Na třech desetisekundových úsecích každé nahrávky se vyhodnotily dva lokální modely: **AST / AudioSet** a nezávislé porovnání textu a audia **CLAP**. Detekce nástrojů je hypotéza s chybami. Nízká AST skóre neposkytují spolehlivou identifikaci a podobnost CLAP není pravděpodobnost; výsledky se v UI takto označují. Modely nejsou součástí generování hudby a skladby neslouží jako audio samply.

Vzorek převládá v elektronice a popu, protože pochází z této osobní knihovny. Nedokládá kvalitu generátoru v klasice či jazzu. Rozbor FL Studia a výzkumu vnímání hudby je v `research/NOTES.md`; jde o zdůvodnění implementačních rozhodnutí, nikoli o poslechovou studii ani trénink vlastního generativního modelu.

Generátor vytváří instrumentální hudbu. Nezpívá text, nehostuje pluginy FL Studia a neslibuje kvalitu profesionální studiové produkce v každém žánru. NCS a Argofox jsou hudební značky, jejichž různorodé styly zde zastupují žánrové profily. Technické testy neprokazují, že se skladba bude líbit konkrétnímu člověku, ani právní jedinečnost každého motivu.

## Vývoj a ověření

Použitý Python: **3.12 x64**. Při přenesení na jiný počítač je třeba znovu vytvořit `.venv`; Python prostředí obsahuje absolutní cesty. Běžný provoz používá jen `requirements.txt`. Rozšířené balíčky a dva modely jsou potřeba pouze k nové analýze.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py --open
```

Zvukové banky a přenosný FluidSynth jsou už stažené. Obnovovací nástroje jsou `tools/fetch_assets.py`, `tools/fetch_acoustic.py` a pro výzkum `tools/fetch_clap.py`. Jejich stahování vyžaduje internet; v manifestech jsou kontrolní součty dodané verze. FreePats v době sestavení používal prošlý TLS certifikát; jeho neexekutivní audio archiv byl získán z oficiálního HTTP endpointu, s touto skutečností zachovanou ve zdrojích.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools/validate_audio.py --all
node --check static/app.js
```

První sada kontroluje 696 úplných plánů přes 58 profilů, různé délky a nálady, determinismus, rozmanitost, ovladače, hranice not, harmonii, MIDI a nezávislé varianty. Audio test skutečně vyrenderuje všechny styly, ověří 48 kHz / 24 bit / stereo WAV, přesné délky, Opus 160 kb/s, špičky před i po kompresi, cache osmi stop a slyšitelný účinek všech pěti maker na skutečném PCM. Výsledky se zapisují do `research/audio-validation.json`.

`tools/analyze_library.py --count 60` a `tools/crosscheck_instruments.py` obnovují analýzu. Výběr používá seed 20261030, setříděné a promíchané cesty, kontrolu duplicit SHA-256 a vyřazení nahrávek kratších než 45 s. Analýza je obnovitelná po přerušení.

Kód je rozdělený na `catalogue.py` (profily a banky), `composer.py` (noty a forma), `dynamics.py` (úrovně částí), `audio_engine.py` (render a mastering), `live_backend.py` (náhledy a přesný export), `server.py` (lokální API) a soubory v `static/` (UI a živý zvukový graf). Server naslouchá výhradně na loopbacku, kontroluje Host/Origin a neposkytuje soubory mimo povolené statické a exportní cesty.

`tools/validate_presets.py` kontroluje skutečný zvuk všech 610 nabízených presetů. Výsledek je v `research/preset-validation.json`; při poslední kontrole nebyl žádný preset tichý. Opt-in testy HTTP lze spustit nastavením `RUN_HTTP_TESTS=1` a běžným unittest discovery; kontrolují i exportní rozsahy, ochranu lokálního API a zachování předchozího masteru při zrušení.

## Ověření verze 1.1

`research/dynamics.json` porovnává třísekundovou RMS energii 60 referencí. Medián rozdílu P90–P10 je 7,66 dB; původní Future House měl 1,41 dB a po opravě 6,70 dB. Melodic House se změnil z 2,18 na 7,41 dB. Porovnáním not je ověřeno, že se melodie, akordy, basa ani bicí při této opravě nezměnily. Jedná se o RMS dynamiku, nikoli o LUFS ani ruční označení všech dropů.

`http://localhost:8877/audio-tests.html` provede 27 kontrol zvuku, ovládání a exportních názvů bez přehrávání do reproduktorů: hlasitost, mute, panorama, jas, sytost, dozvuk, hlasitost částí a synchronizace. Testy serveru navíc kontrolují opakované požadavky, neměnné výsledky, načtení jediné stopy a vzorkovou shodu vstupního PCM s WAV exportem.

Finální sada má 18 úspěšných testů, včetně ochrany proti dvěma serverům na jednom portu a správného načtení starších skladeb bez dvojího použití hlasitostní křivky. Záznam je v `research/balance-seed-tests.log`; aktuální kontroly v prohlížeči jsou v `research/balance-browser-tests.txt`. Audio regrese zahrnuje 61 renderů přes všech 58 stylů a 20 kontrol účinku zvukových maker.

Živý přehrávač drží dekódované stopy v RAM. U 3:30 je to přibližně 645 MB stereo PCM, u 10 minut více. Načítání běží po dvou stopách; po načtení nevyžaduje poslech ani pohyb mixu další mastering. Pracovní náhledy jednotlivých nástrojů mají omezenou cache. Před aktualizací byly existující skladby zálohovány v `.history/before-realtime/user-compositions/`.

## Ověření resetu a rychlého průběhu

Rozšířená stránka `audio-tests.html` má 27 úspěšných kontrol včetně Backspace, ochrany textových vstupů, shody optimalizovaného a plného zvukového grafu a odezvy průběhu u 30 s i 210 s / osmi stop. Přesný render vynechává pouze větve s nulovým příspěvkem; maximální naměřený rozdíl vůči plnému grafu byl 1,20 × 10⁻⁷ amplitudy. Není snížen sample rate ani kvalita efektů.

Výpočet rychlého náhledu měl v benchmarku 4–6 ms; skutečný slider basy v celé skladbě se v UI projevil za 22 ms a reset za 8 ms. Přesný dopočet byl v této zkoušce přibližně 0,86 s pro 30 s a 4,58 s pro 210 s včetně čekání po změně. Rychlosti závisejí na hardwaru a zatížení. Záznamy jsou `research/hover-reset-tests.txt` a `research/hover-reset-performance.json`. Zdroj UI před úpravou je v `.history/before-hover-reset/`.

## Seedy, vyvážení a přirozený konec

**Uložené seedy** pojmou až 50 vlastních oblíbených položek, nejde o předem vybrané náhodné skladby. Uložení uchová celé zadání včetně nástrojů, mixu a variant motivu/zvuků. Nabídka rozlišuje uložení vyplněného zadání a přehrávané skladby. Kliknutí na položku vyplní zadání; hudbu vytvoří hlavní tlačítko a právě přehrávaný mix mezitím pokračuje. Seedy jsou trvale v `saved-seeds.json` vedle programu, nezávisle na audio cache a datech prohlížeče. Zápis je atomický, existuje `saved-seeds.backup.json` a poslední odstranění lze vrátit. Každé otevření nebo obnovení stránky vybere nový náhodný seed a čisté výchozí zadání. Knihovna se sama nenačítá do zadání.

`balance.py` obsahuje upravitelné zvukové preference a opatrné počáteční úrovně pro jasné doprovody a husté vysoké party. Měření osmi skutečně vyrenderovaných presetů je v `research/balance-analysis.json`; jde o měření hlasitosti a spektra, ne o automatické skóre obliby. Skript `tools/analyze_balance.py` analýzu obnoví. Kontrola přes 58 stylů a dva seedy potvrzuje shodné noty před vyvážením a po něm.

Opravený konec drží úroveň závěrečné části až do konce audia. Dřívější obálka se v mezeře za posledním úplným taktem vracela na 100 %, u tanečních stylů to vytvořilo přibližně +6 dB. Nové rendery mají `tail_gain_fixed=true`; starší stopy opravuje přehrávač i export při přehrání, včetně výměny jednotlivého nástroje. Závěrečné tóny a efekty zůstávají; oprava nepřidává náhodné zvýšení hlasitosti. Regrese je v `research/balance-seed-tests.log` a `research/balance-browser-tests.txt`.

## Čistý start a volné ruční hlasitosti

Po otevření nebo obnovení stránky se použije výchozí zadání, nový náhodný seed, prázdný přehrávač a automatický výběr nástrojů. Poslední skladba, mix ani rozpracované ovladače se z prohlížeče nenačítají. Uložené projekty a knihovna oblíbených seedů zůstávají dostupné a použijí se až po výslovném otevření.

Silk 50 %, Glass 20 %, Orbit 25 % a Vibraphone do 50 % jsou doporučené počáteční úrovně, nikoli stropy. Všechny mixové slidery mají ruční rozsah 0–150 %. Přepnutí presetu nastaví jeho doporučenou úroveň; další ruční změna se zachová i v exportu a uloženém projektu. Backspace vrací doporučenou počáteční hodnotu. Explicitní mix v načteném projektu má přednost před automatickým vyvážením. 

## Hlasitostní křivky a rychlejší přepínání

U každé vygenerované stopy rozbal **Hlasitostní křivka**. Klik přidá bod, tažení upraví jeho čas a relativní hlasitost; Delete nebo Backspace smaže vybraný vnitřní bod. Krajní body určují začátek a konec skladby. Tlačítko **Rovná křivka** vrátí 100 % po celou dobu. Křivka násobí hlasitost slideru, reaguje při přehrávání, mění vizualizér a ukládá se do projektu, oblíbeného seedu i metadat exportu. Maximum je 64 bodů a relativní úroveň 0–150 %.

Výměna nástroje začíná po 35 ms místo 230 ms a dokončení se kontroluje po 35 ms místo 160 ms. Dekódované dříve použité zvuky uchovává omezená LRU cache (nejvýše 256 MiB na otevřenou skladbu); návrat k nim nevyžaduje serverový render, přenos ani dekódování. První použití nového zvuku stále vyžaduje výpočet celé stopy, aby se zachovala přesná kalibrace a export. Nová stopa se prolíná 35 ms, ostatní hrají dál. Rychlé přepínání použije poslední zvolený nástroj.

Aktuální ověření: 19 Python/HTTP testů (`research/clean-start-tests.log`) a 30 kontrol skutečného Web Audio grafu (`research/curves-browser-tests.txt`). Prohlížeč ověřil přidání/tažení/mazání bodu, zachování hlasitosti 120 % v projektu i exportu a čistý start po F5 (prázdný přehrávač, 3:30, nový seed, poslech 80 %, špičky vypnuté). Při měření skladby 3:30 trvala první výměna testovaného syntezátoru 2 214 ms a návrat z cache 196 ms včetně ovládání přes automatizaci; nejde o garanci pro všechny banky a počítače. Detaily: `research/instrument-latency-browser.json`. Test rychlé volby A–B–A ověřuje, že výsledek odpovídá poslednímu výběru i při opětovném použití čekající úlohy.

## Průběh každé stopy a návrat k volbě seedu

Pod nástrojem rozbal **Hlasitostní křivka a průběh stopy**. Nahoře je bodová křivka, pod ní skutečný zvuk samostatného nástroje po efektech, hlasitosti, panoramě a automatizaci, před společným masterem. Oba grafy mají stejné časové členění a barvy jako hlavní přehrávač. RMS graf používá pevné měřítko: tichá stopa se automaticky nezvětšuje. Mute a sólo jiné stopy se projeví i zde. Při změně se okamžitě ukáže označený živý náhled; po krátké prodlevě jej nahradí **Přesný průběh** vypočtený skutečným Web Audio grafem z celého PCM. Výpočet probíhá jen pro rozbalené stopy, postupně, a zastaralé výsledky nemohou přepsat novější editaci.

Klik na bod jej vybere; šipky doladí čas o sekundu nebo hlasitost o procento, Shift krok zvětší desetkrát. Vybranému bodu lze také zadat přesný čas v sekundách a hlasitost v procentech. Delete / Backspace smaže vnitřní bod, krajní body zůstávají. Kliknutí do průběhu nástroje posune přehrávání; šipky vlevo/vpravo posouvají o pět sekund a Home / End na začátek/konec. Svislá pozice přehrávání je společná oběma grafům i hlavnímu přehrávači.

Tlačítko **↺** na řádku stopy obnoví celou automatickou volbu daného seedu a varianty zvuků: nástroj, jeho počáteční hlasitost, panorama, pět zvukových ovladačů, mute/solo i rovnou křivku. Funguje i tehdy, když skladba vznikla z projektu s ručním výběrem nástroje. Reset nezasahuje do not a ostatních stop. Tlačítko **Zpět** vrátí stav před resetem; další vlastní úprava dané stopy tuto jednorázovou možnost zruší. Metadata `seed_default` se ukládají s plánem, hlasitosti jsou i nadále ručně volné do 150 %. U starších interních renderů bez metadat se použije původní uložený stav stopy.

Výpadek načtení nástroje zachová přehrávaný zvuk a vrátí výběr i obálku k jeho skutečným hodnotám. Editor se během tvorby nepřepisuje a mazání bodů se vztahuje pouze na právě vybranou křivku.
