# 💰 Kharcha Tracker (Split & Expense Manager)

A streamlined, secure shared expense tracking web application designed for family/partners (e.g., Ashish & Uncle).

---

## ✨ Features

1. **Separate PIN Authentication**:
   - Individual PIN-based login for each person.
   - Pre-seeded accounts: **Uncle** (PIN: `1234`) and **Ashish** (PIN: `5678`).
2. **Change PIN Anytime**:
   - Change your PIN from the dashboard (`Change PIN`).
   - Requires verification of your current PIN.
   - The old PIN is immediately invalidated and replaced with the new one.
   - Triggers an email security notification.
3. **Separate Ledger & Totals (No Confusion / No Mixing)**:
   - Displays clear totals for each person per currency (e.g. Total INR, Total AED).
   - Shows all transactions in a unified timeline with color-coded badges.
4. **Smart 12-Minute Edit Rule**:
   - **Within 12 Minutes**: Creator can edit mistakes directly without needing approval.
   - **After 12 Minutes**: Submitting changes creates an **Edit Request** that is sent to the 2nd person for approval.
   - The 2nd person can **Approve** or **Reject** the request from their dashboard.
5. **Gmail SMTP Notifications**:
   - Automatically dispatches email notifications for:
     - New expense added.
     - Direct edit performed.
     - New edit request submitted (> 12 minutes).
     - Edit request approved or rejected.
     - Security alert when PIN is changed.

---

## 🚀 Running Locally

```bash
# 1. Navigate to directory
cd expense_tracker

# 2. (Optional) Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your .env file
# Fill in GMAIL_USER and GMAIL_APP_PASSWORD

# 5. Run the server
python run.py
```

Access the app at: **`http://127.0.0.1:5000`**

---

## 🌐 Deploying to Render

1. Push this repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Kharcha Tracker"
   git remote add origin https://github.com/<YOUR-USERNAME>/<REPO-NAME>.git
   git branch -M main
   git push -u origin main
   ```
2. Log into [Render.com](https://render.com) and click **New +** -> **Web Service**.
3. Connect your GitHub repository.
4. Render will auto-detect settings from `Procfile` and `runtime.txt`:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn run:app`
5. In **Environment Variables**, add:
   - `SECRET_KEY`: `<any-random-secret-string>`
   - `GMAIL_USER`: `<your-gmail-address>`
   - `GMAIL_APP_PASSWORD`: `<your-16-char-gmail-app-password>`
6. Click **Deploy Web Service**! Render will build and deploy your app with a free HTTPS URL.
