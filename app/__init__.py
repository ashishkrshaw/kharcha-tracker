import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='../templates')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///expense.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail settings
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('GMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('GMAIL_APP_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('GMAIL_USER')

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login with your PIN to access this page.'
login_manager.login_message_category = 'warning'

from .models import User
from . import routes  # noqa: E402

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    # Ensure default accounts exist
    if not User.query.filter_by(name="Uncle").first():
        uncle = User(name="Uncle")
        uncle.set_pin("1234")
        db.session.add(uncle)
    if not User.query.filter_by(name="Ashish").first():
        ashish = User(name="Ashish")
        ashish.set_pin("5678")
        db.session.add(ashish)
    db.session.commit()
