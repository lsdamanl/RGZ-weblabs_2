from flask import Flask, render_template, session

from registration import reg
from storage_room import room

import os

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'Секретно-секретный секрет')
app.config['DB_TYPE'] = os.getenv('DB_TYPE', 'postgres')


app.register_blueprint(reg)
app.register_blueprint(room)

@app.route("/")
def menu():
    return render_template('registration/menu.html', login=session.get('login'))

