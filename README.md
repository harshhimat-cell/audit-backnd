# AuBit Backend API

FastAPI + PostgreSQL backend for AuBit.

## Endpoints

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| POST | /auth/register | — | Register new user |
| POST | /auth/login | — | Login, get JWT token |
| GET | /auth/me | User | Get current user |
| POST | /waitlist/join | — | Join waitlist |
| GET | /waitlist/check/{email} | — | Check waitlist status |
| GET | /vault/ | User | Get vault balances + allocation |
| PUT | /vault/allocation | User | Update asset allocation |
| POST | /rewards/transact | User | Log a card transaction, earn rewards |
| GET | /rewards/history | User | Transaction history |
| GET | /rewards/summary | User | Spending + rewards summary |
| GET | /admin/waitlist | Admin | All waitlist entries |
| GET | /admin/users | Admin | All users |
| GET | /admin/stats | Admin | Platform-wide stats |
| PUT | /admin/users/{id}/deactivate | Admin | Deactivate a user |

Interactive docs available at `/docs` once running.

---

## Setup

### 1. Clone and install

```bash
cd aubit-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up PostgreSQL

```bash
psql -U postgres
CREATE DATABASE aubit_db;
CREATE USER aubit WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE aubit_db TO aubit;
\q
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your DATABASE_URL and a strong SECRET_KEY
```

Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API is live at `http://localhost:8000`
Docs at `http://localhost:8000/docs`

---

## Make yourself admin

After registering your account, run this in psql:

```sql
UPDATE users SET role = 'admin' WHERE email = 'your@email.com';
```

---

## Connect to the frontend

Add your API URL to the website's email form — replace the `handleSubmit()` function in `index.html`:

```javascript
async function handleSubmit() {
  const email = document.getElementById('inv-email').value;
  if (!email || !email.includes('@')) return;

  const res = await fetch('https://your-api-url.com/waitlist/join', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, is_investor: true, source: 'website' })
  });

  const data = await res.json();
  if (res.ok) {
    document.getElementById('cta-fb').textContent =
      `✓ You're #${data.position} on the list. We'll be in touch.`;
  }
}
```

---

## Deploy to a server

```bash
# Install on Ubuntu/Debian
sudo apt update && sudo apt install python3-pip postgresql nginx -y

# Run with gunicorn in production
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Use nginx as a reverse proxy and add an SSL cert via Let's Encrypt (`certbot`).
