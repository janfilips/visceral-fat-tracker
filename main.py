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
    }

def baseline_projection(start_date: date, days: int = 28):
    # Idealized 4-week curve from 0 to 100% if you follow the plan
    step = 100.0 / (days - 1) if days > 1 else 100.0
    return {
        str(start_date + timedelta(days=i)): round(step * i, 1)
        for i in range(days)
    }

def prediction_curve(data, target_beers=4, target_walk=10, target_sleep=7):
    # Simple heuristic projection:
    # good days push the score up, bad days slow or drop it.
    # Result is a 0-100 "progress" index, not medical truth.
    dates = sorted(data.keys())
    progress = {}
    score = 0.0

    for d in dates:
        entry = data[d]
        daily = 0.0

        # Walking contribution
        walk = entry.get("walk_km", 0)
        if walk >= target_walk:
            daily += 0.6
        elif walk >= target_walk * 0.5:
            daily += 0.3
        else:
            daily -= 0.2

        # Beer contribution (less is better)
        beers = entry.get("beers", 0)
        if beers <= target_beers:
            daily += 0.6
        else:
            daily -= 0.3 * (beers - target_beers)

        # Sleep contribution
        sleep = entry.get("sleep_h", 0)
        if sleep >= target_sleep:
            daily += 0.3
        elif sleep < 6:
            daily -= 0.2

        # Update cumulative score and clamp between 0 and 100
        score = max(0.0, min(100.0, score + daily))
        progress[d] = round(score, 1)

    return progress

def visceral_curve(pred):
    # Heuristic: visceral fat mobilization "kicks in" after consistent adherence.
    # Below 25% progress: essentially 0 (mainly water/glycogen / habits).
    # 25-100% progress: scaled up to 100 to show intensity of deep fat work.
    visceral = {}
    for d in sorted(pred.keys()):
        p = pred[d]
        if p <= 25:
            val = 0.0
        else:
            val = (p - 25) / 75 * 100  # linear ramp from 0 to 100
        visceral[d] = round(max(0.0, min(100.0, val)), 1)
    return visceral

@app.get("/", response_class=HTMLResponse)
def dashboard():
    data = load_data()
    summary = weekly_summary(data)
    today = datetime.now().date()

    if data:
        first_logged_date = min(datetime.strptime(d, "%Y-%m-%d").date() for d in data.keys())
        baseline = baseline_projection(first_logged_date)
    else:
        # If no data yet, start baseline today so graph is pre-filled
        baseline = baseline_projection(today)

    target_beers = 4
    target_walk = 10
    target_sleep = 7

    pred_curve = prediction_curve(data, target_beers=target_beers, target_walk=target_walk, target_sleep=target_sleep)
    visceral = visceral_curve(pred_curve)

    def compute_deviation(pred, base):
        common = [d for d in pred.keys() if d in base]
        if not common:
            return None
        diffs = [pred[d] - base[d] for d in common]
        return round(sum(diffs) / len(diffs), 1)

    deviation = compute_deviation(pred_curve, baseline)

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
              width: 28%;
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
          <h3>Avg Sleep (h)</h3>
          <p>{summary.get("avg_sleep", "–")}</p>
          <div class="indicator" style="background-color:{indicator(summary.get('avg_sleep'), target_sleep)}"></div>
        </div>
      </div>
      <div style="text-align:center; margin-bottom: 1rem;">
    """
    if deviation is None:
        html += "        <span>Plan loaded. Start logging to see how close you are to the curve.</span>"
    else:
        status_text = "On track" if deviation >= -5 else "Slightly behind" if deviation >= -15 else "Off track"
        status_color = "#16a34a" if deviation >= -5 else "#f97316" if deviation >= -15 else "#dc2626"
        html += f"        <span style='font-weight:500;color:{status_color};'>Status: {status_text} ({deviation}% vs plan)</span>"
    html += """
      </div>

      <canvas id="chart" height="100"></canvas>

      <form method="post" action="/log">
        <h2>Log Today</h2>
        <label>Beers:</label><input type="number" name="beers" min="0" max="10" required><br>
        <label>Walk (km):</label><input type="number" name="walk_km" step="0.1" required><br>
        <label>Meals:</label><input type="number" name="meals" min="0" max="3" required><br>
        <label>Sleep (h):</label><input type="number" name="sleep_h" step="0.1" required><br>
        <button type="submit">Save today</button>
      </form>

      <table>
        <tr><th>Date</th><th>Beers</th><th>Walk</th><th>Meals</th><th>Sleep</th></tr>
    """

    for d, e in sorted(data.items(), reverse=True):
        html += f"<tr><td>{d}</td><td>{e['beers']}</td><td>{e['walk_km']}</td><td>{e['meals']}</td><td>{e['sleep_h']}</td></tr>"
    html += "</table>"

    # Chart.js visual - last 14 days, including baseline (plan) and actual
    # Collect all dates from baseline and predictions so we can show deviation vs plan
    all_dates = sorted(set(list(baseline.keys()) + list(pred_curve.keys())))
    last_labels = all_dates[-14:] if all_dates else []

    labels = last_labels
    beers = [data.get(d, {}).get("beers") if d in data else None for d in labels]
    walks = [data.get(d, {}).get("walk_km") if d in data else None for d in labels]
    planned = [baseline.get(d) for d in labels]
    actual = [pred_curve.get(d) if d in pred_curve else None for d in labels]
    visceral_vals = [visceral.get(d) if d in visceral else None for d in labels]

    import json as _json

    labels_js = _json.dumps(labels)
    beers_js = _json.dumps(beers)
    walks_js = _json.dumps(walks)
    planned_js = _json.dumps(planned)
    actual_js = _json.dumps(actual)
    visceral_js = _json.dumps(visceral_vals)

    html += f"""
      <script>
        const ctx = document.getElementById('chart').getContext('2d');
        new Chart(ctx, {{
          type: 'line',
          data: {{
            labels: {labels_js},
            datasets: [
              {{
                label: 'Beers',
                data: {beers_js},
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239,68,68,0.25)',
                spanGaps: true,
                fill: true,
                tension: 0.25,
                yAxisID: 'y'
              }},
              {{
                label: 'Walk km',
                data: {walks_js},
                borderColor: '#10b981',
                backgroundColor: 'rgba(16,185,129,0.25)',
                spanGaps: true,
                fill: true,
                tension: 0.25,
                yAxisID: 'y'
              }},
              {{
                label: 'Planned progress %',
                data: {planned_js},
                borderColor: '#9ca3af',
                backgroundColor: 'rgba(148,163,253,0.08)',
                borderDash: [4,3],
                fill: false,
                tension: 0.15,
                yAxisID: 'y1'
              }},
              {{
                label: 'Actual progress %',
                data: {actual_js},
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99,102,241,0.15)',
                fill: false,
                spanGaps: true,
                tension: 0.25,
                yAxisID: 'y1'
              }},
              {{
                label: 'Visceral burn phase %',
                data: {visceral_js},
                borderColor: '#22c55e',
                backgroundColor: 'rgba(34,197,94,0.12)',
                fill: false,
                spanGaps: true,
                tension: 0.25,
                yAxisID: 'y1'
              }}
            ]
          }},
          options: {{
            responsive: true,
            interaction: {{
              mode: 'index',
              intersect: false
            }},
            scales: {{
              y: {{
                beginAtZero: true,
                title: {{
                  display: true,
                  text: 'Beers / Walk km'
                }}
              }},
              y1: {{
                beginAtZero: true,
                max: 100,
                position: 'right',
                grid: {{
                  drawOnChartArea: false
                }},
                title: {{
                  display: true,
                  text: 'Progress %'
                }}
              }}
            }},
            plugins: {{
              legend: {{
                labels: {{
                  usePointStyle: true
                }}
              }},
              tooltip: {{
                callbacks: {{
                  label: function(context) {{
                    const label = context.dataset.label || '';
                    if (label.includes('progress')) {{
                      return label + ': ' + context.parsed.y + '%';
                    }}
                    return label + ': ' + (context.parsed.y !== null ? context.parsed.y : '-');
                  }}
                }}
              }}
            }}
          }}
        }});
      </script>
    </body></html>
    """
    return html

@app.post("/log")
def log(beers: int = Form(...), walk_km: float = Form(...), meals: int = Form(...), sleep_h: float = Form(...)):
    data = load_data()
    today = str(date.today())
    data[today] = dict(beers=beers, walk_km=walk_km, meals=meals, sleep_h=sleep_h)
    save_data(data)
    return RedirectResponse("/", status_code=303)
