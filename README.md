# Retail Banking Scraper Portal

This project is an internal web portal for Retail Banking staff to collect structured records from Telegram channels/groups and append them to a Google Sheet.

It replaces the manual notebook workflow with:

- A React frontend where staff choose dates and Telegram source links.
- A FastAPI backend that runs the scraping job safely in the background.
- A Google Sheets writer that appends only new rows and skips duplicates.

## What To Show IT Or Retail Staff

Show these parts during the handoff:

- The web page at `http://localhost:5173`.
- The form inputs: start date/time, end date/time, and Telegram source links.
- The live scraping status: queued, running, completed, or failed.
- The counters: records found, rows added, and duplicates skipped.
- The execution log, which helps explain what happened during each run.
- The destination Google Sheet tab where the final rows are written.

The main message for Retail staff:

> Staff only need to select the reporting window, add Telegram links, and click Run scraping. The system handles Telegram reading, parsing, duplicate checking, and Google Sheets upload.

The main message for IT:

> Credentials stay on the backend. The frontend does not contain Telegram or Google secrets.

## User Workflow

1. Open the portal:

```text
http://localhost:5173
```

2. Choose the start date and end date for the report.

3. Add Telegram channel or group links.

Valid examples:

```text
https://t.me/example_channel
https://telegram.me/example_group
```

4. Click `Run scraping`.

5. Wait for the live status to complete.

6. Review the Google Sheet tab configured by IT.

## What Users Need To Input

Retail users input these values in the frontend:

- `Start date & time`: beginning of the reporting period.
- `End date & time`: end of the reporting period.
- `Telegram sources`: one or more Telegram channel/group links.

Rules:

- At least one Telegram link is required.
- Maximum links are controlled by backend config, default `100`.
- Links must start with `https://t.me/` or `https://telegram.me/`.
- Start date must be earlier than end date.
- The app uses Cambodia timezone by default: `Asia/Phnom_Penh`.

## Backend Workflow

When a user clicks `Run scraping`, this happens:

1. Frontend sends a request to the backend:

```text
POST /api/jobs
```

2. Backend validates:

- Telegram links are valid.
- Empty links are ignored.
- Duplicate links are removed.
- Date range is valid.
- Link count does not exceed the configured limit.

3. Backend creates a job and adds it to a queue.

4. The worker runs one job at a time. This avoids multiple jobs fighting over the same Telegram session.

5. Backend connects to Telegram using the configured Telegram account.

6. Messages inside the selected date range are read.

7. The parser extracts Retail Banking fields from each message.

8. Backend opens the configured Google Sheet.

9. Existing rows are checked so duplicate records are skipped.

10. New rows are appended to the worksheet.

11. Frontend polls the backend for job progress:

```text
GET /api/jobs/{job_id}
```

12. The user sees the final result: completed, failed, rows added, duplicates skipped, and logs.

## Backend Configuration For IT

Create or update this file:

```text
backend/.env
```

Use `backend/.env.example` as the template.

Required values:

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=replace-with-api-hash
TELEGRAM_PHONE_NUMBER=+855000000000
TELEGRAM_SESSION_PATH=../tg_sessions/geo_scraper
TELEGRAM_SESSION_STRING=replace-with-telethon-string-session

GOOGLE_CREDENTIALS_PATH=../khemra_account.json
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"replace-me"}
GOOGLE_SHEET_ID=replace-with-spreadsheet-id
GOOGLE_WORKSHEET_NAME=Retail_Banking

SCRAPER_TIMEZONE=Asia/Phnom_Penh
SCRAPER_HISTORY_LIMIT=100
SCRAPER_MAX_LINKS=100

BACKEND_CORS_ORIGINS=http://localhost:5173,https://your-project.vercel.app
SERVERLESS_SYNC_JOBS=false
```

Configuration meaning:

- `TELEGRAM_API_ID`: Telegram API ID for the backend account.
- `TELEGRAM_API_HASH`: Telegram API hash for the backend account.
- `TELEGRAM_PHONE_NUMBER`: phone number used for the Telegram session.
- `TELEGRAM_SESSION_PATH`: where the Telegram login session is stored.
- `TELEGRAM_SESSION_STRING`: Telethon string session for Vercel/serverless hosting.
- `GOOGLE_CREDENTIALS_PATH`: Google service-account JSON file path.
- `GOOGLE_CREDENTIALS_JSON`: Google service-account JSON contents for Vercel/serverless hosting.
- `GOOGLE_SHEET_ID`: ID from the Google Sheet URL.
- `GOOGLE_WORKSHEET_NAME`: worksheet/tab name to write into.
- `SCRAPER_TIMEZONE`: timezone used for date filtering.
- `SCRAPER_HISTORY_LIMIT`: Telegram message batch limit.
- `SCRAPER_MAX_LINKS`: maximum Telegram links per job.
- `BACKEND_CORS_ORIGINS`: frontend URLs that are allowed to call the backend.
- `SERVERLESS_SYNC_JOBS`: set to `true` on Vercel so jobs run inside the API request.

Important:

- The Google service account must have edit access to the destination Google Sheet.
- The Telegram account must have access to the channels/groups being scraped.
- Never put Telegram or Google credentials into frontend source code.

## Deploy Frontend And Backend To Vercel

The repository includes:

- `vercel.json` for the Vite frontend and Python API routing.
- `api/index.py` as the Vercel serverless FastAPI entrypoint.
- `requirements.txt` so Vercel installs backend Python dependencies.

In Vercel:

1. Import `https://github.com/cheezykim/Scrap_Interface_Retail-.git`.
2. Keep the project root as the repository root.
3. Add the environment variables listed below in Vercel Project Settings.
4. Leave `VITE_API_URL` empty so the frontend calls the same Vercel project at `/api`.
5. Deploy.

```env
VITE_API_URL=
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=replace-with-api-hash
TELEGRAM_PHONE_NUMBER=+855000000000
TELEGRAM_SESSION_STRING=replace-with-telethon-string-session
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"replace-me"}
GOOGLE_SHEET_ID=replace-with-spreadsheet-id
GOOGLE_WORKSHEET_NAME=Retail_Banking
SCRAPER_TIMEZONE=Asia/Phnom_Penh
SCRAPER_HISTORY_LIMIT=100
SCRAPER_MAX_LINKS=100
SERVERLESS_SYNC_JOBS=true
```

To create `TELEGRAM_SESSION_STRING`, first authorize the Telegram account locally with the file session, then run:

```powershell
cd C:\Users\sombath.kim\Documents\Retail_Banking_interface\backend
python scripts\export_telegram_session.py
```

Copy the printed value into Vercel as `TELEGRAM_SESSION_STRING`.

Vercel serverless note:

- Jobs run inside the API request when `SERVERLESS_SYNC_JOBS=true`.
- Long Telegram scrapes can hit Vercel function duration limits.
- For heavy production use, the same backend code will still run better on a persistent Python server, but the project is now configured to deploy both frontend and backend on Vercel.

## Run Locally

Use two PowerShell windows.

Backend:

```powershell
cd C:\Users\sombath.kim\Documents\Retail_Banking\backend
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --env-file .env
```

Frontend:

```powershell
cd C:\Users\sombath.kim\Documents\Retail_Banking\frontend
npm.cmd run dev -- --host localhost --port 5173
```

Open:

```text
http://localhost:5173
```

Backend health check:

```text
http://127.0.0.1:8000/api/health
```

Expected response:

```json
{"status":"ok","worker":"ready"}
```

## Test Commands

Backend unit tests:

```powershell
cd C:\Users\sombath.kim\Documents\Retail_Banking\backend
python -m unittest discover
```

Frontend build:

```powershell
cd C:\Users\sombath.kim\Documents\Retail_Banking\frontend
npm.cmd run build
```

## Output Fields

The parser writes records using the Retail Banking sheet schema. Key business fields include:

- `Type`
- `Call_Plan`
- `Direction`
- `Client_Name`
- `Contact`
- `Category`

The backend also keeps source and message metadata so it can identify duplicate Telegram records before appending new rows.

## Troubleshooting

Port already in use:

```text
[Errno 10048] address already in use
```

This means the backend or frontend is already running. Use the existing page, or stop the old process before restarting.

Bad Google proxy error:

```text
HTTPSConnectionPool(host='oauth2.googleapis.com'...)
ProxyError ... 127.0.0.1:9
```

This means the machine has a broken proxy setting. The backend removes that known dead proxy on startup, but IT should still check system/user environment variables if the error returns.

Telegram login/session issue:

- Confirm the phone number is correct.
- Confirm the Telegram session file exists or authorize the account again.
- Confirm the account can access the requested channels/groups.

Google Sheet permission issue:

- Confirm `GOOGLE_CREDENTIALS_PATH` points to the correct JSON file.
- Confirm the Google Sheet is shared with the service-account email.
- Confirm `GOOGLE_SHEET_ID` and `GOOGLE_WORKSHEET_NAME` are correct.

Worksheet header issue:

- The backend expects the worksheet header to match the required schema.
- If the tab was manually edited, restore the correct header row or use a fresh worksheet.

## Security Handoff Checklist

Before handing this project to another team:

- Do not share real `.env` values publicly.
- Do not commit Google service-account JSON files.
- Do not commit `tg_sessions/`.
- Do not expose Telegram API ID/hash or phone number in screenshots.
- Give IT ownership of credential rotation and Google Sheet access.
- If credentials were shared accidentally, rotate the Google service-account key and revoke old Telegram sessions.
