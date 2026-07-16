"""Password-gated UI to trigger outbound Twilio calls into the voice agent.

  - GET  /      -> the form (behind HTTP Basic Auth)
  - POST /call  -> places the call via Twilio's REST API (same auth)

HTTP Basic Auth (not a form password field) so the browser's native login
prompt handles credential caching for the session — you authenticate once,
not on every call. Username is fixed since there's only one operator; only
the password (APP_PASSWORD) is checked.
"""
import os
import secrets

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

load_dotenv(override=True)

app = FastAPI()
security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_password = os.getenv("APP_PASSWORD", "")
    if not secrets.compare_digest(credentials.password, correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Basic"},
        )


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Outbound Call Console</title>
<style>
  :root {{
    --navy: #0f2545;
    --navy-dark: #0a1b33;
    --accent: #2f6fed;
    --accent-dark: #1f56c9;
    --border: #d9dee6;
    --text: #1c2733;
    --muted: #64748b;
    --bg: #f4f6f9;
    --ok-bg: #eaf7ee;
    --ok-text: #1e7a3d;
    --err-bg: #fdecec;
    --err-text: #b3261e;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: var(--text);
    padding: 24px;
  }}
  .card {{
    width: 100%;
    max-width: 420px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(15, 37, 69, 0.08), 0 12px 32px rgba(15, 37, 69, 0.10);
    overflow: hidden;
  }}
  .card-header {{
    background: linear-gradient(135deg, var(--navy), var(--navy-dark));
    color: #fff;
    padding: 28px 32px;
  }}
  .card-header h1 {{
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    letter-spacing: 0.2px;
  }}
  .card-header p {{
    margin: 6px 0 0;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.72);
  }}
  .card-body {{
    padding: 28px 32px 32px;
  }}
  label {{
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: var(--muted);
    margin-bottom: 6px;
  }}
  input[type="text"], input[type="tel"] {{
    width: 100%;
    padding: 11px 14px;
    font-size: 15px;
    border: 1px solid var(--border);
    border-radius: 8px;
    outline: none;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
    color: var(--text);
    background: #fff;
  }}
  input:focus {{
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(47, 111, 237, 0.15);
  }}
  .hint {{
    font-size: 12px;
    color: var(--muted);
    margin-top: 6px;
  }}
  button {{
    width: 100%;
    margin-top: 22px;
    padding: 12px 16px;
    font-size: 15px;
    font-weight: 600;
    color: #fff;
    background: var(--accent);
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.15s ease;
  }}
  button:hover {{ background: var(--accent-dark); }}
  button:disabled {{ background: #9db6e8; cursor: not-allowed; }}
  .banner {{
    margin-top: 18px;
    padding: 12px 14px;
    border-radius: 8px;
    font-size: 13.5px;
    line-height: 1.4;
    word-break: break-word;
  }}
  .banner.ok {{ background: var(--ok-bg); color: var(--ok-text); }}
  .banner.err {{ background: var(--err-bg); color: var(--err-text); }}
</style>
</head>
<body>
  <div class="card">
    <div class="card-header">
      <h1>Outbound Call Console</h1>
      <p>Trigger a call through the voice agent</p>
    </div>
    <div class="card-body">
      <form method="post" action="/call" id="call-form">
        <label for="to_number">Phone number</label>
        <input type="tel" id="to_number" name="to_number" placeholder="+91XXXXXXXXXX" required>
        <div class="hint">E.164 format, with country code (e.g. +91 for India).</div>
        <button type="submit">Call</button>
      </form>
      {message}
    </div>
  </div>
  <script>
    document.getElementById("call-form").addEventListener("submit", function (e) {{
      var btn = e.target.querySelector("button");
      btn.disabled = true;
      btn.textContent = "Calling...";
    }});
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index(_: None = Depends(require_auth)):
    return PAGE.format(message="")


@app.post("/call", response_class=HTMLResponse)
async def call(to_number: str = Form(...), _: None = Depends(require_auth)):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{os.getenv('TWILIO_ACCOUNT_SID')}/Calls.json",
            data={
                "To": to_number,
                "From": os.getenv("TWILIO_FROM_NUMBER"),
                "Url": os.getenv("VOICE_WEBHOOK_URL"),
            },
            auth=(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")),
        )

    if resp.status_code >= 400:
        message = f"<div class='banner err'>Failed: {resp.text}</div>"
    else:
        message = f"<div class='banner ok'>Call started to {to_number}.</div>"

    return PAGE.format(message=message)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8001)))
