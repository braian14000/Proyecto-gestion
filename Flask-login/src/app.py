from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

from config import config
from models.ModeUsers import ModelUser
from models.entities.users import User

app = Flask(__name__)

app.config.from_object(config['development'])

db = MySQL(app)
csrf = CSRFProtect(app)
login_manager_app = LoginManager(app)

login_manager_app.login_view = 'login'

@login_manager_app.user_loader
def load_user(id):
    return ModelUser.get_by_id(db, id)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Pasamos: id=0, username="", email=formulario, password=formulario
        user = User(0, "", request.form['email'], request.form['password'])
        logged_user = ModelUser.login(db, user)
        
        if logged_user != None:
            if logged_user.password:
                login_user(logged_user)
                return redirect(url_for('home'))
            else:
                flash("La contraseña ingresada es incorrecta.")
                return render_template('auth/login.html')
        else:
            flash("El correo ingresado no existe.")
            return render_template('auth/login.html')
    else:
        return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        telefono = request.form['telefono']
        email = request.form['email']
        dni = request.form['dni']
        
        hashed_password = generate_password_hash(password)
        
        try:
            cursor = db.connection.cursor()
            
            # Validar si el correo o usuario ya existen
            cursor.execute("SELECT id FROM user WHERE username = %s OR email = %s", (username, email))
            user_exists = cursor.fetchone()
            
            if user_exists:
                flash("El usuario o correo electrónico ya está registrado.")
                return render_template('auth/register.html')
            
            # Insertar con las nuevas columnas
            cursor.execute(
                "INSERT INTO user (username, password, telefono, email, dni) VALUES (%s, %s, %s, %s, %s)",
                (username, hashed_password, telefono, email, dni)
            )
            db.connection.commit()
            
            flash("¡Registro exitoso! Ya puedes iniciar sesión.", "success")
            return redirect(url_for('login'))
            
        except Exception as ex:
            flash("Ocurrió un error durante el registro.")
            return render_template('auth/register.html')
            
    return render_template('auth/register.html')

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()

