from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
import json
from datetime import date

app = FastAPI(title="Visceral Fat Tracker")

DATA_FILE = Path("progress.json")

def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {}

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2))

@app.get("/", response_class=HTMLResponse)
def dashboard():
    data = load_data()
    html = """
    <html>
      <head>
        <title>Visceral Fat Tracker</title>
        <style>
          body { font-family: sans-serif; max-width: 600px; margin: 2rem auto; }
          h1 { text-align: center; }
          table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
          th, td { border: 1px solid #ccc; padding: 6px; text-align: center; }
          th { background-color: #f5f5f5; }
          input[type=number] { width: 70px; }
          form { margin-top: 2rem; }
          button { padding: 8px 16px; margin-top: 1rem; }
        </style>
      </head>
      <body>
        <h1>Visceral Fat Tracker</h1>
        <form method="post" action="/log">
          <label>Beers:</label> <input type="number" name="beers" min="0" max="10" required><br><br>
          <label>Walk (km):</label> <input type="number" name="walk_km" step="0.1" required><br><br>
          <label>Healthy Meals:</label> <input type="number" name="meals" min="0" max="3" required><br><br>
          <label>Water (L):</label> <input type="number" name="water_l" step="0.1" required><br><br>
          <label>Sleep (hrs):</label> <input type="number" name="sleep_h" step="0.1" required><br><br>
          <button type="submit">Save today</button>
        </form>
        <h2>Progress</h2>
        <table>
          <tr><th>Date</th><th>Beers</th><th>Walk</th><th>Meals</th><th>Water</th><th>Sleep</th></tr>
    """
    for d, entry in sorted(data.items(), reverse=True):
        html += f"<tr><td>{d}</td><td>{entry['beers']}</td><td>{entry['walk_km']}</td><td>{entry['meals']}</td><td>{entry['water_l']}</td><td>{entry['sleep_h']}</td></tr>"
    html += "</table></body></html>"
    return html

@app.post("/log")
def log(
    beers: int = Form(...),
    walk_km: float = Form(...),
    meals: int = Form(...),
    water_l: float = Form(...),
    sleep_h: float = Form(...)
):
    data = load_data()
    today = str(date.today())
    data[today] = dict(beers=beers, walk_km=walk_km, meals=meals, water_l=water_l, sleep_h=sleep_h)
    save_data(data)
    return RedirectResponse("/", status_code=303)

