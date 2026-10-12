# Vädervett

En väderstyrd svensk vardagsplanerare. Next.js står för gränssnittet; FastAPI i Python hämtar väder, räknar ut dagens råd och uppdrag, och sparar väderkapslar i SQLite.

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

Väder hämtas från [Open-Meteo](https://open-meteo.com/) och uppdateras var 15:e minut. Kapslar lagras lokalt i `backend/weather_capsules.sqlite3`.
