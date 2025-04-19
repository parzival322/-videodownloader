from flask import Flask, render_template, request, flash, url_for, make_response, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

# Инициализация приложения, БД, миграции и логин-менеджера

app = Flask(__name__, template_folder='templates')
app.secret_key = 'abobes'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
migrate = Migrate(app=app, db=db)

login_manager = LoginManager()
login_manager.init_app(app)

from app import database
from app import routes
