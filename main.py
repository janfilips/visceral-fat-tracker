from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from datetime import date, datetime, timedelta
import json

app = FastAPI(title="Visceral Fat Tracker")

DATA_FILE = Path("progress.json")

def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {}

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2))

def weekly_summary(data):
    # Compute 7-day rolling averages
    today = datetime.now().date()
    past_week = [today - timedelta(days=i) for i in range(7)]
    subset = [data.get(str(d)) for d in reversed(past_week) if str(d) in data]
    if not subset:
        return {}
    avg = lambda k: round(sum(e[k] for e in subset) / len(subset), 1)
    return {
        "avg_beers": avg("beers"),
        "avg_walk": avg("walk_km"),
        "avg_sleep": avg("sleep_h"),
        "avg_water": avg("water_l"),
    }

@app.get("/", response_class=HTMLResponse)
def dashboard():
    data = load_data()
    summary = weekly_summary(data)
    target_beers = 4
    target_walk = 10
    target_sleep = 7
    target_water = 2.5

    def indicator(current, target, inverse=False):
        if not current:
            return "gray"
        if inverse:
            return "red" if current > target else "green"
        return "green" if current >= target else "orange"

    html = f"""
    <html>
    <head>
        <title>Visceral Fat Tracker</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{
              font-family: 'Poppins', sans-serif;
              background-color: #f3e8ff;
              color: #222;
              margin: 0;
              padding: 2rem;
            }}
            h1 {{
              text-align: center;
              color: #6b21a8;
            }}
            .summary {{
              display: flex;
              justify-content: space-around;
              margin: 1.5rem 0;
            }}
            .card {{
              background: white;
              border-radius: 16px;
              padding: 1rem;
              width: 22%;
              box-shadow: 0 2px 5px rgba(0,0,0,0.1);
              text-align: center;
            }}
            .indicator {{
              height: 12px;
              border-radius: 6px;
              margin-top: 8px;
            }}
            form {{
              background: #fff;
              padding: 1rem;
              border-radius: 16px;
              box-shadow: 0 2px 5px rgba(0,0,0,0.1);
              max-width: 500px;
              margin: 2rem auto;
            }}
            input[type=number] {{
              width: 80px;
              margin-left: 1rem;
            }}
            button {{
              margin-top: 1rem;
              padding: 8px 16px;
              background-color: #8b5cf6;
              color: white;
              border: none;
              border-radius: 8px;
              cursor: pointer;
            }}
            table {{
              width: 100%;
              border-collapse: collapse;
              margin-top: 1.5rem;
            }}
            th, td {{
              border: 1px solid #ccc;
              padding: 6px;
              text-align: center;
            }}
            th {{
              background-color: #e9d5ff;
            }}
        </style>
    </head>
    <body>
      <h1>4-Week Visceral Fat & Beer-Taper Tracker</h1>

      <div class="summary">
        <div class="card">
          <h3>Avg Beers</h3>
          <p>{summary.get("avg_beers", "–")}</p>
          <div class="indicator" style="background-color:{indicator(summary.get('avg_beers'), target_beers, inverse=True)}"></div>
        </div>
        <div class="card">
          <h3>Avg Walk (km)</h3>
          <p>{summary.get("avg_walk", "–")}</p>
          <div class="indicator" style="background-color:{indicator(summary.get('avg_walk'), target_walk)}"></div>
        </div>
        <div class="card">
          <h3>Avg Water (L)</h3>
          <p>{summary.get("avg_water", "–")}</p>
          <div class="indicator" style="background-color:{indicator(summary.get('avg_water'), target_water)}"></div>
        </div>
        <div class="card">
          <h3>Avg Sleep (h)</h3>
          <p>{summary.get("avg_sleep", "–")}</p>
          <div class="indicator" style="background-color:{indicator(summary.get('avg_sleep'), target_sleep)}"></div>
        </div>
      </div>

      <canvas id="chart" height="100"></canvas>

      <form method="post" action="/log">
        <h2>Log Today</h2>
        <label>Beers:</label><input type="number" name="beers" min="0" max="10" required><br>
        <label>Walk (km):</label><input type="number" name="walk_km" step="0.1" required><br>
        <label>Meals:</label><input type="number" name="meals" min="0" max="3" required><br>
        <label>Water (L):</label><input type="number" name="water_l" step="0.1" required><br>
        <label>Sleep (h):</label><input type="number" name="sleep_h" step="0.1" required><br>
        <button type="submit">Save today</button>
      </form>

      <table>
        <tr><th>Date</th><th>Beers</th><th>Walk</th><th>Meals</th><th>Water</th><th>Sleep</th></tr>
    """

    for d, e in sorted(data.items(), reverse=True):
        html += f"<tr><td>{d}</td><td>{e['beers']}</td><td>{e['walk_km']}</td><td>{e['meals']}</td><td>{e['water_l']}</td><td>{e['sleep_h']}</td></tr>"
    html += "</table>"

    # Chart.js
    labels = [d for d in sorted(data.keys())[-14:]]
    beers = [data[d]["beers"] for d in labels]
    walks = [data[d]["walk_km"] for d in labels]
    html += f"""
      <script>
        const ctx = document.getElementById('chart').getContext('2d');
        new Chart(ctx, {{
          type: 'line',
          data: {{
            labels: {labels},
            datasets: [
              {{ label: 'Beers', data: {beers}, borderColor: '#ef4444', fill: false }},
              {{ label: 'Walk km', data: {walks}, borderColor: '#10b981', fill: false }}
            ]
          }},
          options: {{
            responsive: true,
            scales: {{ y: {{ beginAtZero: true }} }}
          }}
        }});
      </script>
    </body></html>
    """
    return html

@app.post("/log")
def log(beers: int = Form(...), walk_km: float = Form(...), meals: int = Form(...), water_l: float = Form(...), sleep_h: float = Form(...)):
    data = load_data()
    today = str(date.today())
    data[today] = dict(beers=beers, walk_km=walk_km, meals=meals, water_l=water_l, sleep_h=sleep_h)
    save_data(data)
    return RedirectResponse("/", status_code=303)
