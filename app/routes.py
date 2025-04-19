from app import app, login_manager, db
from flask import render_template, flash, request, redirect, url_for, make_response, Response
from flask_login import login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import User
from transliterate import translit
import json
import requests
import random

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    email = request.form.get('email')
    login = request.form.get('login')
    password = request.form.get('password')
    password2 = request.form.get('password')

    if request.method == 'POST':
        if not(login or password or password2 or email):
            flash('Пожалуйста, заполните все поля')
        elif password != password2:
            flash('Введеные вами пароли не сходятся')
        else:
            hash_pwd = generate_password_hash(password)
            new_user = User(login=login, password=hash_pwd, email=email)
            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('login_page'))
    else:
        return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    login = request.form.get('login')
    password = request.form.get('password')

    if login and password:
        user = User.query.filter_by(login=login).first()

        if (user and user.login == login) and user.password == generate_password_hash(password):
            login_user(user)

            return redirect(url_for('index'))
        else:
            flash('Логин или пароль некорректен')

    else:
        flash('Пожалуйста введите логин и пароль')
        return render_template('login_page.html')


@app.route('/profile/<int:id>')
@login_required
def profile_page(id):
    user = User.query.get_or_404(id)
    return render_template("profile_page.html", user=user)


if __name__ == '__main__':
    app.run(debug=True)