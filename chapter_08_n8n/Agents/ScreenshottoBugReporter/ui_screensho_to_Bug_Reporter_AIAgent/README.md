# QAAfterHours · Screenshot → Bug Reporter UI

Light-mode web UI for the n8n workflow `../08_Screenshot_to_bug_reporter_AIAgent_UI.json`.
Static page (`public/`) + one Vercel function (`api/report.js`) that forwards the upload to n8n.

```
Browser ──multipart──▶ /api/report (Vercel) ──▶ n8n Webhook /webhook/bug-reporter ──▶ AI ──▶ Jira KAN
        ◀──── JSON { ok, key, url, title, severity, confidence, labels } ◀────────────────────────┘
```

## Setup
1. Import `08_Screenshot_to_bug_reporter_AIAgent_UI.json` into n8n Cloud, check the Groq/OpenRouter/Jira credentials, **activate** it.
2. Copy the **Production URL** from the *Bug Report Webhook* node (`https://<you>.app.n8n.cloud/webhook/bug-reporter`).
3. In Vercel → Project → Settings → Environment Variables, set `N8N_WEBHOOK_URL` to that URL, then redeploy.
4. Optional: set `N8N_SHARED_SECRET`; the proxy sends it as header `x-bug-reporter-key`. Turn on *Header Auth* in the Webhook node with the same value to block direct calls.

## Deploy
```
vercel deploy --prod
```

## Fields sent to n8n
`screenshot` (file, PNG/JPG/WEBP) · `notes` · `logs` · `environment`. Screenshots over 3.8 MB are re-encoded in the browser (Vercel request limit is 4.5 MB).
