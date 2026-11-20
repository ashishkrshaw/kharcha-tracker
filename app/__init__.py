import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='../templates')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dubai-diary-secure-key-2026')

# -------------------------------------------------------------
# Permanent Database Configuration (Never get erased)
# -------------------------------------------------------------
# 1. JSONBin.io: If JSONBIN_API_KEY and JSONBIN_BIN_ID are set,
#    data is automatically synced and restored from the cloud across redeploys!
# 2. If DATABASE_URL is set (e.g. Free Render PostgreSQL or Supabase/Neon),
#    use it for database persistence.
# 3. If a Render Persistent Disk is mounted at /var/data or /data, use that SQLite path.
# 4. Otherwise fallback to local SQLite database.
db_url = os.getenv('DATABASE_URL')
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
elif os.path.exists('/var/data'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////var/data/dubaidiary.db'
elif os.path.exists('/data'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////data/dubaidiary.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dubaidiary.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail settings (Gmail SMTP)
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
login_manager.login_message = 'Please login with your secret PIN to access Dubai Diary.'
login_manager.login_message_category = 'warning'

from .models import User
from .jsonbin_sync import sync_from_jsonbin, is_jsonbin_configured
from . import routes  # noqa: E402

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

    # If JSONBin is configured, restore all expenses & users from cloud
    if is_jsonbin_configured():
        sync_from_jsonbin(app)

    # Migrate any old "Uncle" account name to "Amit Uncle"
    old_uncle = User.query.filter_by(name="Uncle").first()
    if old_uncle:
        old_uncle.name = "Amit Uncle"
        db.session.commit()

    # Default Hard PINs
    # Ashish: 839217 (or from env ASHISH_DEFAULT_PIN)
    # Amit Uncle: 591428 (or from env AMIT_UNCLE_DEFAULT_PIN)
    ashish_default_pin = os.getenv("ASHISH_DEFAULT_PIN", "839217")
    uncle_default_pin = os.getenv("AMIT_UNCLE_DEFAULT_PIN", "591428")

    if not User.query.filter_by(name="Amit Uncle").first():
        amit_uncle = User(name="Amit Uncle")
        amit_uncle.set_pin(uncle_default_pin)
        db.session.add(amit_uncle)

    if not User.query.filter_by(name="Ashish").first():
        ashish = User(name="Ashish")
        ashish.set_pin(ashish_default_pin)
        db.session.add(ashish)

    db.session.commit()
