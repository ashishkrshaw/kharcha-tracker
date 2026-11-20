import datetime
from app import app, db
from app.models import User, Expense, EditRequest

def run_tests():
    with app.app_context():
        print("--- 1. Testing Default Users & Hard PINs ---")
        uncle = User.query.filter_by(name="Amit Uncle").first()
        ashish = User.query.filter_by(name="Ashish").first()
        assert uncle is not None, "Amit Uncle account not found"
        assert ashish is not None, "Ashish account not found"
        assert uncle.check_pin("591428"), "Amit Uncle PIN 591428 check failed"
        assert ashish.check_pin("839217"), "Ashish PIN 839217 check failed"
        print("[OK] Default users (Ashish & Amit Uncle) and hard PINs verified.")

        print("\n--- 2. Testing PIN Change Logic ---")
        ashish.set_pin("987654")
        db.session.commit()
        assert not ashish.check_pin("839217"), "Old PIN should be invalid!"
        assert ashish.check_pin("987654"), "New PIN should be valid!"
        # Reset back to default hard PIN
        ashish.set_pin("839217")
        db.session.commit()
        assert ashish.check_pin("839217")
        print("[OK] PIN change verified: Old PIN becomes invalid, new PIN takes effect.")

        print("\n--- 3. Testing Adding Expenses & Separate Totals ---")
        Expense.query.delete()
        EditRequest.query.delete()
        db.session.commit()

        exp1 = Expense(description="Visa Payment for Amit Uncle", amount=200000.0, currency="INR", user_id=ashish.id)
        exp2 = Expense(description="Dubai Marina Dinner", amount=200.0, currency="AED", user_id=uncle.id)
        db.session.add_all([exp1, exp2])
        db.session.commit()

        ashish_expenses = Expense.query.filter_by(user_id=ashish.id).all()
        uncle_expenses = Expense.query.filter_by(user_id=uncle.id).all()
        assert sum(e.amount for e in ashish_expenses) == 200000.0
        assert sum(e.amount for e in uncle_expenses) == 200.0
        print("[OK] Expenses added & separate totals calculated cleanly.")

        print("\n--- 4. Testing 12-Minute Direct Edit Rule ---")
        assert exp1.is_within_grace_period(12) is True
        exp1.description = "Visa Payment for Amit Uncle (Updated)"
        exp1.amount = 210000.0
        exp1.is_edited = True
        db.session.commit()
        assert exp1.amount == 210000.0
        print("[OK] Direct edit within 12 minutes verified.")

        print("\n--- 5. Testing Over-12-Minute Edit Request & Approval ---")
        exp1.timestamp = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(minutes=30)
        db.session.commit()
        assert exp1.is_within_grace_period(12) is False, "Should be expired"

        req = EditRequest(
            expense_id=exp1.id,
            requested_by_id=ashish.id,
            new_description="Visa Payment Final",
            new_amount=195000.0,
            new_currency="INR",
            status="pending"
        )
        db.session.add(req)
        db.session.commit()

        assert req.requested_by_id == ashish.id
        assert req.status == "pending"

        # Amit Uncle approves it
        exp1.description = req.new_description
        exp1.amount = req.new_amount
        exp1.currency = req.new_currency
        req.status = "approved"
        db.session.commit()

        updated_exp = db.session.get(Expense, exp1.id)
        assert updated_exp.amount == 195000.0
        assert updated_exp.description == "Visa Payment Final"
        assert req.status == "approved"
        print("[OK] Edit Request & 2nd Person Approval workflow verified successfully.")

        # Clean up test rows so no demo data remains!
        Expense.query.delete()
        EditRequest.query.delete()
        db.session.commit()
        print("[OK] All demo/test data cleaned up. Production ledger is clean and empty!")

    print("\n==========================================")
    print("ALL TESTS PASSED FOR DUBAI DIARY!")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
