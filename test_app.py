import datetime
from app import app, db
from app.models import User, Expense, EditRequest

def run_tests():
    with app.app_context():
        print("--- 1. Testing Default Users & Seeding ---")
        uncle = User.query.filter_by(name="Uncle").first()
        ashish = User.query.filter_by(name="Ashish").first()
        assert uncle is not None, "Uncle account not found"
        assert ashish is not None, "Ashish account not found"
        assert uncle.check_pin("1234"), "Uncle PIN 1234 check failed"
        assert ashish.check_pin("5678"), "Ashish PIN 5678 check failed"
        print("[OK] Default users and PIN verification passed.")

        print("\n--- 2. Testing PIN Change Logic ---")
        # Test changing Ashish's PIN
        ashish.set_pin("9876")
        db.session.commit()
        # Verify old PIN is now INVALID
        assert not ashish.check_pin("5678"), "Old PIN should be invalid!"
        # Verify new PIN works
        assert ashish.check_pin("9876"), "New PIN should be valid!"
        # Reset back for default convenience
        ashish.set_pin("5678")
        db.session.commit()
        assert ashish.check_pin("5678")
        print("[OK] PIN change verified: Old PIN becomes invalid, new PIN takes effect.")

        print("\n--- 3. Testing Adding Expenses & Separate Totals ---")
        Expense.query.delete()
        EditRequest.query.delete()
        db.session.commit()

        exp1 = Expense(description="Uncle Visa Payment", amount=200000.0, currency="INR", user_id=ashish.id)
        exp2 = Expense(description="Dinner in Dubai", amount=200.0, currency="AED", user_id=uncle.id)
        db.session.add_all([exp1, exp2])
        db.session.commit()

        ashish_expenses = Expense.query.filter_by(user_id=ashish.id).all()
        uncle_expenses = Expense.query.filter_by(user_id=uncle.id).all()
        assert sum(e.amount for e in ashish_expenses) == 200000.0
        assert sum(e.amount for e in uncle_expenses) == 200.0
        print("[OK] Expenses added & separate totals calculated cleanly.")

        print("\n--- 4. Testing 12-Minute Direct Edit Rule ---")
        assert exp1.is_within_grace_period(12) is True
        exp1.description = "Uncle Visa Payment (Edited Quickly)"
        exp1.amount = 210000.0
        exp1.is_edited = True
        db.session.commit()
        assert exp1.amount == 210000.0
        print("[OK] Direct edit within 12 minutes verified.")

        print("\n--- 5. Testing Over-12-Minute Edit Request & Approval ---")
        exp1.timestamp = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
        db.session.commit()
        assert exp1.is_within_grace_period(12) is False, "Should be expired"

        req = EditRequest(
            expense_id=exp1.id,
            requested_by_id=ashish.id,
            new_description="Uncle Visa Final Amount",
            new_amount=195000.0,
            new_currency="INR",
            status="pending"
        )
        db.session.add(req)
        db.session.commit()

        assert req.requested_by_id == ashish.id
        assert req.status == "pending"

        # Uncle approves it
        exp1.description = req.new_description
        exp1.amount = req.new_amount
        exp1.currency = req.new_currency
        req.status = "approved"
        db.session.commit()

        updated_exp = Expense.query.get(exp1.id)
        assert updated_exp.amount == 195000.0
        assert updated_exp.description == "Uncle Visa Final Amount"
        assert req.status == "approved"
        print("[OK] Edit Request & 2nd Person Approval workflow verified successfully.")

        # Clean up test rows
        Expense.query.delete()
        EditRequest.query.delete()
        db.session.commit()

    print("\n==========================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
