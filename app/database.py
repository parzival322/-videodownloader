# from enum import unique
#
# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime
# from flask_login import UserMixin
# from app import db, login_manager
#
# class User(db.Model, UserMixin):
#     __tablename__ = 'user'
#
#     id = db.Column(db.Integer, primary_key=True)
#     email = db.Column(128, nullable=False, unique=True)
#     login = db.Column(db.String(128), nullable=False, unique=True)
#     password = db.Column(db.String(128), nullable=False)