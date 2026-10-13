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
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Terminal 2, webbsidan:

```powershell
npm.cmd run dev
```

Öppna [http://localhost:3000](http://localhost:3000). API-dokumentation finns på [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Testa Pythonbackendens väderregler och kapsel-API:

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test_main -v
```

## Datakällor och integritet

- Aktuellt väder och timprognos hämtas från [Open-Meteo](https://open-meteo.com/). Vädret uppdateras var 15:e minut; det är prognosmodellens senaste uppgifter, inte sekundfärska observationer.
- Ortsökning använder Open-Meteos Geocoding API. Närplatser hämtas från [OpenStreetMap](https://www.openstreetmap.org/copyright) via Overpass. Den öppna karttjänsten kan vara belastad; då visas ett återförsök i stället för påhittade platser.
- Platsbilder används från en `wikimedia_commons`-tagg i OpenStreetMap eller från Wikimedia Commons när filnamnet matchar platsens namn. Bildsökningen cachas i backend ett dygn; foto och källsida visas bara när en träff finns. Annars visas kategorimarkören `(C)` eller `(M)`.
- Öppettider visas endast när de finns i OpenStreetMap. De verifieras inte som “öppet nu”. Kartbidrag kan vara ofullständiga eller gamla.
- Ingen inloggning krävs. Webbläsaren skapar ett slumpmässigt ID i `localStorage`; backend använder det för att hålla preferenser och väderminnen åtskilda mellan webbläsare. Det är inte autentisering eller molnsynkronisering.
- SQLite-filen `backend/weather_capsules.sqlite3` innehåller lokala preferenser och sparade väderminnen. Ta en säkerhetskopia innan du flyttar installationen.
- Platsåtkomst begärs först när besökaren väljer “Använd min plats”. Svensk ortssökning fungerar som alternativ.

Väderkomfortpoängen är Vädervetts egen deterministiska uppskattning av utomhuskomfort, inte ett officiellt meteorologiskt mått.
