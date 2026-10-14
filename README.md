# Vädervett

En väderstyrd svensk vardagsplanerare: “Don't just check the weather. Outsmart it.” Next.js visar upplevelsen; FastAPI i Python hämtar prognoser, räknar ut väderkomfort och råd, söker verkliga närplatser och sparar webbläsarspecifika preferenser och väderminnen i SQLite.

## Starta lokalt

Installera backendberoenden en gång:

```powershell
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
```

Starta sedan två terminaler i projektmappen.

Terminal 1, Python-API:

```powershell
$env:GEOAPIFY_API_KEY = "din-geoapify-nyckel"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Skapa en kostnadsfri API-nyckel hos [Geoapify](https://myprojects.geoapify.com/) och ersätt exempelvärdet ovan. Nyckeln läses bara av Python-backenden; lägg den inte i frontendens `NEXT_PUBLIC_*`-variabler eller i Git. Geoapifys Places API söker i en exakt radie runt koordinaterna och den kostnadsfria nivån har 3 000 credits per dag. Utan nyckeln används Overpass som reservkälla.

Terminal 2, webbsidan:

```powershell
npm.cmd run dev
```

Öppna [http://localhost:3000](http://localhost:3000). API-dokumentation finns på [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Öppna utvecklingssidan på en telefon

`localhost` och `127.0.0.1` pekar alltid på enheten som öppnar adressen. För telefonen används därför datorns privata nätverksadress. Datorns aktuella adress är `192.168.10.170`; ersätt den om nätverket ger datorn en annan adress och anslut båda enheterna till samma Wi-Fi.

Starta Python-API:t med LAN-origin tillåten:

```powershell
$env:WEATHER_ALLOWED_ORIGINS = "http://192.168.10.170:3000"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Starta webbsidan i en andra terminal:

```powershell
npm.cmd run dev -- --hostname 0.0.0.0
```

Öppna sedan `http://192.168.10.170:3000` på telefonen. Om Windows-brandväggen frågar, tillåt Node och Python på det privata nätverket.

Testa Pythonbackendens väderregler och kapsel-API:

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test_main -v
```

## Datakällor och integritet

- Aktuellt väder och timprognos hämtas från [Open-Meteo](https://open-meteo.com/). Vädret uppdateras var 15:e minut; det är prognosmodellens senaste uppgifter, inte sekundfärska observationer.
- Backend cachar väder i fem minuter och ortsökningar i fem minuter. Vid upstream-avbrott kan senast hämtade väder och platser återanvändas i upp till en timme; vädervyn visar då datans faktiska hämtningstid. Cacheminnet gäller per backendprocess.
- Ortsökning använder Open-Meteos Geocoding API. Närplatser hämtas i första hand från Geoapify Places API, som använder OpenStreetMap-data och filtrerar på vald GPS-position och radie. Overpass används som reserv om Geoapify-nyckel saknas eller tjänsten tillfälligt fallerar. Geoapify-attribuering visas när den källan används. Kartresultat cachelagras; vid fel utan cache visas ett återförsök i stället för påhittade platser. API-svaren innehåller `Server-Timing` för att kunna inspektera backendens svarstid.
- Platsbilder används från en `wikimedia_commons`-tagg i OpenStreetMap. Foto och källsida visas bara när kartdatan innehåller en bildlänk; annars visas kategorimarkören `(C)` eller `(M)`.
- Öppettider visas endast när de finns i OpenStreetMap. De verifieras inte som “öppet nu”. Kartbidrag kan vara ofullständiga eller gamla.
- Ingen inloggning krävs. Webbläsaren skapar ett slumpmässigt ID i `localStorage`; backend använder det för att hålla preferenser och väderminnen åtskilda mellan webbläsare. Det är inte autentisering eller molnsynkronisering.
- SQLite-filen `backend/weather_capsules.sqlite3` innehåller lokala preferenser och sparade väderminnen. Ta en säkerhetskopia innan du flyttar installationen.
- Platsåtkomst begärs först när besökaren väljer “Använd min plats”. Svensk ortssökning fungerar som alternativ.

Väderkomfortpoängen är Vädervetts egen deterministiska uppskattning av utomhuskomfort, inte ett officiellt meteorologiskt mått.
