"""Genre-specific composition recipes; presets are real SoundFont bank/program pairs."""
from pathlib import Path
import struct
from functools import lru_cache
from titles import TITLE_BANKS,MOOD_WORDS,generate_title

ROOT=Path(__file__).resolve().parent
FAMILIES={
 'house': dict(rhythm='house',chords='offbeat',bass='offbeat',lead='hook',kit=26,palette=[81,89,38,98,80],swing=.02,extended=False,arp_min=.35,pad_min=0.),
 'bass': dict(rhythm='half',chords='pulse',bass='wobble_bass',lead='hook',kit=24,palette=[81,89,38,98,87],swing=.015,extended=False,arp_min=.35,pad_min=0.),
 'dnb': dict(rhythm='break',chords='long',bass='reese_bass',lead='flow',kit=26,palette=[81,4,38,89,98],swing=.02,extended=False,arp_min=.35,pad_min=0.),
 'retro': dict(rhythm='retro',chords='pulse',bass='octave',lead='hook',kit=24,palette=[81,89,38,90,80],swing=.015,extended=False,arp_min=.25,pad_min=0.),
 'pop': dict(rhythm='pop',chords='pulse',bass='pop',lead='sing',kit=0,palette=[0,4,33,89,24],swing=.025,extended=False,arp_min=.45,pad_min=0.),
 'rock': dict(rhythm='rock',chords='rock',bass='eighth',lead='sing',kit=16,palette=[29,30,34,48,27],swing=.02,extended=False,arp_min=.72,pad_min=.35),
 'hiphop': dict(rhythm='hiphop',chords='comp',bass='808',lead='sparse',kit=25,palette=[4,0,38,89,11],swing=.11,extended=True,arp_min=.72,pad_min=.20),
 'jazz': dict(rhythm='jazz',chords='comp',bass='walk',lead='flow',kit=32,palette=[0,4,32,49,11],swing=.20,extended=True,arp_min=.82,pad_min=.78),
 'acoustic': dict(rhythm='soft',chords='strum',bass='root',lead='sing',kit=40,palette=[25,0,32,49,46],swing=.035,extended=False,arp_min=.35,pad_min=.30),
 'classical': dict(rhythm='none',chords='alberti',bass='root',lead='classical',kit=48,palette=[0,48,42,49,46],swing=.01,extended=False,arp_min=.35,pad_min=0.),
 'ambient': dict(rhythm='none',chords='long',bass='root',lead='sparse',kit=40,palette=[89,0,39,91,46],swing=.01,extended=True,arp_min=.30,pad_min=0.),
 'world': dict(rhythm='bossa',chords='bossa',bass='latin',lead='flow',kit=40,palette=[24,0,33,49,12],swing=.04,extended=False,arp_min=.68,pad_min=.25),
}

# id, display name, recipe family, BPM, preferred mode, short audible identity
ROWS=[
 ('melodic-house','Melodic House','house',124,'minor','Jemný pluck, otevřené akordy a melodický návrat.'),
 ('progressive-house','Progressive House','house',128,'major','Dlouhá gradace, široké akordy a festivalový refrén.'),
 ('future-house','Future House','house',126,'minor','Krátké akordové staby, pružná basa a synkopy.'),
 ('deep-house','Deep House','house',120,'dorian','Měkké klávesy, septakordy a střídmý groove.'),
 ('bass-house','Bass House','house',128,'minor','Úderná basa, řídký hook a krátké odpovědi.'),
 ('tropical-house','Tropical House','house',108,'major','Marimba, lehké perkuse a vzdušný letní motiv.'),
 ('electro-house','Electro House','house',128,'minor','Ostré syntezátory, osminová basa a důrazné přechody.'),
 ('tech-house','Tech House','house',126,'dorian','Rytmické staby a perkuse s malým počtem tónů.'),
 ('slap-house','Slap House','house',124,'minor','Plná krátká basa a minimalistický taneční hook.'),
 ('future-bounce','Future Bounce','house',128,'major','Poskakující basová linka a synkopovaný motiv.'),
 ('festival-edm','Festival EDM','house',128,'major','Velká gradace, supersaw a dva kontrastní dropy.'),
 ('future-bass','Future Bass','bass',150,'major','Pulzující široké akordy a melodický half-time.'),
 ('melodic-dubstep','Melodic Dubstep','bass',144,'minor','Emotivní téma, half-time bicí a silný refrén.'),
 ('dubstep','Dubstep','bass',140,'minor','Half-time rytmus, modulovaná basa a odpovědi.'),
 ('chillstep','Chillstep','bass',136,'minor','Vzdušné plochy, klavír a klidný half-time.'),
 ('colour-bass','Colour Bass','bass',150,'major','Zvonivé vrstvy a barevné akordové synkopy.'),
 ('drumstep','Drumstep','bass',174,'minor','Rychlé hi-haty nad těžkým half-time rytmem.'),
 ('midtempo','Midtempo Bass','bass',100,'minor','Pomalý těžký puls a temná basová textura.'),
 ('liquid-dnb','Liquid Drum & Bass','dnb',174,'dorian','Tekoucí breakbeat, Rhodes a široké plochy.'),
 ('dance-dnb','Dancefloor Drum & Bass','dnb',174,'minor','Rychlý breakbeat a výrazný melodický hook.'),
 ('neurofunk','Neurofunk','dnb',172,'minor','Synkopovaná modulovaná basa a úsečné odpovědi.'),
 ('jungle','Jungle','dnb',166,'dorian','Rozlámaný rytmus a subbasa s řídkým doprovodem.'),
 ('synthwave','Synthwave','retro',100,'minor','Analogové klávesy, osminová basa a noční melodie.'),
 ('retrowave','Retrowave','retro',112,'major','Jasnější osmdesátkový zvuk a velký refrén.'),
 ('darksynth','Darksynth','retro',110,'minor','Temná osminová basa a agresivnější syntezátory.'),
 ('chillwave','Chillwave','retro',92,'major','Zasněné klávesy, měkký rytmus a dlouhé dozvuky.'),
 ('trance','Trance','house',138,'minor','Šestnáctinové arpeggio a dlouhá melodická gradace.'),
 ('psytrance','Psytrance','house',142,'phrygian','Krátká šestnáctinová basa a hypnotické arpeggio.'),
 ('techno','Melodic Techno','house',126,'minor','Stálý puls, modulace a postupný vývoj textury.'),
 ('uk-garage','UK Garage','house',132,'dorian','Dvoukrokový rytmus a výrazný shuffle.'),
 ('pop','Pop','pop',112,'major','Zpěvná instrumentální melodie, sloka a refrén.'),
 ('dance-pop','Dance Pop','pop',122,'major','Přehledný taneční rytmus a krátký zapamatovatelný hook.'),
 ('kpop','K-Pop · instrumental','pop',118,'minor','Kontrastní sloka, předrefrén a změna textury v bridge.'),
 ('indie-pop','Indie Pop','pop',104,'major','Kytary, jemné klávesy a přirozenější rytmus.'),
 ('electropop','Electropop','pop',116,'minor','Elektronický groove a jasná popová melodie.'),
 ('disco','Disco / Nu Disco','pop',118,'dorian','Oktávová basa, klávesy a rytmické kytary.'),
 ('rock','Rock','rock',128,'minor','Kytarové riffy, živé bicí a kontrastní refrén.'),
 ('pop-rock','Pop Rock','rock',124,'major','Zpěvná melodie nad kytarami a basou.'),
 ('indie-rock','Indie Rock','rock',138,'dorian','Kytarové odpovědi a střídmější harmonická textura.'),
 ('post-rock','Post Rock','rock',92,'major','Delší kytarové tóny a postupné přibývání vrstev.'),
 ('punk-rock','Punk Rock','rock',168,'major','Rychlé osminy, power akordy a úsporný motiv.'),
 ('hiphop','Hip Hop','hiphop',90,'minor','Backbeat, basová synkopa a klávesový motiv.'),
 ('lofi','Lo-fi Hip Hop','hiphop',78,'dorian','Rhodes, swing, jazzové akordy a měkké bicí.'),
 ('trap','Trap','hiphop',140,'minor','Half-time snare, hi-hat rolly a dlouhá subbasa.'),
 ('phonk','Phonk','hiphop',130,'minor','Krátký zvonivý motiv a úderný rytmus.'),
 ('rnb','R&B / Neo Soul','hiphop',86,'dorian','Rozšířené akordy, prostor a živější basová linka.'),
 ('jazz','Jazz Quartet','jazz',122,'dorian','Chůze basy, swing a odpovědi saxofonu.'),
 ('smooth-jazz','Smooth Jazz','jazz',96,'major','Rhodes, měkká basa a zpěvná saxofonová linka.'),
 ('funk','Funk','jazz',108,'dorian','Šestnáctinové synkopy a rytmická basa.'),
 ('bossa','Bossa Nova','world',128,'major','Nylonová kytara, latinská basa a lehké perkuse.'),
 ('reggaeton','Reggaeton','world',96,'minor','Dembow, krátké kytarové akordy a taneční hook.'),
 ('afro-house','Afro House','world',120,'minor','Vrstvené perkuse, mallety a stálý taneční puls.'),
 ('acoustic','Acoustic Folk','acoustic',92,'major','Prstová kytara, jemná basa a flétnový motiv.'),
 ('piano','Solo Piano','classical',82,'major','Klavírní motivy, vedení hlasů a přirozená dynamika.'),
 ('classical','Classical Chamber','classical',104,'major','Komorní smyčce, otázka a odpověď, kadence.'),
 ('cinematic','Cinematic Orchestral','classical',96,'minor','Smyčce, klavír a postupně rostoucí orchestrace.'),
 ('ambient','Ambient','ambient',70,'major','Pomalé harmonické plochy a řídké zvonivé motivy.'),
 ('chillout','Chillout / Downtempo','ambient',88,'dorian','Klidný rytmus, dlouhé akordy a prostor.'),
]

MOOD_ROWS=[
 ('uplifting','Povznášející',.78,.8),('happy','Radostná',.72,.98),('energetic','Energická',.96,.65),
 ('euphoric','Euforická',.94,.9),('playful','Hravá',.65,.9),('hopeful','Nadějná',.58,.72),
 ('dreamy','Zasněná',.35,.62),('calm','Klidná',.22,.65),('relaxed','Uvolněná',.3,.7),
 ('melancholic','Melancholická',.4,.24),('sad','Smutná',.25,.08),('emotional','Emotivní',.6,.35),
 ('nostalgic','Nostalgická',.42,.42),('romantic','Romantická',.4,.7),('dark','Temná',.67,.08),
 ('mysterious','Tajemná',.35,.2),('tense','Napjatá',.78,.18),('aggressive','Agresivní',.98,.12),
 ('epic','Epická',.87,.6),('heroic','Hrdinská',.84,.82),('groovy','Groovy',.7,.67),
 ('focused','Na soustředění',.32,.5),('cinematic','Filmová',.65,.45),('bittersweet','Hořkosladká',.5,.4)
]
MOODS=[dict(id=i,name=n,energy=e,valence=v,title_words=MOOD_WORDS[i]) for i,n,e,v in MOOD_ROWS]
RECOMMENDED={
 'house':['uplifting','energetic','euphoric','groovy','happy'],
 'bass':['emotional','epic','energetic','dark','euphoric'],
 'dnb':['energetic','uplifting','dreamy','dark','groovy'],
 'retro':['nostalgic','dreamy','dark','hopeful','energetic'],
 'pop':['happy','emotional','playful','romantic','bittersweet'],
 'rock':['energetic','aggressive','heroic','emotional','hopeful'],
 'hiphop':['groovy','relaxed','dark','melancholic','focused'],
 'jazz':['groovy','relaxed','romantic','playful','calm'],
 'world':['happy','groovy','playful','relaxed','energetic'],
 'acoustic':['hopeful','romantic','calm','melancholic','nostalgic'],
 'classical':['emotional','epic','calm','melancholic','heroic'],
 'ambient':['dreamy','calm','focused','mysterious','relaxed']}

PROFILE_EDITS={
 'melodic-house':dict(chords='house_piano',bass='offbeat',extended=True,arp_min=.30),
 'progressive-house':dict(chords='long',bass='octave',arp_min=.30),
 'future-house':dict(chords='stab',bass='slap',swing=.03,arp_min=.55),
 'deep-house':dict(chords='comp',lead='flow',bass='pop',extended=True,arp_min=.68,recommended=['groovy','relaxed','dreamy','romantic','calm']),
 'bass-house':dict(chords='stab',lead='riff',bass='wobble_bass',arp_min=.72),
 'tropical-house':dict(chords='offbeat',bass='pop',lead='hook',swing=.04,extended=True,arp_min=.35),
 'electro-house':dict(chords='pulse',bass='eighth',lead='riff',arp_min=.40),
 'tech-house':dict(chords='stab',bass='funk',lead='sparse',arp_min=.68),
 'slap-house':dict(chords='long',bass='slap',lead='hook',arp_min=.68),
 'future-bounce':dict(chords='offbeat',bass='slap',lead='flow',arp_min=.45),
 'festival-edm':dict(chords='pulse',bass='offbeat',lead='hook',arp_min=.35),
 'future-bass':dict(rhythm='half',chords='future',bass='sync',lead='hook',extended=True,arp_min=.30),
 'melodic-dubstep':dict(rhythm='half',chords='long',bass='wobble_bass',lead='sing',arp_min=.38),
 'dubstep':dict(rhythm='dubstep',chords='stab',bass='wobble_bass',lead='riff',arp_min=.72),
 'chillstep':dict(rhythm='half',chords='long',bass='reese_bass',lead='sparse',extended=True,arp_min=.35,recommended=['dreamy','calm','emotional','melancholic','hopeful']),
 'colour-bass':dict(rhythm='half',chords='future',bass='wobble_bass',lead='flow',extended=True,arp_min=.28),
 'drumstep':dict(rhythm='drumstep',chords='pulse',bass='wobble_bass',lead='hook',arp_min=.50),
 'midtempo':dict(rhythm='dubstep',chords='long',lead='riff',bass='eighth',arp_min=.60),
 'liquid-dnb':dict(rhythm='break',chords='long',bass='reese_bass',lead='flow',extended=True,arp_min=.38,recommended=['dreamy','uplifting','emotional','relaxed','groovy']),
 'dance-dnb':dict(rhythm='break',chords='pulse',bass='reese_bass',lead='hook',arp_min=.35),
 'neurofunk':dict(rhythm='break',chords='stab',bass='wobble_bass',lead='riff',arp_min=.72),
 'jungle':dict(rhythm='jungle',lead='sparse',bass='reese_bass',chords='comp',extended=True,arp_min=.72),
 'synthwave':dict(rhythm='retro',chords='long',bass='octave',lead='hook',arp_min=.25),
 'retrowave':dict(rhythm='retro',chords='offbeat',bass='octave',lead='sing',arp_min=.25),
 'darksynth':dict(rhythm='retro',chords='pulse',lead='riff',bass='eighth',arp_min=.25,recommended=['dark','aggressive','tense','mysterious','energetic']),
 'chillwave':dict(rhythm='soft',chords='long',bass='pop',lead='sparse',extended=True,arp_min=.35),
 'trance':dict(rhythm='trance',chords='long',bass='offbeat',lead='hook',arp_min=.15),
 'psytrance':dict(rhythm='trance',bass='psy',chords='long',lead='riff',arp_min=.15),
 'techno':dict(rhythm='house',chords='long',bass='eighth',lead='sparse',arp_min=.20),
 'uk-garage':dict(rhythm='garage',swing=.15,chords='stab',bass='sync',lead='flow',extended=True,arp_min=.68),
 'pop':dict(rhythm='pop',chords='pulse',bass='pop',lead='sing',arp_min=.45),
 'dance-pop':dict(rhythm='house',chords='house_piano',bass='pop',lead='hook',arp_min=.35),
 'kpop':dict(rhythm='pop',chords='stab',bass='slap',lead='hook',arp_min=.38),
 'indie-pop':dict(rhythm='soft',chords='strum',bass='pop',lead='sing',extended=True,arp_min=.45),
 'electropop':dict(rhythm='house',chords='offbeat',bass='octave',lead='hook',arp_min=.30),
 'disco':dict(rhythm='house',chords='funk',bass='octave',lead='flow',extended=True,arp_min=.55),
 'rock':dict(rhythm='rock',chords='rock',bass='eighth',lead='sing',arp_min=.75,pad_min=.45),
 'pop-rock':dict(rhythm='rock',chords='strum',bass='eighth',lead='sing',arp_min=.55,pad_min=.35),
 'indie-rock':dict(rhythm='rock',chords='pulse',bass='octave',lead='sing',arp_min=.48,pad_min=.45),
 'post-rock':dict(rhythm='postrock',chords='postrock',bass='root',lead='sparse',arp_min=.25,pad_min=0.,recommended=['hopeful','emotional','cinematic','melancholic','epic']),
 'punk-rock':dict(rhythm='punk',chords='punk',bass='eighth',lead='riff',swing=.01,arp_min=.88,pad_min=.88),
 'hiphop':dict(rhythm='hiphop',chords='comp',bass='808',lead='sparse',swing=.10,extended=True,arp_min=.72),
 'lofi':dict(rhythm='lofi',chords='comp',bass='pop',lead='sparse',swing=.14,extended=True,arp_min=.74,recommended=['relaxed','focused','nostalgic','melancholic','calm']),
 'trap':dict(rhythm='trap',lead='sparse',chords='long',bass='808',swing=.02,extended=False,arp_min=.38),
 'phonk':dict(rhythm='phonk',chords='long',bass='808',lead='riff',swing=.02,extended=False,arp_min=.74),
 'rnb':dict(rhythm='hiphop',chords='comp',bass='pop',lead='sing',swing=.08,extended=True,arp_min=.70,recommended=['romantic','groovy','relaxed','emotional','bittersweet']),
 'jazz':dict(rhythm='jazz',chords='comp',bass='walk',lead='flow',swing=.20,extended=True,arp_min=.85,pad_min=.82),
 'smooth-jazz':dict(rhythm='smooth_jazz',chords='comp',lead='sing',bass='pop',swing=.06,extended=True,arp_min=.75,pad_min=.20),
 'funk':dict(rhythm='funk',chords='funk',bass='funk',lead='riff',swing=.05,extended=True,arp_min=.72,pad_min=.45),
 'bossa':dict(rhythm='bossa',chords='bossa',bass='latin',lead='flow',swing=.035,extended=True,arp_min=.76,pad_min=.35),
 'reggaeton':dict(rhythm='dembow',chords='reggaeton',bass='dembow',lead='hook',swing=.02,extended=False,arp_min=.68,pad_min=.25),
 'afro-house':dict(rhythm='afro',chords='offbeat',bass='pop',lead='flow',swing=.035,extended=True,arp_min=.30,pad_min=0.),
 'acoustic':dict(rhythm='soft',chords='strum',bass='root',lead='sing',swing=.035,extended=False,arp_min=.35,pad_min=.30),
 'piano':dict(rhythm='none',chords='piano_solo',bass='root',lead='classical',swing=.015,extended=False,arp_min=1.1,pad_min=1.1,recommended=['emotional','calm','melancholic','romantic','hopeful']),
 'classical':dict(rhythm='none',chords='alberti',bass='root',lead='classical',swing=.01,extended=False,arp_min=.35,pad_min=.15),
 'cinematic':dict(rhythm='cinematic',chords='long',bass='root',lead='sing',swing=.01,extended=False,arp_min=.30,pad_min=0.,recommended=['epic','heroic','cinematic','emotional','tense']),
 'ambient':dict(rhythm='none',chords='long',bass='root',lead='sparse',swing=.005,extended=True,arp_min=.30,pad_min=0.),
 'chillout':dict(rhythm='soft',chords='long',bass='pop',lead='sparse',swing=.03,extended=True,arp_min=.38,pad_min=0.),
}

# Authentic, handcrafted multi-instrument palettes for every single genre.
GENRE_POOLS={
 'melodic-house':dict(drums=['sf:128:26','sf:128:25'],bass=['syn:round-bass','syn:reese','syn:sub'],chords=['syn:soft-saw','ms:8:0','syn:analog-pad'],lead=['syn:warm-pluck','syn:silk-pluck','piano:0:0'],counter=['syn:soft-pulse','syn:chime','syn:glass-pluck'],pad=['syn:dream-pad','syn:drift','syn:analog-pad'],arp=['syn:warm-pluck','syn:arp','syn:silk-pluck'],fx=['syn:noise-rise']),
 'progressive-house':dict(drums=['sf:128:26','sf:128:25'],bass=['syn:round-bass','syn:reese'],chords=['syn:supersaw','syn:soft-saw','piano:0:0'],lead=['syn:supersaw','syn:soft-saw','syn:warm-pluck'],counter=['piano:0:0','syn:silk-pluck','syn:shimmer'],pad=['syn:analog-pad','syn:strings','syn:dream-pad'],arp=['syn:arp','syn:silk-pluck'],fx=['syn:noise-rise']),
 'future-house':dict(drums=['sf:128:26','sf:128:25'],bass=['syn:fm-bass','syn:slap-bass','syn:round-bass'],chords=['syn:chord-stab','piano:0:0','syn:soft-saw'],lead=['syn:warm-pluck','syn:chord-stab','syn:silk-pluck'],counter=['syn:soft-pulse','syn:glass-pluck'],pad=['syn:dream-pad','syn:analog-pad'],arp=['syn:silk-pluck','syn:arp'],fx=['syn:noise-rise']),
 'deep-house':dict(drums=['sf:128:26','sf:128:25'],bass=['syn:round-bass','syn:sub','syn:fm-bass'],chords=['syn:rhodes','ms:0:4','syn:organ'],lead=['syn:warm-pluck','syn:soft-pulse','ms:0:66'],counter=['syn:rhodes','syn:soft-pulse','ms:0:11'],pad=['syn:dream-pad','syn:analog-pad'],arp=['syn:warm-pluck','syn:rhodes'],fx=['syn:noise-rise']),
 'bass-house':dict(drums=['sf:128:26','sf:128:24'],bass=['syn:growl','syn:fm-bass','syn:acid'],chords=['syn:chord-stab','syn:soft-saw'],lead=['syn:retro-lead','syn:square-lead','syn:brass'],counter=['syn:fm-bass','syn:soft-pulse'],pad=['syn:analog-pad','syn:drift'],arp=['syn:arp','syn:square-lead'],fx=['syn:noise-rise']),
 'tropical-house':dict(drums=['sf:128:26','ms:128:0'],bass=['syn:round-bass','syn:sub'],chords=['piano:0:0','ms:0:24','ms:0:4'],lead=['syn:tropical','ms:0:12','ms:0:75','ms:0:114'],counter=['ms:0:73','ms:0:108','syn:tropical'],pad=['syn:dream-pad','ms:0:89'],arp=['ms:0:24','ms:0:108','syn:warm-pluck'],fx=['syn:noise-rise']),
 'electro-house':dict(drums=['sf:128:24','sf:128:26'],bass=['syn:fm-bass','syn:acid','syn:growl'],chords=['syn:supersaw','syn:chord-stab'],lead=['syn:square-lead','syn:retro-lead','syn:supersaw'],counter=['syn:soft-pulse','syn:arp'],pad=['syn:analog-pad','syn:strings'],arp=['syn:arp','syn:square-lead'],fx=['syn:noise-rise']),
 'tech-house':dict(drums=['sf:128:25','sf:128:26'],bass=['syn:round-bass','syn:sub','syn:fm-bass'],chords=['syn:chord-stab','syn:organ'],lead=['syn:warm-pluck','syn:acid','syn:soft-pulse'],counter=['syn:chord-stab','syn:soft-pulse'],pad=['syn:drift','syn:analog-pad'],arp=['syn:warm-pluck','syn:arp'],fx=['syn:noise-rise']),
 'slap-house':dict(drums=['sf:128:26','sf:128:25'],bass=['syn:slap-bass','syn:fm-bass'],chords=['syn:analog-pad','ms:8:0','syn:soft-saw'],lead=['syn:warm-pluck','syn:silk-pluck','ms:0:42'],counter=['syn:soft-pulse','piano:0:0'],pad=['syn:dream-pad','syn:choir-pad'],arp=['syn:warm-pluck','syn:silk-pluck'],fx=['syn:noise-rise']),
 'future-bounce':dict(drums=['sf:128:26','sf:128:24'],bass=['syn:slap-bass','syn:fm-bass','syn:round-bass'],chords=['syn:chord-stab','syn:supersaw','piano:0:0'],lead=['syn:supersaw','syn:silk-pluck','syn:square-lead'],counter=['syn:warm-pluck','syn:chime'],pad=['syn:analog-pad','syn:dream-pad'],arp=['syn:arp','syn:silk-pluck'],fx=['syn:noise-rise']),
 'festival-edm':dict(drums=['sf:128:26','sf:128:24'],bass=['syn:round-bass','syn:sub','syn:fm-bass'],chords=['syn:supersaw','piano:0:0'],lead=['syn:supersaw','syn:brass'],counter=['piano:0:0','syn:silk-pluck'],pad=['syn:analog-pad','syn:strings'],arp=['syn:arp','syn:silk-pluck'],fx=['syn:noise-rise']),
 'future-bass':dict(drums=['sf:128:24','sf:128:26'],bass=['syn:sub','syn:reese','syn:round-bass'],chords=['syn:wobble-pad','syn:supersaw'],lead=['syn:supersaw','syn:silk-pluck','syn:square-lead'],counter=['syn:chime','syn:bell','piano:0:0'],pad=['syn:dream-pad','syn:shimmer'],arp=['syn:arp','syn:chime','syn:silk-pluck'],fx=['syn:noise-rise']),
 'melodic-dubstep':dict(drums=['sf:128:16','sf:128:24'],bass=['syn:growl','syn:reese','syn:sub'],chords=['syn:supersaw','syn:wobble-pad'],lead=['syn:supersaw','piano:0:0','syn:soft-saw'],counter=['piano:0:0','syn:chime','ms:0:40'],pad=['syn:choir-pad','syn:strings','syn:dream-pad'],arp=['piano:0:0','syn:silk-pluck'],fx=['syn:noise-rise']),
 'dubstep':dict(drums=['sf:128:24','sf:128:16'],bass=['syn:growl','syn:fm-bass','syn:reese'],chords=['syn:chord-stab','syn:brass'],lead=['syn:retro-lead','syn:square-lead','syn:growl'],counter=['syn:fm-bass','syn:bell'],pad=['syn:drift','syn:analog-pad'],arp=['syn:arp','syn:square-lead'],fx=['syn:noise-rise']),
 'chillstep':dict(drums=['sf:128:24','ms:128:8'],bass=['syn:sub','syn:reese'],chords=['piano:0:0','ms:8:0','syn:dream-pad'],lead=['piano:0:0','syn:soft-pulse','ms:0:40'],counter=['syn:shimmer','syn:chime'],pad=['syn:dream-pad','syn:drift','syn:choir-pad'],arp=['piano:0:0','syn:warm-pluck'],fx=['syn:noise-rise']),
 'colour-bass':dict(drums=['sf:128:24','sf:128:26'],bass=['syn:growl','syn:fm-bass','syn:reese'],chords=['syn:shimmer','syn:wobble-pad','syn:supersaw'],lead=['syn:chime','syn:bell','syn:silk-pluck'],counter=['syn:shimmer','syn:glass-pluck'],pad=['syn:dream-pad','syn:shimmer'],arp=['syn:chime','syn:arp','syn:glass-pluck'],fx=['syn:noise-rise']),
 'drumstep':dict(drums=['sf:128:16','sf:128:24'],bass=['syn:growl','syn:reese','syn:fm-bass'],chords=['syn:supersaw','syn:chord-stab'],lead=['syn:supersaw','syn:retro-lead','syn:square-lead'],counter=['syn:soft-pulse','syn:arp'],pad=['syn:analog-pad','syn:strings'],arp=['syn:arp','syn:retro-lead'],fx=['syn:noise-rise']),
 'midtempo':dict(drums=['sf:128:24','sf:128:16'],bass=['syn:growl','syn:fm-bass','syn:acid'],chords=['syn:analog-pad','syn:brass'],lead=['syn:retro-lead','syn:brass','syn:acid'],counter=['syn:soft-pulse','syn:bell'],pad=['syn:drift','syn:analog-pad'],arp=['syn:retro-lead','syn:arp'],fx=['syn:noise-rise']),
 'liquid-dnb':dict(drums=['ms:128:0','sf:128:26'],bass=['syn:reese','syn:sub'],chords=['syn:rhodes','ms:0:4','piano:0:0'],lead=['piano:0:0','syn:soft-pulse','syn:warm-pluck'],counter=['syn:shimmer','ms:0:65','syn:rhodes'],pad=['syn:dream-pad','syn:drift','syn:strings'],arp=['piano:0:0','syn:warm-pluck'],fx=['syn:noise-rise']),
 'dance-dnb':dict(drums=['sf:128:16','sf:128:26'],bass=['syn:reese','syn:fm-bass'],chords=['syn:supersaw','piano:0:0'],lead=['syn:supersaw','syn:soft-saw','syn:brass'],counter=['piano:0:0','syn:silk-pluck'],pad=['syn:analog-pad','syn:strings'],arp=['syn:arp','syn:silk-pluck'],fx=['syn:noise-rise']),
 'neurofunk':dict(drums=['sf:128:16','sf:128:24'],bass=['syn:growl','syn:reese','syn:fm-bass'],chords=['syn:analog-pad','syn:drift'],lead=['syn:retro-lead','syn:acid','syn:fm-bass'],counter=['syn:soft-pulse','syn:growl'],pad=['syn:drift','syn:analog-pad'],arp=['syn:retro-lead','syn:arp'],fx=['syn:noise-rise']),
 'jungle':dict(drums=['sf:128:0','ms:128:8'],bass=['syn:sub','syn:reese'],chords=['syn:rhodes','syn:chord-stab','ms:0:4'],lead=['syn:soft-pulse','ms:0:73','syn:warm-pluck'],counter=['syn:chime','syn:chord-stab'],pad=['syn:dream-pad','syn:drift','ms:0:89'],arp=['syn:warm-pluck','syn:rhodes'],fx=['syn:noise-rise']),
 'synthwave':dict(drums=['sf:128:24','sf:128:16'],bass=['syn:round-bass','syn:fm-bass'],chords=['syn:analog-pad','syn:brass','syn:strings'],lead=['syn:retro-lead','syn:brass','syn:soft-saw'],counter=['syn:bell','syn:soft-pulse'],pad=['syn:strings','syn:analog-pad'],arp=['syn:warm-pluck','syn:arp'],fx=['syn:noise-rise']),
 'retrowave':dict(drums=['sf:128:24','sf:128:16'],bass=['syn:round-bass','syn:slap-bass','syn:fm-bass'],chords=['syn:brass','syn:soft-saw','ms:0:5'],lead=['syn:retro-lead','syn:supersaw','ms:0:65'],counter=['ms:0:5','syn:bell'],pad=['syn:analog-pad','syn:strings'],arp=['syn:arp','syn:warm-pluck'],fx=['syn:noise-rise']),
 'darksynth':dict(drums=['sf:128:16','sf:128:24'],bass=['syn:fm-bass','syn:growl','syn:acid'],chords=['syn:brass','syn:supersaw','ms:0:19'],lead=['syn:retro-lead','syn:square-lead','syn:brass'],counter=['syn:acid','syn:soft-pulse'],pad=['syn:choir-pad','syn:analog-pad'],arp=['syn:arp','syn:retro-lead'],fx=['syn:noise-rise']),
 'chillwave':dict(drums=['sf:128:24','ms:128:25'],bass=['syn:round-bass','syn:sub'],chords=['syn:analog-pad','syn:rhodes','ms:8:4'],lead=['syn:soft-pulse','syn:warm-pluck','sf:8:27'],counter=['syn:shimmer','syn:chime'],pad=['syn:dream-pad','syn:drift'],arp=['syn:warm-pluck','syn:shimmer'],fx=['syn:noise-rise']),
 'trance':dict(drums=['sf:128:26','sf:128:25'],bass=['syn:round-bass','syn:reese'],chords=['syn:supersaw','syn:strings','syn:analog-pad'],lead=['syn:supersaw','syn:soft-saw'],counter=['piano:0:0','syn:shimmer'],pad=['syn:choir-pad','syn:dream-pad','syn:strings'],arp=['syn:arp','syn:silk-pluck','syn:warm-pluck'],fx=['syn:noise-rise']),
 'psytrance':dict(drums=['sf:128:25','sf:128:26'],bass=['syn:acid','syn:round-bass'],chords=['syn:analog-pad','syn:drift'],lead=['syn:acid','syn:retro-lead','syn:square-lead'],counter=['syn:soft-pulse','syn:shimmer'],pad=['syn:drift','syn:choir-pad'],arp=['syn:arp','syn:retro-lead'],fx=['syn:noise-rise']),
 'techno':dict(drums=['sf:128:25','sf:128:24'],bass=['syn:reese','syn:round-bass','syn:acid'],chords=['syn:analog-pad','syn:soft-saw'],lead=['syn:warm-pluck','syn:retro-lead','syn:soft-saw'],counter=['syn:soft-pulse','syn:shimmer'],pad=['syn:drift','syn:analog-pad'],arp=['syn:warm-pluck','syn:arp'],fx=['syn:noise-rise']),
 'uk-garage':dict(drums=['sf:128:26','ms:128:0'],bass=['syn:sub','syn:fm-bass','syn:round-bass'],chords=['syn:organ','syn:rhodes','syn:chord-stab'],lead=['syn:warm-pluck','syn:silk-pluck','syn:soft-pulse'],counter=['syn:rhodes','syn:chime'],pad=['syn:dream-pad','syn:analog-pad'],arp=['syn:warm-pluck','syn:rhodes'],fx=['syn:noise-rise']),
 'pop':dict(drums=['ms:128:0','sf:128:26'],bass=['ms:0:33','syn:round-bass'],chords=['piano:0:0','ms:0:25','ms:0:4'],lead=['syn:warm-pluck','piano:0:0','ms:0:27'],counter=['syn:soft-pulse','ms:0:25'],pad=['syn:dream-pad','ms:0:49'],arp=['ms:0:25','syn:warm-pluck'],fx=['syn:noise-rise']),
 'dance-pop':dict(drums=['sf:128:26','sf:128:25'],bass=['syn:round-bass','syn:slap-bass','ms:0:37'],chords=['piano:0:0','syn:chord-stab','syn:soft-saw'],lead=['syn:silk-pluck','syn:warm-pluck','syn:soft-saw'],counter=['syn:soft-pulse','syn:chime'],pad=['syn:dream-pad','syn:analog-pad'],arp=['syn:silk-pluck','syn:arp'],fx=['syn:noise-rise']),
 'kpop':dict(drums=['sf:128:26','sf:128:24'],bass=['syn:slap-bass','syn:fm-bass','syn:round-bass'],chords=['syn:chord-stab','piano:0:0','syn:wobble-pad'],lead=['syn:silk-pluck','syn:supersaw','syn:brass'],counter=['syn:chime','syn:glass-pluck'],pad=['syn:shimmer','syn:dream-pad'],arp=['syn:arp','syn:silk-pluck'],fx=['syn:noise-rise']),
 'indie-pop':dict(drums=['ms:128:0','ms:128:8'],bass=['ms:0:33','ms:0:34'],chords=['sf:8:27','ms:0:25','ms:8:4'],lead=['sf:8:27','syn:soft-pulse','piano:0:0'],counter=['syn:warm-pluck','ms:0:27'],pad=['syn:dream-pad','syn:analog-pad'],arp=['ms:0:27','syn:warm-pluck'],fx=['syn:noise-rise']),
 'electropop':dict(drums=['sf:128:24','sf:128:26'],bass=['syn:round-bass','syn:fm-bass'],chords=['syn:soft-saw','syn:analog-pad','syn:chord-stab'],lead=['syn:warm-pluck','syn:retro-lead','syn:silk-pluck'],counter=['syn:soft-pulse','syn:chime'],pad=['syn:analog-pad','syn:dream-pad'],arp=['syn:arp','syn:warm-pluck'],fx=['syn:noise-rise']),
 'disco':dict(drums=['sf:128:26','ms:128:0'],bass=['ms:0:36','ms:0:33','syn:slap-bass'],chords=['ms:8:28','ms:0:4','ms:0:7'],lead=['ms:0:61','syn:brass','ms:0:48'],counter=['ms:8:28','ms:0:48'],pad=['ms:0:49','syn:strings'],arp=['ms:8:28','syn:warm-pluck'],fx=['syn:noise-rise']),
 'rock':dict(drums=['ms:128:16','sf:128:16','ms:128:8'],bass=['ms:0:34','ms:0:33'],chords=['ms:0:30','ms:0:29'],lead=['ms:0:29','ms:0:30'],counter=['ms:0:27','ms:0:18'],pad=['ms:0:18','syn:analog-pad'],arp=['ms:0:27','ms:0:28'],fx=['syn:noise-rise']),
 'pop-rock':dict(drums=['ms:128:16','ms:128:0'],bass=['ms:0:33','ms:0:34'],chords=['ms:0:29','ms:0:25','piano:0:0'],lead=['ms:0:29','ms:0:27','piano:0:0'],counter=['ms:0:27','piano:0:0'],pad=['ms:0:16','syn:dream-pad'],arp=['ms:0:27','ms:0:25'],fx=['syn:noise-rise']),
 'indie-rock':dict(drums=['ms:128:8','ms:128:0'],bass=['ms:0:34','ms:0:33'],chords=['ms:0:29','sf:8:27','ms:0:27'],lead=['sf:8:27','ms:0:29','ms:0:27'],counter=['ms:0:27','ms:0:16'],pad=['ms:0:16','syn:analog-pad'],arp=['sf:8:27','ms:0:27'],fx=['syn:noise-rise']),
 'post-rock':dict(drums=['ms:128:8','ms:128:16'],bass=['ms:0:33','ms:0:34'],chords=['sf:8:27','ms:0:44','ms:0:29'],lead=['sf:8:27','ms:0:44','piano:0:0'],counter=['piano:0:0','ms:0:42'],pad=['syn:shimmer','ms:0:49','syn:drift'],arp=['ms:0:27','piano:0:0'],fx=['syn:noise-rise']),
 'punk-rock':dict(drums=['ms:128:16','sf:128:16'],bass=['ms:0:34'],chords=['ms:0:30','ms:0:29'],lead=['ms:0:29','ms:0:30'],counter=['ms:0:28','ms:0:29'],pad=['ms:0:18'],arp=['ms:0:28'],fx=['syn:noise-rise']),
 'hiphop':dict(drums=['ms:128:0','sf:128:25'],bass=['ms:0:33','syn:sub','syn:round-bass'],chords=['ms:0:4','piano:0:0','ms:8:4'],lead=['piano:0:0','ms:0:59','syn:soft-pulse'],counter=['ms:0:45','ms:0:11','ms:0:61'],pad=['ms:0:49','syn:analog-pad'],arp=['ms:0:46','piano:0:0'],fx=['syn:noise-rise']),
 'lofi':dict(drums=['ms:128:40','ms:128:0','sf:128:25'],bass=['ms:0:33','ms:0:32','syn:sub'],chords=['ms:8:4','ms:0:4','ms:8:0'],lead=['ms:8:0','ms:0:26','ms:0:59'],counter=['ms:0:26','ms:0:73','ms:0:11'],pad=['syn:dream-pad','syn:analog-pad'],arp=['ms:0:24','ms:0:108'],fx=['syn:noise-rise']),
 'trap':dict(drums=['ms:128:25','sf:128:25'],bass=['syn:sub'],chords=['ms:8:0','syn:analog-pad','ms:0:45'],lead=['syn:bell','ms:0:73','ms:8:0'],counter=['ms:0:73','syn:chime','syn:brass'],pad=['syn:choir-pad','syn:drift'],arp=['syn:bell','ms:0:46','syn:music-box'],fx=['syn:noise-rise']),
 'phonk':dict(drums=['ms:128:25','sf:128:25'],bass=['syn:sub','syn:growl','syn:fm-bass'],chords=['syn:analog-pad','syn:drift'],lead=['sf:0:113','syn:bell','syn:retro-lead'],counter=['syn:retro-lead','syn:brass'],pad=['syn:drift','syn:choir-pad'],arp=['syn:bell','syn:retro-lead'],fx=['syn:noise-rise']),
 'rnb':dict(drums=['ms:128:0','sf:128:25'],bass=['ms:0:33','syn:sub','ms:0:35'],chords=['ms:0:4','syn:rhodes','ms:8:4'],lead=['ms:0:26','syn:soft-pulse','ms:0:64'],counter=['syn:organ','ms:0:11','piano:0:0'],pad=['syn:dream-pad','ms:0:53'],arp=['ms:0:26','syn:rhodes'],fx=['syn:noise-rise']),
 'jazz':dict(drums=['ms:128:32','ms:128:40','sf:128:32'],bass=['ms:0:32'],chords=['piano:0:0','ms:0:4','ms:0:26'],lead=['ms:0:66','ms:0:65','ms:0:59','ms:0:26'],counter=['piano:0:0','ms:0:11','ms:0:56','ms:0:71'],pad=['ms:0:49','ms:0:16'],arp=['ms:0:26','ms:0:11'],fx=['syn:noise-rise']),
 'smooth-jazz':dict(drums=['ms:128:40','ms:128:0'],bass=['ms:0:35','ms:0:33'],chords=['ms:0:4','ms:0:5','syn:rhodes'],lead=['ms:0:64','ms:0:65','ms:0:26'],counter=['ms:0:26','piano:0:0','ms:0:73'],pad=['syn:dream-pad','ms:0:49'],arp=['ms:0:24','ms:0:26'],fx=['syn:noise-rise']),
 'funk':dict(drums=['ms:128:0','ms:128:8'],bass=['ms:0:36','ms:0:33','syn:slap-bass'],chords=['ms:0:7','ms:8:28','ms:0:4'],lead=['ms:0:61','ms:0:65','ms:0:56'],counter=['ms:8:28','ms:0:16','ms:0:61'],pad=['ms:0:16','syn:organ'],arp=['ms:8:28','ms:0:7'],fx=['syn:noise-rise']),
 'bossa':dict(drums=['ms:128:40','ms:128:32'],bass=['ms:0:32','ms:0:33'],chords=['ms:0:24','piano:0:0'],lead=['ms:0:73','ms:0:66','ms:0:24'],counter=['piano:0:0','ms:0:11'],pad=['ms:0:49','ms:8:48'],arp=['ms:0:24','piano:0:0'],fx=['syn:noise-rise']),
 'reggaeton':dict(drums=['ms:128:25','sf:128:25','sf:128:26'],bass=['syn:sub','syn:round-bass'],chords=['ms:0:24','syn:warm-pluck','syn:chord-stab'],lead=['syn:warm-pluck','syn:tropical','ms:0:24'],counter=['syn:silk-pluck','ms:0:12'],pad=['syn:analog-pad','syn:dream-pad'],arp=['syn:silk-pluck','ms:0:24'],fx=['syn:noise-rise']),
 'afro-house':dict(drums=['sf:128:26','sf:128:25'],bass=['syn:round-bass','syn:sub'],chords=['piano:0:0','syn:analog-pad','ms:0:4'],lead=['ms:0:12','ms:0:108','syn:tropical'],counter=['syn:warm-pluck','ms:0:75'],pad=['syn:drift','syn:dream-pad','syn:choir-pad'],arp=['ms:0:108','ms:0:12','syn:warm-pluck'],fx=['syn:noise-rise']),
 'acoustic':dict(drums=['ms:128:40','ms:128:0'],bass=['ms:0:32'],chords=['ms:0:25','ms:0:24','ms:8:25'],lead=['ms:0:25','ms:0:73','ms:0:40','ms:0:22'],counter=['piano:0:0','ms:0:42','ms:16:25'],pad=['ms:0:49','ms:0:21'],arp=['ms:0:24','ms:16:25','ms:0:46'],fx=['syn:noise-rise']),
 'piano':dict(drums=['sf:128:0'],bass=['piano:0:0'],chords=['piano:0:0'],lead=['piano:0:0'],counter=['piano:0:0'],pad=['piano:0:0'],arp=['piano:0:0'],fx=['piano:0:0']),
 'classical':dict(drums=['ms:128:48'],bass=['ms:0:42','ms:0:43','ms:40:49'],chords=['ms:0:48','piano:0:0','ms:30:48'],lead=['ms:0:40','ms:0:73','ms:0:68','piano:0:0'],counter=['ms:0:68','ms:0:71','ms:0:42','ms:0:73'],pad=['ms:0:49','ms:8:48'],arp=['ms:0:46','ms:0:45'],fx=['syn:noise-rise']),
 'cinematic':dict(drums=['ms:128:48','sf:128:48'],bass=['ms:50:49','ms:0:43','ms:40:49'],chords=['ms:0:49','ms:0:48','piano:0:0'],lead=['ms:0:60','ms:20:49','ms:0:42','piano:0:0'],counter=['piano:0:0','ms:0:68','ms:0:60','ms:0:73'],pad=['ms:0:52','ms:8:48','syn:choir-pad'],arp=['ms:0:46','piano:0:0','ms:0:45'],fx=['syn:noise-rise']),
 'ambient':dict(drums=['ms:128:40'],bass=['syn:sub','syn:round-bass','ms:40:49'],chords=['syn:dream-pad','syn:drift','ms:8:0'],lead=['ms:8:0','piano:0:0','syn:shimmer','syn:soft-pulse'],counter=['syn:chime','syn:shimmer','ms:0:46'],pad=['syn:drift','syn:choir-pad','ms:0:94'],arp=['syn:shimmer','ms:0:46','syn:chime'],fx=['syn:noise-rise']),
 'chillout':dict(drums=['ms:128:40','sf:128:25','ms:128:0'],bass=['syn:sub','syn:round-bass','ms:0:35'],chords=['ms:8:4','syn:rhodes','syn:dream-pad'],lead=['ms:8:0','syn:soft-pulse','ms:0:26','ms:0:73'],counter=['syn:chime','syn:warm-pluck','ms:0:11'],pad=['syn:dream-pad','syn:drift'],arp=['syn:warm-pluck','ms:0:24','ms:0:46'],fx=['syn:noise-rise']),
}

GENRES=[]
for i,name,fam,bpm,mode,description in ROWS:
    g=dict(FAMILIES[fam],id=i,name=name,family=fam,bpm=bpm,mode=mode,description=description,recommended=RECOMMENDED[fam],title_words=TITLE_BANKS[i])
    if i in PROFILE_EDITS:g.update(PROFILE_EDITS[i])
    GENRES.append(g)
GENRE_MAP={g['id']:g for g in GENRES}
MOOD_MAP={m['id']:m for m in MOODS}
GROUPS=['Piano','Chromatické perkuse','Varhany','Kytary','Basy','Smyčce','Ensemble','Žestě','Dechy','Flétny','Synth lead','Synth pad','Textury','Etnické','Perkuse','Efekty']

SYNTHS=[
 ('silk-pluck','Silk · pluck','pluck',.16,.15),('glass-pluck','Glass · pluck','fm',.35,.15),
 ('warm-pluck','Warm · analog pluck','pluck',.4,.1),('tropical','Tropic · mallet','fm',.12,.08),
 ('supersaw','Aurora · supersaw','saw',.6,.7),('soft-saw','Velvet · soft saw','saw',.22,.5),
 ('retro-lead','Neon · retro lead','pulse',.4,.2),('square-lead','Pixel · square lead','pulse',.65,.1),
 ('dream-pad','Cloud · dream pad','pad',.15,.8),('analog-pad','Horizon · analog pad','pad',.4,.6),
 ('choir-pad','Halo · choir pad','pad',.25,.8),('shimmer','Prism · shimmer','fm',.2,.8),
 ('sub','Deep · sine sub','sub',.05,0),('round-bass','Round · analog bass','bass',.2,.05),
 ('reese','Reese · moving bass','reese',.55,.2),('growl','Motion · growl bass','growl',.7,.2),
 ('slap-bass','Elastic · slap bass','bass',.7,.1),('acid','Acid · resonant bass','acid',.8,.05),
 ('rhodes','Dusk · FM keys','fm',.15,.4),('bell','Crystal · bell','bell',.5,.55),
 ('music-box','Lullaby · music box','bell',.15,.2),('organ','Solar · drawbar','organ',.5,.2),
 ('chord-stab','Bounce · chord stab','saw',.35,.12),('wobble-pad','Tide · future chords','pad',.65,.4),
 ('soft-pulse','Lumen · soft pulse','pulse',.1,.4),('fm-bass','Vector · FM bass','fm',.75,.03),
 ('drift','Drift · evolving pad','pad',.3,1),('arp','Orbit · bright arp','pluck',.7,.25),
 ('chime','Silver · chime','bell',.35,.7),('brass','Flare · synth brass','saw',.8,.3),
 ('strings','Aster · synth strings','pad',.55,.65),('noise-rise','Air · riser','noise',.5,.7)
]

def preset_headers(path):
    with path.open('rb') as f:
        f.seek(12)
        while header:=f.read(8):
            kind,size=struct.unpack('<4sI',header);start=f.tell()
            if kind==b'LIST' and f.read(4)==b'pdta':
                while f.tell()<start+size:
                    sub,n=struct.unpack('<4sI',f.read(8))
                    if sub==b'phdr':return f.read(n)
                    f.seek(n+n%2,1)
            f.seek(start+size+size%2)
    raise ValueError('SoundFont has no preset headers: '+str(path))

@lru_cache(maxsize=1)
def load_instruments():
    instruments=[]
    banks=[('sf',ROOT/'assets/GeneralUser-GS.sf2','GeneralUser GS 2.0.3')]
    ms=ROOT/'assets/musescore/MuseScore_General.sf2'
    if ms.exists():banks.append(('ms',ms,'MuseScore General · S. Christian Collins et al.'))
    for path in (ROOT/'assets/salamander').glob('*.sf2'):
        banks.append(('piano',path,'Salamander Grand Piano · Alexander Holm · CC BY 3.0'))
    seen=set()
    for prefix,path,source in banks:
      data=preset_headers(path)
      for offset in range(0,len(data)-38,38):
        name,program,bank,*_=struct.unpack_from('<20sHHHIII',data,offset)
        name=name.split(b'\0')[0].decode('latin1');id=f'{prefix}:{bank}:{program}'
        # GeneralUser mirrors its 13 kits in bank 120 for non-GM players; don't count those twice.
        if prefix=='sf' and bank==120:continue
        # The six marching presets use a proprietary, non-GM note map and are
        # not complete drum kits for the patterns exposed by this application.
        if prefix=='ms' and bank==128 and 'marching' in name.lower():continue
        if prefix=='piano':name='Salamander · Yamaha C5'
        if id in seen:continue
        seen.add(id)
        instruments.append(dict(id=id,name=name,bank=bank,program=program,sf_path=str(path.relative_to(ROOT)),
            group='Bicí sady' if bank==128 else GROUPS[min(program//8,15)],engine='sample',source=source))
    for id,name,kind,colour,width in SYNTHS:
        instruments.append(dict(id='syn:'+id,name=name,kind=kind,colour=colour,width=width,group='Moderní syntéza',engine='synth',source='Music Forge · vlastní syntéza'))
    from balance import instrument_limits
    for instrument in instruments:instrument['gain_limits']=instrument_limits(instrument)
    return instruments

def catalogue():
    return dict(genres=GENRES,moods=MOODS,title_banks=TITLE_BANKS,mood_words=MOOD_WORDS,instruments=load_instruments(),default=dict(genre='melodic-house',mood='uplifting',duration=210,seed=431207,bpm=124,key='auto',complexity=.55,variation=.65,humanize=.55,space=.35,energy=.78))
