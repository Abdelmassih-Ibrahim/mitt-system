from __future__ import annotations

from typing import Any


_TRANSLATIONS = {
    "Klart och soligt": "Clear and sunny",
    "Mestadels klart": "Mostly clear",
    "Växlande molnighet": "Partly cloudy",
    "Mulet": "Overcast",
    "Dimma": "Fog",
    "Dimma med frost": "Freezing fog",
    "Lätt duggregn": "Light drizzle",
    "Duggregn och regn": "Drizzle and rain",
    "Tätt duggregn": "Dense drizzle",
    "Underkylt duggregn": "Freezing drizzle",
    "Kraftigt underkylt duggregn": "Heavy freezing drizzle",
    "Lätt regn": "Light rain",
    "Regn": "Rain",
    "Kraftigt regn": "Heavy rain",
    "Underkylt regn": "Freezing rain",
    "Kraftigt underkylt regn": "Heavy freezing rain",
    "Lätt snöfall": "Light snow",
    "Snöfall": "Snowfall",
    "Kraftigt snöfall": "Heavy snow",
    "Snökorn": "Snow grains",
    "Regnskurar": "Rain showers",
    "Kraftiga regnskurar": "Heavy rain showers",
    "Snöbyar": "Snow showers",
    "Kraftiga snöbyar": "Heavy snow showers",
    "Åska": "Thunderstorm",
    "Åska och hagel": "Thunderstorm and hail",
    "Kraftig åska och hagel": "Severe thunderstorm and hail",
    "Klart i natt": "Clear tonight",
    "Molnig kväll": "Cloudy evening",
    "Väder på väg": "Weather incoming",
    "Väderbonus": "Glorious",
    "Ganska fint": "Pretty decent",
    "Jacka och plan": "Jacket weather",
    "Inomhus är rimligt": "Indoors is a valid choice",
    "Härligt ute. Ta vara på ljuset.": "Lovely outside. Make the most of the light.",
    "En lätt jacka räcker för många.": "A light jacket should do for most people.",
    "Kolla vinden och välj ett bra lager.": "Check the wind and choose a good layer.",
    "Välj utefönstret noga eller gör det mysigt inne.": "Pick your outdoor window carefully, or make indoors cosy.",
    "Kyla": "Cold",
    "Vind": "Wind",
    "Nederbörd": "Precipitation",
    "Åska": "Thunder risk",
    "Sikt": "Visibility",
    "Åska gör utomhusplaner olämpliga.": "Thunder makes outdoor plans unsuitable.",
    "Dimma försämrar sikten.": "Fog reduces visibility.",
    "Vädervetts uppskattning av utomhuskomfort, inte ett officiellt meteorologiskt mått.": "Vädervett's estimate of outdoor comfort, not an official meteorological measure.",
    "Vattentätt före allt annat.": "Waterproof first.",
    "Lager på lager vinner.": "Layers make the difference.",
    "Klä dig för en lång dag ute.": "Dress for a long day outside.",
    "Välj jacka med huva och skor som tål väta. Byt paraply mot en ledig hand om det blåser.": "Choose a hooded waterproof jacket and shoes that can handle wet ground. In strong wind, skip the umbrella.",
    "En varm tröja under skaljackan gör promenaden skönare. Ta gärna mössa om vinden tar i.": "A warm mid-layer under a shell makes a walk more comfortable. Add a hat if the wind picks up.",
    "Ta med ett extra lager så kan du stanna ute även när temperaturen skiftar.": "Bring an extra layer so you can stay out as the temperature changes.",
    "Huva slår paraply i blåst": "A hood beats an umbrella in wind",
    "Ett extra lager skadar aldrig": "An extra layer never hurts",
    "Lätt lager · stor frihet": "Light layers · more freedom",
    "Gör museet till utflykten.": "Make the museum the outing.",
    "Hitta lä bakom husen.": "Find shelter between the buildings.",
    "Ta omvägen genom parken.": "Take the scenic route through the park.",
    "Gör inomhuset till äventyret.": "Make indoors the adventure.",
    "Ta en omväg du inte planerat.": "Take an unplanned detour.",
    "Välj en utställning eller ett växthus och låt skuren dra förbi innan du går vidare.": "Choose an exhibition or greenhouse, and let the shower pass before heading on.",
    "En skogsdunge eller en gata med lä gör promenaden mycket trevligare när vinden tar i.": "A sheltered street or small grove makes a walk more pleasant when the wind picks up.",
    "En kort promenad före eftermiddagskaffet kan vara dagens bästa paus.": "A short walk before afternoon coffee may be the best break of the day.",
    "Välj ett växthus, litet galleri eller ett kafé du aldrig provat. Dagen behöver inte vara solig för att bli ny.": "Try a greenhouse, small gallery or café you have never visited. A day does not need sunshine to feel new.",
    "Välj ett museum, växthus eller en bio med matiné. Ta en helt vanlig tisdag och gör den till en liten utflykt.": "Choose a museum, greenhouse or matinee. Turn an ordinary day into a small outing.",
    "Vattentätt före allt annat.": "Waterproof first.",
    "En liten inomhusvärld att upptäcka.": "A little indoor world to discover.",
    "En liten inomhusvärld att upptäcka.": "A little indoor world to discover.",
    "En liten inomhusvärld att upptäcka.": "A little indoor world to discover.",
    "Sök skydd på ett kvarterskafé. Beställ något varmt och låt skuren passera.": "Take shelter in a neighbourhood café. Order something warm and let the shower pass.",
    "Hitta ett kafé med fönsterplats och se vädret sköta underhållningen.": "Find a café window seat and let the weather provide the show.",
    "En varm paus under tak nära till hands.": "A warm break under cover, close by.",
    "En fin omväg för dagens kaffepaus.": "A pleasant detour for today's coffee break.",
    "En liten inomhusvärld att upptäcka.": "A small indoor world to explore.",
    "En dörr du aldrig öppnat": "A door you have never opened",
    "Gå in på ett litet galleri, bokcafé eller växthus du annars hade gått förbi.": "Step into a small gallery, book café or greenhouse you would usually pass by.",
    "Tre sidor på ett nytt ställe": "Three pages somewhere new",
    "Ta med en bok till ett kafé du aldrig besökt och läs tills regnet byter takt.": "Bring a book to a café you have never visited and read until the rain changes pace.",
    "Jakten på stadens bästa skydd": "Find the city's best shelter",
    "Hitta en plats med tak där du kan höra regnet utan att bli blöt.": "Find a covered spot where you can hear the rain without getting wet.",
    "Fem droppar från torrskodd": "Five drops from staying dry",
    "Ta dig till ett varmt ställe med så få paraplyöppningar som möjligt.": "Reach somewhere warm with as few umbrella openings as possible.",
    "Första fotspåret": "First footprints",
    "Hitta den tystaste snön i närmaste park och lämna dagens första spår.": "Find the quietest snow in a nearby park and leave the first tracks of the day.",
    "Varm dryck-radar": "Hot drink radar",
    "Promenera till närmaste ställe som serverar något rykande varmt.": "Walk to the nearest place serving something steaming hot.",
    "Följ ljusstrimman": "Follow the light",
    "Hitta en solfläck du aldrig lagt märke till och stanna där i fem minuter.": "Find a patch of sunlight you have never noticed and stay for five minutes.",
    "Hem via omvägen": "Take the long way home",
    "Ta tre nya gator på vägen hem och välj den finaste fasaden.": "Take three new streets on your way home and pick the loveliest façade.",
    "Stormspanaren": "Storm watcher",
    "Betrakta vädret från en trygg plats och fånga dess mest dramatiska ljud.": "Watch the weather from a safe place and listen for its most dramatic sound.",
    "Färgspaning": "Colour spotting",
    "Hitta tre små färgklickar i en grå dag: en dörr, en mössa eller en skylt.": "Find three small splashes of colour on a grey day: a door, a hat or a sign.",
    "Kvartersdetektiven": "Neighbourhood detective",
    "Upptäck en butik eller ett kafé på din gata som du aldrig lagt märke till.": "Notice a shop or café on your street you have never seen before.",
    "Skymningssamlaren": "Twilight collector",
    "Hitta den finaste upplysta platsen i kvarteret innan du går hem.": "Find the loveliest lit-up place in the neighbourhood before heading home.",
    "Slantsinglarens rutt": "The coin-flip route",
    "Kasta ett mynt vid varje vägskäl: krona vänster, klave höger. Stanna efter fyra kast.": "Flip a coin at every crossing: heads left, tails right. Stop after four flips.",
    "Välj med öronen": "Follow your ears",
    "Gå mot det mest intressanta ljudet du hör och se var det leder.": "Walk towards the most interesting sound you hear and see where it leads.",
    "+1 nyfikenhet": "+1 curiosity", "+1 regnresistent": "+1 rain resilience", "+1 paraplydiplomat": "+1 umbrella diplomacy",
    "+1 vinterpoäng": "+1 winter point", "+1 frostskydd": "+1 frost protection", "+1 solladdning": "+1 solar charge",
    "+1 upptäckare": "+1 explorer", "+1 vädermod": "+1 weather courage", "+1 detaljseende": "+1 eye for detail",
    "+1 lokalpoäng": "+1 local knowledge", "+1 kvällsljus": "+1 evening light", "+1 inomhusäventyrare": "+1 indoor explorer", "+1 vardagsflykt": "+1 everyday escape",
    "Dramatiskt lugn": "Dramatic calm", "Avlägset muller och långsamma syntmattor": "Distant thunder and slow synth layers", "Låt ovädret vara soundtrack, men lyssna inomhus.": "Let the storm be the soundtrack, but listen from indoors.",
    "Mjukt och frostigt": "Soft and frosty", "Dämpat piano, snöknarr och varm bas": "Muted piano, snow crunch and warm bass", "Ett långsamt tempo passar en kall dag.": "A slower pace suits a cold day.",
    "Fönsterplats": "Window seat", "Regn mot ruta, mjuk vinyl och kontrabas": "Rain on glass, soft vinyl and double bass", "Låt regnet stå för hi-haten.": "Let the rain handle the hi-hat.",
    "Ljus i steget": "A spring in your step", "Lätt gitarr, fåglar och varm analog synth": "Light guitar, birds and warm analogue synth", "Spara lite av solen till promenaden.": "Save some of the sun for your walk.",
    "Blå timmen": "Blue hour", "Glittrig synth och stadsljud på avstånd": "Shimmering synth and distant city sounds", "Kvällen får gärna gå i slow motion.": "Let the evening move in slow motion.",
    "Lugn upptäckare": "Calm explorer", "Dämpad puls, stadssus och enstaka pianotoner": "A gentle pulse, city hush and occasional piano", "En stadig rytm gör även en grå dag lättare.": "A steady rhythm makes even a grey day easier.",
    "Ingen lugn och torr dagsljuslucka i den hämtade prognosen. Välj ett inomhusalternativ.": "No calm, dry daylight window in the available forecast. Choose an indoor option.",
}


def _translate_string(value: str) -> str:
    exact = _TRANSLATIONS.get(value)
    if exact is not None:
        return exact
    if value.startswith("Det känns som "):
        return value.replace("Det känns som ", "Feels like ", 1)
    if value.startswith("Vinden ligger på "):
        return value.replace("Vinden ligger på ", "Wind is ", 1)
    if value.endswith(" mm nederbörd nyligen."):
        return value.replace(" mm nederbörd nyligen.", " mm of recent precipitation.")
    if value.startswith("En kortare lucka med dagsljus"):
        return value.replace("En kortare lucka med dagsljus", "A short daylight window", 1).replace("Soluppgång", "Sunrise").replace("solnedgång", "sunset")
    if value.startswith("Längsta sammanhängande dagsljusfönstret"):
        return value.replace("Längsta sammanhängande dagsljusfönstret", "Longest continuous daylight window", 1).replace("högst", "up to").replace("nederbördsrisk", "rain chance").replace("och vind under", "and wind below").replace("Soluppgång", "Sunrise").replace("solnedgång", "sunset")
    return value


def translate_payload(value: Any) -> Any:
    if isinstance(value, str):
        return _translate_string(value)
    if isinstance(value, list):
        return [translate_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: translate_payload(item) for key, item in value.items()}
    return value
