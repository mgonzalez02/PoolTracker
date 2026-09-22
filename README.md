# PoolTracker

A small Flask app for tracking swimming pool chemical levels: log test-strip
readings, log chemicals added to the pool, and view 7-day trend charts for
each tracked chemical.

## Features

- Login-protected app (local username/password accounts, hashed with Werkzeug).
- Dashboard with trend charts for Free Chlorine, Total Chlorine, pH, Total
  Alkalinity, CYA, TDS, Calcium Hardness, and NaCl (salt), covering the last
  7 days, with chemical-addition events marked on each chart.
- "Enter Chemical Levels" form that timestamps and saves a full set of
  readings.
- "Log Chemicals Added" form for Chlorine (oz), Muriatic Acid, CYA, Bromine,
  Soda Ash, and a free-form "Other" chemical/amount.

## Setup (one-time)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated key into `.env` as the value of `SECRET_KEY` (it must not
be left blank — the app will refuse to start otherwise).

Create a login (you'll be prompted for a password):

```bash
flask --app run.py create-user yourname
```

## Running the website

Every time you want to start the app:

```bash
source .venv/bin/activate   # if not already active
python run.py
```

Then open http://127.0.0.1:5000 in your browser and log in with the account
you created above. Press `Ctrl+C` in the terminal to stop the server.

The SQLite database is created automatically at `instance/pooltracker.db`
(gitignored) the first time the app starts, and persists between runs.
