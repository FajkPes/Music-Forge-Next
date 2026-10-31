"""Conservative section contrast. Never normalize individual sections to equal loudness."""
DANCE={'intro':-5,'verse':-2.5,'verseB':-2,'build':-2,'chorus':0,'final':.3,'bridge':-5.5,'outro':-6}
ACOUSTIC={'intro':-2,'verse':-.8,'verseB':-.6,'build':-.5,'chorus':0,'final':.3,'bridge':-2.5,'outro':-3}

def section_db(plan,section):
    values=DANCE if plan['family'] in ['house','bass','dnb','retro','pop','rock','hiphop','world'] else ACOUSTIC
    return values.get(section['kind'],0)
