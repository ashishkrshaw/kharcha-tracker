# 🇦🇪 Dubai Diary (Ashish & Amit Uncle)

A shared, secure expense ledger built exclusively for **Ashish & Amit Uncle**.

---

## ✨ Features & Setup

1. **Branding & Accounts**:
   - Name: **Dubai Diary**
   - Accounts: **Ashish** and **Amit Uncle**
   - Default Hard PINs:
     - **Ashish**: `839217`
     - **Amit Uncle**: `591428`
2. **Change PIN Anytime**:
   - Each person can change their PIN from the "Change PIN" menu.
   - The old PIN is instantly destroyed and replaced with the new one.
   - Triggers an email security alert.
3. **Clean Ledger (No Demo Data)**:
   - Starts with 0 demo transactions. Ready for real entries.
4. **Data Never Erased on Deploy**:
   - Supports **Render Free PostgreSQL** (or Supabase/Neon) via `DATABASE_URL`.
   - Also supports **Render Persistent Disks** (`/var/data` or `/data`).
   - Connecting a database ensures your expenses and PINs remain permanent across every deploy and container restart!
5. **Separate Calculations**:
   - Totals for Ashish and Amit Uncle are tracked separately per currency (`INR`, `AED`, `USD`, `EUR`). No mixing!
6. **12-Minute Edit Window**:
   - **Within 12 minutes**: Quick typo or amount fix applied directly.
   - **After 12 minutes**: Sends an approval request to the second person.
7. **Gmail SMTP Alerts**:
   - Instant email notifications for all expenses, edits, approvals, and PIN changes.

---

## 🔒 Keeping Data Permanent on Render (Never Erased)

On Render's free tier, application code restarts on fresh containers. To ensure data is **never erased on any deploy**:

### Option 1 (Recommended & 100% Free): Render PostgreSQL Database
1. In your [Render Dashboard](https://dashboard.render.com/), click **New +** $\rightarrow$ **PostgreSQL**.
2. Give it a name (e.g., `dubaidiary-db`), choose the Free plan, and click **Create Database**.
3. Copy the **Internal Database URL** (starts with `postgres://...`).
4. Go to your `kharcha-tracker` Web Service $\rightarrow$ **Environment**.
5. Add an Environment Variable:
   - **Key:** `DATABASE_URL`
   - **Value:** *(paste the Internal Database URL)*
6. Click **Save Changes**.

Your database is now independent of the web service code — data will **never be lost** on redeploys!

---

## 🚀 Running Locally

```bash
cd expense_tracker
python run.py
```
Open: `http://127.0.0.1:5000`
