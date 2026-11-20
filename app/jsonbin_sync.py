import os
import json
import threading
import datetime
import requests
from flask import current_app

JSONBIN_BASE_URL = "https://api.jsonbin.io/v3/b"

def get_jsonbin_credentials():
    api_key = os.getenv("JSONBIN_API_KEY") or os.getenv("JSONBIN_MASTER_KEY") or os.getenv("JSONBIN_KEY")
    bin_id = os.getenv("JSONBIN_BIN_ID") or os.getenv("JSONBIN_ID")
    return (api_key.strip() if api_key else None, bin_id.strip() if bin_id else None)

def is_jsonbin_configured():
    api_key, bin_id = get_jsonbin_credentials()
    return bool(api_key and bin_id)

def get_headers():
    api_key, _ = get_jsonbin_credentials()
    return {
        "Content-Type": "application/json",
        "X-Master-Key": api_key,
    }

def create_bin_if_needed(initial_data):
    """If API key is given but no BIN_ID, automatically creates a new Bin."""
    api_key, bin_id = get_jsonbin_credentials()
    if api_key and not bin_id:
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Master-Key": api_key,
                "X-Bin-Name": "Dubai Diary Storage",
            }
            res = requests.post(JSONBIN_BASE_URL, headers=headers, json=initial_data, timeout=10)
            if res.status_code in (200, 201):
                data = res.json()
                new_bin_id = data.get("metadata", {}).get("id")
                print(f"\n========================================================")
                print(f"[JSONBin] Created new bin successfully! BIN_ID: {new_bin_id}")
                print(f"Set JSONBIN_BIN_ID={new_bin_id} in your environment variables.")
                print(f"========================================================\n")
                return new_bin_id
        except Exception as e:
            print(f"[JSONBin] Could not auto-create bin: {e}")
    return bin_id

def export_db_to_dict():
    from .models import User, Expense, EditRequest
    users_data = []
    for u in User.query.all():
        users_data.append({
            "id": u.id,
            "name": u.name,
            "pin_hash": u.pin_hash,
        })

    expenses_data = []
    for e in Expense.query.all():
        expenses_data.append({
            "id": e.id,
            "description": e.description,
            "amount": float(e.amount),
            "currency": e.currency,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "user_id": e.user_id,
            "is_edited": e.is_edited,
        })

    requests_data = []
    for r in EditRequest.query.all():
        requests_data.append({
            "id": r.id,
            "expense_id": r.expense_id,
            "requested_by_id": r.requested_by_id,
            "new_description": r.new_description,
            "new_amount": float(r.new_amount),
            "new_currency": r.new_currency,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        })

    return {
        "app": "Dubai Diary",
        "last_synced": datetime.datetime.utcnow().isoformat(),
        "users": users_data,
        "expenses": expenses_data,
        "edit_requests": requests_data,
    }

def sync_from_jsonbin(app_obj):
    """Pulls cloud data on startup to restore expenses & PINs if running on fresh container."""
    api_key, bin_id = get_jsonbin_credentials()
    if not (api_key and bin_id):
        return

    with app_obj.app_context():
        from . import db
        from .models import User, Expense, EditRequest
        try:
            url = f"{JSONBIN_BASE_URL}/{bin_id}/latest"
            headers = {"X-Master-Key": api_key}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                record = res.json().get("record", {})
                cloud_users = record.get("users", [])
                cloud_expenses = record.get("expenses", [])
                cloud_requests = record.get("edit_requests", [])

                # 1. Sync Users
                for u_data in cloud_users:
                    user = User.query.filter_by(name=u_data["name"]).first()
                    if not user:
                        user = User(id=u_data.get("id"), name=u_data["name"], pin_hash=u_data["pin_hash"])
                        db.session.add(user)
                    else:
                        # Restore custom PIN if present in cloud
                        if u_data.get("pin_hash"):
                            user.pin_hash = u_data["pin_hash"]

                db.session.commit()

                # 2. Sync Expenses
                for e_data in cloud_expenses:
                    existing = db.session.get(Expense, e_data["id"])
                    ts = datetime.datetime.fromisoformat(e_data["timestamp"]) if e_data.get("timestamp") else datetime.datetime.utcnow()
                    if not existing:
                        exp = Expense(
                            id=e_data["id"],
                            description=e_data["description"],
                            amount=float(e_data["amount"]),
                            currency=e_data["currency"],
                            timestamp=ts,
                            user_id=e_data["user_id"],
                            is_edited=e_data.get("is_edited", False),
                        )
                        db.session.add(exp)
                    else:
                        existing.description = e_data["description"]
                        existing.amount = float(e_data["amount"])
                        existing.currency = e_data["currency"]
                        existing.is_edited = e_data.get("is_edited", False)

                db.session.commit()

                # 3. Sync Edit Requests
                for r_data in cloud_requests:
                    existing_req = db.session.get(EditRequest, r_data["id"])
                    c_ts = datetime.datetime.fromisoformat(r_data["created_at"]) if r_data.get("created_at") else datetime.datetime.utcnow()
                    r_ts = datetime.datetime.fromisoformat(r_data["reviewed_at"]) if r_data.get("reviewed_at") else None
                    if not existing_req:
                        req = EditRequest(
                            id=r_data["id"],
                            expense_id=r_data["expense_id"],
                            requested_by_id=r_data["requested_by_id"],
                            new_description=r_data["new_description"],
                            new_amount=float(r_data["new_amount"]),
                            new_currency=r_data["new_currency"],
                            status=r_data["status"],
                            created_at=c_ts,
                            reviewed_at=r_ts,
                        )
                        db.session.add(req)
                    else:
                        existing_req.status = r_data["status"]
                        existing_req.reviewed_at = r_ts

                db.session.commit()
                print(f"[JSONBin] Successfully restored data from JSONBin.io (Users: {len(cloud_users)}, Expenses: {len(cloud_expenses)})")
            else:
                print(f"[JSONBin] Failed to fetch latest bin: Status {res.status_code}")
        except Exception as e:
            print(f"[JSONBin] Sync from cloud failed: {e}")

def _push_worker(app_obj, payload):
    api_key, bin_id = get_jsonbin_credentials()
    if not (api_key and bin_id):
        return
    try:
        url = f"{JSONBIN_BASE_URL}/{bin_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Master-Key": api_key,
        }
        res = requests.put(url, headers=headers, json=payload, timeout=12)
        if res.status_code == 200:
            print("[JSONBin] Cloud storage updated successfully.")
        else:
            print(f"[JSONBin] Cloud update returned status: {res.status_code}")
    except Exception as e:
        print(f"[JSONBin] Cloud push failed: {e}")

def trigger_cloud_backup(app_obj):
    """Triggers an asynchronous background update to JSONBin.io."""
    if not is_jsonbin_configured():
        return
    with app_obj.app_context():
        try:
            payload = export_db_to_dict()
            thr = threading.Thread(target=_push_worker, args=(app_obj, payload))
            thr.daemon = True
            thr.start()
        except Exception as e:
            print(f"[JSONBin] Could not trigger backup: {e}")
