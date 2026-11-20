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
4. **Permanent Cloud Sync with JSONBin.io (Never Erased)**:
   - Synchronizes all expenses, edit requests, and custom PINs with **JSONBin.io**.
   - Whenever Render restarts or redeploys, data is automatically restored from the cloud.
5. **Separate Calculations**:
   - Totals for Ashish and Amit Uncle are tracked separately per currency (`INR`, `AED`, `USD`, `EUR`). No mixing!
6. **12-Minute Edit Window**:
   - **Within 12 minutes**: Quick typo or amount fix applied directly.
   - **After 12 minutes**: Sends an approval request to the second person.
7. **Gmail SMTP Alerts**:
   - Instant email notifications for all expenses, edits, approvals, and PIN changes.

---

## ☁️ How to Connect JSONBin.io (Data is NEVER Erased)

1. Go to **[https://jsonbin.io](https://jsonbin.io)** and log in / create a free account.
2. In the sidebar, go to **API Keys** $\rightarrow$ copy your **Master Key** (starts with `$2a$10$...`).
3. Click **"Create Bin"** (top right) $\rightarrow$ paste empty JSON `{}` $\rightarrow$ click **Save** $\rightarrow$ copy the **Bin ID** (e.g. `673ea...`).
4. Go to your **Render Web Service** $\rightarrow$ **Environment** $\rightarrow$ add these two environment variables:
   * **`JSONBIN_API_KEY`**: *(paste your Master Key)*
   * **`JSONBIN_BIN_ID`**: *(paste your Bin ID)*
5. Click **Save Changes**.

> **How it works:**  
> - Every time an expense is saved, edited, or a PIN is changed, Dubai Diary pushes the update to JSONBin in the background.  
> - When Render redeploys or restarts on a new container, Dubai Diary automatically restores all your expenses and custom PINs from JSONBin!

---

## 🚀 Running Locally

```bash
cd expense_tracker
python run.py
```
Open: `http://127.0.0.1:5000`
