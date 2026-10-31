# Rozhodnutí pro Music Forge Next

Datum sestavení: 30. 10. 2026. Toto jsou pracovní návrhové poznámky k implementaci. Měření nahrávek a modelové hypotézy jsou uložené samostatně v `analysis.json`; automatické kontroly zvuku v `audio-validation.json`.

## Co se skutečně analyzovalo

Z místních čtyř částí hudební knihovny se vybralo 60 jedinečných audio souborů. Výběr je náhodný s pevným seedem 20261030; duplicity se odmítají podle obsahu SHA-256. Nahrávky mají dohromady 13 182 sekund, přibližně 220 minut. Neproběhl řízený lidský poslechový experiment ani přepis celých partitur. Vzorek silně zastupuje elektroniku, pop a skladby vydané NCS; není reprezentativním vzorkem všeho, co mají lidé rádi.

Celé skladby se dekódovaly na 16 kHz stereo a měřily se nástupy, RMS, špičky, stereo korelace, spektrální centroid, energie pásem, přibližná chroma/tónina, kandidáti tempa a změny dvousekundových popisů. Pro nástroje se použily úseky o délce 10 sekund v 18 %, 50 % a 80 % skladby. AST používá AudioSet klasifikaci; CLAP porovnává zvuk s pevně uvedenými 26 popisy instrumentace. Oba běží lokálně. Žádná celá skladba ani její výřez se neposílal do externího audio API.

Naměřený medián délky je 211,294 s — požadovaná výchozí délka 210 s dobře odpovídá tomuto konkrétnímu vzorku. Medián počtu detekovaných nástupů je přibližně 4,405 za sekundu; to zahrnuje více zdrojů současně a nelze to ztotožnit s počtem not sólové melodie. Medián podílu energie 20–150 Hz je 0,552 při této metodě měření. Medián crest faktoru je 12,17 dB a stereo korelace 0,773. Tyto údaje podporují opatrné vyvážení basové oblasti, mono kompatibilitu basy a ponechání místa pro transienty; neurčují správný mix každého žánru. Tato implementační volba je vlastní interpretací měření.

Zjištěný medián RMS −25,89 dBFS není automatický masteringový cíl: úroveň konkrétních souborů může odrážet dřívější úpravy hlasitosti, kodek a metadata. Generátor proto používá samostatné měření EBU R128. Přibližná tempa mají omezené rozlišení a mohou být dvojnásobná/poloviční; korelace tóniny není důkaz správné tóniny. Novost spektra může znamenat nástup zpěvu, výměnu nástroje či změnu hlasitosti, nikoli nutně nový refrén.

Medián nejvyššího nástrojového AST skóre byl pouze 0,0311. To je zásadní důvod nepopsat výsledky jako spolehlivě rozpoznanou instrumentaci. Původní automatický výběr navíc zachytil štítky jako „Computer keyboard“ nebo „Drum and bass“, které nejsou nástroji; ty byly ze seznamu nástrojů odstraněny. CLAP byl přidán jako nezávislá kontrola. Například hlasové popisy bývají silné u popových skladeb, u elektronických instrumentálek vystupují synth leady a elektronické perkuse, ale i CLAP může považovat synth za kytaru nebo chybně odhadnout hlas. Jeho kosinové podobnosti jsou pořadím hypotéz, nikoli procenty jistoty. Při neshodě modelů nelze pravdu odhlasovat průměrem čísel.

Modely a metodika: [AST model a licence](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593), [AST dokumentace](https://huggingface.co/docs/transformers/model_doc/audio-spectrogram-transformer), [CLAP model a použití](https://huggingface.co/laion/clap-htsat-unfused). Revize a hashe stažených souborů jsou v manifestech u modelů.

## Co lze vyvodit z výzkumu obliby hudby

Witek a kol. v experimentu s funkovými bicími vzory zjistili nejvyšší příjemnost a chuť k pohybu u střední míry synkop. Nevyplývá z toho, že všechny skladby mají mít stejné synkopy nebo stejné tempo. Přenos do programu je konzervativní: stabilní rytmická kostra a omezené synkopy/ghost notes; náhodnost nerozbíjí všechny důrazy. [Původní studie, PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0094446).

Cheung a kol. zkoumali očekávání a překvapení v harmonii západních popových skladeb. Příjemnost souvisela s jejich kombinací, nikoli s prostým maximalizováním překvapení. Vlastní návrhový závěr pro generátor: rozpoznatelný motiv, jeho návrat a řízeně pozměněný kontext; vedle stabilní harmonie příbuzný kontrast v bridge nebo tématu B. Program neimplementuje model studie a toto rozhodnutí nepotvrzuje poslechovou kvalitu výstupu. [Autorský plný text](https://www.marcus-pearce.com/assets/papers/CheungEtAl2019.pdf), [DOI](https://doi.org/10.1016/j.cub.2019.09.067).

Emoce se nedají zredukovat na „moll = smutek, dur = radost“. Program kombinuje mód s hustotou, úhozem, registrem, instrumentací a kontrastem. Rozdíly mezi lidmi, kulturami, zkušeností a kontextem zůstávají zásadní. Není k dispozici průzkum posluchačů tohoto konkrétního generátoru.

Fráze, melodie a vedení hlasů vycházejí z běžných principů západní tonální hudby: akordové opory na důrazech, průchodné tóny, blízké obraty, zakončení a pauzy. Tato pravidla jsou použitelná pro vybrané profily, nikoli univerzální zákon pro veškerou hudbu. [Open Music Theory — voice leading, harmony, form](https://openmusictheory.github.io/speciesIntro.html).

## Co z FL Studia bylo prozkoumáno

- **FLEX:** presetový nástroj kombinující více syntetických a samplovacích metod, osm maker definovaných konkrétním presetem, filtr, relativní úpravy obálek a efekty. Přenos do aplikace: zvolit dobrý preset, přizpůsobit několik praktických ovladačů, nezahltit úvodní obrazovku stovkami parametrů. [Oficiální manuál FLEX](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/FLEX.htm).
- **Sytrus:** šest operátorů, FM/RM a další syntéza, filtry, unison a efekty. Přenos: samostatné FM klávesy a zvony, rozmanité harmonické struktury, střídmé odladění pro šířku. Zdejší syntezátor není šestoperátorová emulace Sytrusu. [Oficiální manuál Sytrus](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Sytrus.htm).
- **Harmor / Harmless:** práce s harmonickými složkami; Harmor navíc nabízí resyntézu a složité modulace. Přenos: spektrálně omezené vlnové tabulky a opatrné řízení harmonických. Resyntéza audia ani obrazu není implementována. [Harmor](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Harmor.htm), [Harmless](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Harmless.htm).
- **3x Osc:** jednoduché skládání tří oscilátorů jako základ analogových bas a leadů. Přenos: omezený počet oscilátorů, odlišné tvary, detune a obálky s omezením aliasingu. [Oficiální manuál 3x Osc](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/3x%20Osc.htm).
- **DirectWave / FPC:** mapování vzorků podle tónu a síly úhozu; DirectWave popisuje i střídání vrstev, FPC je vícevrstvý bicí sampler. Přenos: opravdové sample banky, reakce na velocity a oddělené bicí sady; generátor však nepředstírá automatické round-robin vzorky tam, kde je banka nemá. [DirectWave](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/DirectWave.htm), [FPC](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/FPC.htm).
- **Transistor Bass:** subtraktivní basový nástroj ve stylu TB-303. Přenos: krátká acidová basa a žánrová šestnáctinová artikulace; nejde o přesnou obvodovou emulaci. [Oficiální manuál](https://cluster.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Transistor%20Bass.htm).

Další dostupné rodiny zahrnují fyzikálně modelované nástroje (např. Sakura), aditivní nástroje, granulární zpracování, slicery, klávesy a perkuse. Aktuální seznam byl ověřen v [oficiálním přehledu generátorů](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/generator_plugins.htm). Dostupnost se liší podle edice a licencí. Žádné licencované binární pluginy, FL presety ani FL sample packy se nekopírovaly.

## Pět věcí, které bych u různých rodin ladil jako první

Nejde o statisticky ověřený žebříček toho, co všichni uživatelé nejčastěji nastavují. Je to praktický výběr podle vlastností nástrojů a dokumentovaných ovladačů.

- **Klavír a elektrické piano:** síla úhozu a frázování; náběh zachovávající úder; přirozené doznění; jas / potlačení kolizí v nižších středech; malý prostor odpovídající aranžmá. U nahrané banky rozhodují také skutečné vrstvy úhozu, které EQ nevytvoří.
- **Kytary a další strunné nástroje:** skutečně hratelný registr a obrat; časování rozloženého úhozu; délka a překryv tónů; barva / míra zkreslení podle stylu; množství prostoru. Klavírní blokové akordy nejsou věrný kytarový úhoz.
- **Smyčce, dechy a žestě:** fráze a mezery pro nádech; náběh; doznění a legato; dynamika / jas; prostor. Dlouhá obálka sama neudělá z krátkého samplu realistické legato.
- **Synth lead a pluck:** spektrum / cutoff; attack; decay a release podle not; detune či sytost; tempo-synchronní delay a prostor. Basy s leadem nesoutěží stejným registrem a subharmonickými.
- **Basa a subbasa:** základní frekvence / registr; délka a překryv; harmonické pro slyšitelnost na menších reproduktorech; vztah ke kopáku; mono kompatibilita. Prostor je ve výchozím stavu suchý; případné odrazy basy jsou filtrovány nad spodním pásmem.
- **Pady:** attack; release; jas a odstranění nežádoucích basů; šířka; prostor. Tato vrstva má mít skutečnou roli a nemusí znít celou skladbu.
- **Bicí:** volba sady a úhozu; transient; délka dozvuku; jas a sytost; prostor a vzájemné úrovně. U jednorázových vzorků může běžný MIDI release nemít žádný účinek; to se při PCM testu prokázalo a implementace používá skutečné tvarování dozvuku.

Ve společném UI se první volby shrnují do **jasu, náběhu, doznění, sytosti a prostoru**. Výchozí obálka zůstává relativní k presetu; registr, rytmus, velocity, strum a obsazení řeší kompoziční vrstva, hlasitost a panorama samostatný mix. Toto je záměrný kompromis mezi jednoduchostí a editovatelností, nikoli náhrada všech možností DAW.

## Ověření a otevřená omezení

Testy prověřují notové hranice, determinismus, skutečné změny parametrů, úplné renderování, hlavičky a délky souborů, špičky po WAV i Opus dekódování a cache. Jsou schopné odhalit nefunkční ovladač nebo přebuzený export. Nehodnotí vkus, hook, emotivní přesvědčivost ani úroveň komerčních NCS / Argofox produkcí. Přesná další validace kvality by vyžadovala slepý poslech konkrétních ukázek mezi lidmi s různými preferencemi.

Zvuková banka Salamander má výrazně vyšší paměťový nárok než GeneralUser. SoundFont nástroje nemají všechny artikulace velkých studiových knihoven; rockové kytary, vokály a komplexní orchestrální styl mají reálná omezení. Proto je K-pop výslovně instrumentální a neexistuje slib syntetického lidského zpěvu.

Měření vstupní hlasitosti používá oficiálně dokumentovaný [FFmpeg loudnorm](https://ffmpeg.org/ffmpeg-filters.html#loudnorm); samotný novější master používá konstantní zisk a limiter. Rychlost je změřená na tomto počítači; nelze ji garantovat na jiném hardwaru. Oddělené noty a PCM stopy umožňují opakovaně použít 8/8 stop při čisté změně mixu a 7/8 při změně jediného nástroje.


## Oprava hlasitostního vývoje a živého ovládání (1.1)

Nové přímé měření celých 60 nahrávek používá třísekundové RMS okno po 0,5 s a práh 35 dB pod nejhlasitějším oknem. Medián rozdílu P90–P10 je 7,66 dB a úvod je mediánově 7,74 dB pod P90. Starý Future House měl kontrast jen 1,41 dB. Příčinou byla malá hlasitostní diferenciace částí spolu s adaptivní normalizací. Oprava používá konstantní masteringový zisk a limitaci špiček, žánrově mírné rozdíly částí a krátká prolínání jejich hranic. Future House dosáhl 6,70 dB, Melodic House 7,41 dB; noty obou porovnaných skladeb zůstaly stejné. Nejde o vnucení jednoho dynamického průběhu všem žánrům.

Hlasitostní průběh v UI má dvě vrstvy: RMS a peak. Zmizela mocninná komprese výšky sloupců, která vizuálně snižovala rozdíly. Shodné barvy propojují průběh s částmi skladby. Uživatel může hlasitost jednotlivých částí upravit a změna se použije ve zvuku i exportu.

Místo stereo přehrávače běží 8 synchronizovaných stop. Běžné mixové a efektové změny se aplikují přes AudioParam bez serverového renderu. Samplerová obálka a výměna nástroje se dopočítají pouze pro jednu stopu a krátce se prolnou ve stejné časové pozici. Stejný graf slouží k offline exportu; WAV neprochází další nezávislou normalizací. [Web Audio API](https://www.w3.org/TR/webaudio/).

## Vyvážení presetů a konec skladby

Po uživatelském poslechu byly zavedeny konkrétní maximální úrovně pro Silk, Glass, Orbit a vibrafony. Preference nejsou vydávány za univerzální práh nepříjemnosti. Další opatrné limity zohledňují roli, medián MIDI výšky a interval mezi nástupy not; nemění noty, harmonii ani rytmus. Dechový nástroj přenesený do basového rejstříku může mít nevhodnou barvu i při nízké úrovni, proto je takové použití v nabídce označené. Jeho automatický výběr do basové role se nepoužívá.

Broadband RMS není totéž jako frekvenčně vážené měření vnímané hlasitosti. Kontrola používá FFmpeg `loudnorm` / BS.1770 a spektrální energii skutečných zvuků. [AES: Loudness Basics](https://aes.org/resources/audio-topics/loudness-project/loudness-basics/), [ITU-R BS.1770](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-3-201208-S%21%21PDF-E.pdf). Měřená hlasitost sama neurčuje, zda bude konkrétní zvuk posluchači příjemný. Rozhodnutí o úrovni se vztahuje k roli v celé skladbě, nikoli jen k sólovému signálu; to odpovídá i doporučením pro práci s nástroji a frekvenčním prostorem v [Image-Line Mixing Advice](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/mixer_levelsandmixing.htm).

Skutečná analýza osmi presetů je v `balance-analysis.json`: například Silk 65→50 % změnil vstupní hlasitost o −2,29 LU, Glass 65→20 % o −10,24 LU a vibrafon 150→50 % přibližně o −9,54 LU. To jsou výsledky konkrétní testovací fráze, ne poslechové hodnocení.

Koncový volume jump měl přesnou implementační příčinu: pole gain obálky bylo vyplněné jedničkami a poslední část pokrývala jen úplné takty. Zbytek souboru tak dostal vyšší gain. Oprava dědí poslední úroveň do zbytku souboru a nové plány mají poslední část protaženou až k délce audia. Zkouška konstantním signálem i nativním Web Audio reprodukuje 6,00 dB před opravou a přibližně 0,00 dB po ní. Nevylučuje všechny možné hudební akcenty či nesoulad jiných presetů; odstraňuje konkrétní nechtěný gain skok.
