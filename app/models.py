import datetime
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    pin_hash = db.Column(db.String(256), nullable=False)

    expenses = db.relationship('Expense', backref='owner', lazy=True, cascade='all, delete-orphan')
    edit_requests = db.relationship('EditRequest', foreign_keys='EditRequest.requested_by_id', backref='requester', lazy=True)

    def set_pin(self, pin: str):
        self.pin_hash = generate_password_hash(str(pin).strip())

    def check_pin(self, pin: str) -> bool:
        return check_password_hash(self.pin_hash, str(pin).strip())

    def __repr__(self):
        return f"<User {self.name}>"

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default='INR')
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_edited = db.Column(db.Boolean, default=False)

    edit_requests = db.relationship('EditRequest', backref='expense', lazy=True, cascade='all, delete-orphan')

    def is_within_grace_period(self, minutes: int = 12) -> bool:
        elapsed_seconds = (datetime.datetime.utcnow() - self.timestamp).total_seconds()
        return elapsed_seconds <= (minutes * 60)

    def minutes_remaining_for_direct_edit(self, minutes: int = 12) -> int:
        elapsed_seconds = (datetime.datetime.utcnow() - self.timestamp).total_seconds()
        remaining = (minutes * 60) - elapsed_seconds
        return max(0, int(remaining // 60))

class EditRequest(db.Model):
    __tablename__ = 'edit_requests'
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=False)
    requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    new_description = db.Column(db.String(255), nullable=False)
    new_amount = db.Column(db.Float, nullable=False)
    new_currency = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
