import datetime
import threading
from collections import defaultdict
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from . import app, db, mail
from .models import User, Expense, EditRequest
from .jsonbin_sync import trigger_cloud_backup

EDIT_GRACE_PERIOD_MINUTES = 12

def send_async_email(app_obj, msg):
    with app_obj.app_context():
        try:
            if app_obj.config.get('MAIL_USERNAME') and app_obj.config.get('MAIL_PASSWORD'):
                mail.send(msg)
        except Exception as e:
            app_obj.logger.warning(f"Failed to send email notification: {e}")

def notify_via_email(subject: str, body: str):
    """Safely dispatches an email notification via Gmail SMTP in background thread."""
    recipient = current_app.config.get('MAIL_USERNAME')
    if not recipient or not current_app.config.get('MAIL_PASSWORD'):
        return
    msg = Message(
        subject=subject,
        recipients=[recipient],
        body=body,
    )
    thr = threading.Thread(target=send_async_email, args=(current_app._get_current_object(), msg))
    thr.daemon = True
    thr.start()

@app.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
        
    users = User.query.order_by(User.name).all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        pin = request.form.get("pin", "").strip()
        
        user = User.query.filter_by(name=name).first()
        if user and user.check_pin(pin):
            login_user(user, remember=True)
            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))
        flash("Invalid user name or PIN. Please try again.", "danger")
        
    return render_template("login.html", users=users)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/change-pin", methods=["GET", "POST"])
@login_required
def change_pin():
    """Allows current user to replace their old PIN with a new PIN."""
    if request.method == "POST":
        old_pin = request.form.get("old_pin", "").strip()
        new_pin = request.form.get("new_pin", "").strip()
        confirm_pin = request.form.get("confirm_pin", "").strip()

        # Validation
        if not current_user.check_pin(old_pin):
            flash("Current PIN is incorrect.", "danger")
            return render_template("change_pin.html")

        if len(new_pin) < 4 or not new_pin.isdigit():
            flash("New PIN must be at least 4 digits (numbers only).", "warning")
            return render_template("change_pin.html")

        if new_pin == old_pin:
            flash("New PIN cannot be the same as your old PIN.", "warning")
            return render_template("change_pin.html")

        if new_pin != confirm_pin:
            flash("New PIN and Confirm PIN do not match.", "danger")
            return render_template("change_pin.html")

        # Set new PIN
        current_user.set_pin(new_pin)
        db.session.commit()
        trigger_cloud_backup(current_app._get_current_object())

        notify_via_email(
            subject=f"🔐 Security Alert: PIN Changed for {current_user.name}",
            body=(
                f"Hello,\n\n"
                f"The account PIN for {current_user.name} was changed successfully.\n"
                f"The old PIN has been permanently invalidated.\n"
                f"Time: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                f"If you did not perform this change, please contact support immediately."
            )
        )

        flash("Your PIN has been changed successfully! Old PIN is now invalid.", "success")
        return redirect(url_for("dashboard"))

    return render_template("change_pin.html")

@app.route("/dashboard")
@login_required
def dashboard():
    all_expenses = Expense.query.order_by(Expense.timestamp.desc()).all()
    all_users = User.query.order_by(User.name).all()

    # Calculate separate totals for each person per currency (No mixing!)
    # totals_by_user: { 'Ashish': {'INR': 200000.0, 'AED': 0.0}, 'Uncle': {'AED': 200.0} }
    totals_by_user = defaultdict(lambda: defaultdict(float))
    for exp in all_expenses:
        curr = (exp.currency or "INR").upper()
        totals_by_user[exp.owner.name][curr] += float(exp.amount)

    # Edit requests pending approval by the current user (sent by other user)
    requests_to_review = (
        EditRequest.query.filter(
            EditRequest.requested_by_id != current_user.id,
            EditRequest.status == "pending"
        )
        .order_by(EditRequest.created_at.desc())
        .all()
    )

    # Pending edit requests submitted by current user (waiting for other user)
    my_pending_requests = (
        EditRequest.query.filter(
            EditRequest.requested_by_id == current_user.id,
            EditRequest.status == "pending"
        )
        .order_by(EditRequest.created_at.desc())
        .all()
    )

    return render_template(
        "dashboard.html",
        expenses=all_expenses,
        all_users=all_users,
        totals_by_user=totals_by_user,
        requests_to_review=requests_to_review,
        my_pending_requests=my_pending_requests,
        grace_period=EDIT_GRACE_PERIOD_MINUTES,
    )

@app.route("/expense/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        currency = request.form.get("currency", "INR").strip().upper()
        
        try:
            amount = float(request.form.get("amount", "0"))
            if amount <= 0:
                raise ValueError()
        except ValueError:
            flash("Please enter a valid positive expense amount.", "danger")
            return render_template("add_expense.html")

        if not description:
            flash("Please provide an expense description.", "warning")
            return render_template("add_expense.html")

        expense = Expense(
            description=description,
            amount=amount,
            currency=currency,
            user_id=current_user.id,
        )
        db.session.add(expense)
        db.session.commit()
        trigger_cloud_backup(current_app._get_current_object())

        # Send email alert
        notify_via_email(
            subject=f"💰 New Expense Added by {current_user.name}: {currency} {amount:,.2f}",
            body=(
                f"Hello,\n\n"
                f"{current_user.name} added a new expense:\n"
                f"----------------------------------------\n"
                f"Description: {description}\n"
                f"Amount: {currency} {amount:,.2f}\n"
                f"Paid by: {current_user.name}\n"
                f"Date & Time: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"----------------------------------------\n\n"
                f"You can view and verify this in your Expense Tracker dashboard."
            )
        )

        flash(f"Expense of {currency} {amount:,.2f} recorded successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_expense.html")

@app.route("/expense/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)

    # Only creator of expense can request/perform an edit
    if expense.user_id != current_user.id:
        flash("You can only edit expenses that you added.", "danger")
        return redirect(url_for("dashboard"))

    within_grace = expense.is_within_grace_period(EDIT_GRACE_PERIOD_MINUTES)
    minutes_left = expense.minutes_remaining_for_direct_edit(EDIT_GRACE_PERIOD_MINUTES)

    if request.method == "POST":
        new_desc = request.form.get("description", "").strip()
        new_curr = request.form.get("currency", expense.currency).strip().upper()
        try:
            new_amount = float(request.form.get("amount", "0"))
            if new_amount <= 0:
                raise ValueError()
        except ValueError:
            flash("Please enter a valid positive amount.", "danger")
            return render_template(
                "edit_expense.html",
                expense=expense,
                within_grace=within_grace,
                minutes_left=minutes_left,
            )

        if not new_desc:
            flash("Description cannot be empty.", "warning")
            return render_template(
                "edit_expense.html",
                expense=expense,
                within_grace=within_grace,
                minutes_left=minutes_left,
            )

        # Re-check grace period on submit
        if expense.is_within_grace_period(EDIT_GRACE_PERIOD_MINUTES):
            # Direct Edit allowed!
            old_info = f"{expense.currency} {expense.amount:,.2f} - {expense.description}"
            expense.description = new_desc
            expense.amount = new_amount
            expense.currency = new_curr
            expense.is_edited = True
            db.session.commit()
            trigger_cloud_backup(current_app._get_current_object())

            notify_via_email(
                subject=f"✏️ Expense Edited Directly by {current_user.name}",
                body=(
                    f"Hello,\n\n"
                    f"{current_user.name} edited an expense directly within the {EDIT_GRACE_PERIOD_MINUTES}-minute window:\n"
                    f"Previous: {old_info}\n"
                    f"Updated: {new_curr} {new_amount:,.2f} - {new_desc}\n"
                    f"Time: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                )
            )

            flash(f"Expense updated directly (within the {EDIT_GRACE_PERIOD_MINUTES}-minute grace window)!", "success")
            return redirect(url_for("dashboard"))
        else:
            # Beyond 12 minutes: Requires approval from 2nd person!
            # Check if there is already a pending request
            existing_req = EditRequest.query.filter_by(expense_id=expense.id, status="pending").first()
            if existing_req:
                flash("There is already a pending edit request waiting for approval for this expense.", "warning")
                return redirect(url_for("dashboard"))

            edit_req = EditRequest(
                expense_id=expense.id,
                requested_by_id=current_user.id,
                new_description=new_desc,
                new_amount=new_amount,
                new_currency=new_curr,
                status="pending",
            )
            db.session.add(edit_req)
            db.session.commit()
            trigger_cloud_backup(current_app._get_current_object())

            notify_via_email(
                subject=f"⚠️ Edit Request from {current_user.name} (Action Required)",
                body=(
                    f"Hello,\n\n"
                    f"{current_user.name} requested to edit an expense (after {EDIT_GRACE_PERIOD_MINUTES} minutes):\n"
                    f"Current: {expense.currency} {expense.amount:,.2f} - {expense.description}\n"
                    f"Requested Changes: {new_curr} {new_amount:,.2f} - {new_desc}\n\n"
                    f"Please login to the Expense Tracker to APPROVE or REJECT this edit."
                )
            )

            flash(
                f"More than {EDIT_GRACE_PERIOD_MINUTES} minutes have passed. "
                "An edit request has been sent to the other person for approval!",
                "info"
            )
            return redirect(url_for("dashboard"))

    return render_template(
        "edit_expense.html",
        expense=expense,
        within_grace=within_grace,
        minutes_left=minutes_left,
    )

@app.route("/edit-request/<int:req_id>/approve", methods=["POST"])
@login_required
def approve_edit(req_id):
    edit_req = EditRequest.query.get_or_404(req_id)

    # Make sure the user approving is the OTHER person, not the one who requested it!
    if edit_req.requested_by_id == current_user.id:
        flash("You cannot approve your own edit request. The second person must approve it.", "danger")
        return redirect(url_for("dashboard"))

    if edit_req.status != "pending":
        flash("This edit request has already been processed.", "warning")
        return redirect(url_for("dashboard"))

    # Apply changes to expense
    expense = edit_req.expense
    old_details = f"{expense.currency} {expense.amount:,.2f} - {expense.description}"
    expense.description = edit_req.new_description
    expense.amount = edit_req.new_amount
    expense.currency = edit_req.new_currency
    expense.is_edited = True

    edit_req.status = "approved"
    edit_req.reviewed_at = datetime.datetime.utcnow()
    db.session.commit()
    trigger_cloud_backup(current_app._get_current_object())

    notify_via_email(
        subject=f"✅ Edit Request Approved by {current_user.name}",
        body=(
            f"Hello,\n\n"
            f"{current_user.name} has APPROVED the edit request from {edit_req.requester.name}:\n"
            f"Previous: {old_details}\n"
            f"New Values: {expense.currency} {expense.amount:,.2f} - {expense.description}\n"
            f"Time: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
    )

    flash("Edit request approved! The expense has been updated.", "success")
    return redirect(url_for("dashboard"))

@app.route("/edit-request/<int:req_id>/reject", methods=["POST"])
@login_required
def reject_edit(req_id):
    edit_req = EditRequest.query.get_or_404(req_id)

    if edit_req.requested_by_id == current_user.id:
        flash("You cannot reject your own request here.", "danger")
        return redirect(url_for("dashboard"))

    if edit_req.status != "pending":
        flash("This edit request has already been processed.", "warning")
        return redirect(url_for("dashboard"))

    edit_req.status = "rejected"
    edit_req.reviewed_at = datetime.datetime.utcnow()
    db.session.commit()
    trigger_cloud_backup(current_app._get_current_object())

    notify_via_email(
        subject=f"❌ Edit Request Rejected by {current_user.name}",
        body=(
            f"Hello,\n\n"
            f"{current_user.name} has REJECTED the edit request for:\n"
            f"{edit_req.expense.description}\n"
            f"Requested: {edit_req.new_currency} {edit_req.new_amount:,.2f} - {edit_req.new_description}\n"
            f"The original expense remains unchanged."
        )
    )

    flash("Edit request rejected. The original expense remains unchanged.", "info")
    return redirect(url_for("dashboard"))
