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
- Self-service "Forgot password?" email reset (if SMTP is configured; see
  below), plus admin CLI commands as a fallback.

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

Create a login (you'll be prompted for an email and a password):

```bash
flask --app run.py create-user yourname
```

The email is optional (press Enter to skip) and enables the "Forgot
password?" link on the login page for this account (requires SMTP to be
configured — see below). You can also attach or change an email on an
existing account later:

```bash
flask --app run.py set-email yourname you@example.com
```

Forgot your password and can't use the email link (or don't have SMTP set
up)? An admin can reset it directly:

```bash
flask --app run.py reset-password yourname
```

### Enabling email-based password reset (optional)

To let users reset their own password from the login page, set these in
`.env` (see `.env.example`) with real SMTP credentials — for Gmail, use an
[app password](https://myaccount.google.com/apppasswords), not your normal
password:

```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=you@example.com
MAIL_PASSWORD=an-app-password-not-your-real-password
MAIL_DEFAULT_SENDER=you@example.com
```

If `MAIL_SERVER` is left unset, the "Forgot password?" link tells users to
contact an admin instead, and the `reset-password` CLI command above still
works regardless.

By default, the link inside the reset email is built from whatever hostname
the request came in on — which is wrong if you're running behind a reverse
proxy, port-forwarding, or testing against `127.0.0.1`. Set `APP_BASE_URL` in
`.env` to pin it to your real, reachable address instead:

```
APP_BASE_URL=https://pool.example.com
```

## Running the website

Every time you want to start the app:

```bash
source .venv/bin/activate   # if not already active
python run.py
```

Then open http://127.0.0.1:8080 in your browser and log in with the account
you created above. Press `Ctrl+C` in the terminal to stop the server.

The SQLite database is created automatically at `instance/pooltracker.db`
(gitignored) the first time the app starts, and persists between runs.

## Running with Podman

Build the image:

```bash
podman build -t pooltracker .
```

Generate a secret key (same as the native setup):

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Run the container, keeping the SQLite database in a named volume so it
persists across restarts. `--env-file .env` passes through `SECRET_KEY` and,
if you set them, the `MAIL_*` settings for password reset emails:

```bash
podman run -d --name pooltracker \
  --env-file .env \
  -p 8080:8080 \
  -v pooltracker-data:/app/instance \
  pooltracker
```

Create your login (first time only):

```bash
podman exec -it pooltracker flask --app run.py create-user yourname
```

Then open http://127.0.0.1:8080 and log in. Useful commands afterward:

```bash
podman stop pooltracker     # stop the container
podman start pooltracker    # start it again (data is preserved)
podman logs -f pooltracker  # tail the app logs
```
