from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash # Asegúrate de que esta importación esté arriba si no lo estaba

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
        user = User(0, request.form['username'], request.form['password'])
        logged_user = ModelUser.login(db, user)
        
        if logged_user != None:
            if logged_user.password:
                login_user(logged_user)
                return redirect(url_for('home'))
            else:
                flash("Contraseña incorrecta...")
                return render_template('auth/login.html')
        else:
            flash("Usuario no encontrado...")
            return render_template('auth/login.html')
    else:
        return render_template('auth/login.html')

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        fullname = request.form['fullname']
        
        # 1. Encriptamos la contraseña de forma segura para la BD
        hashed_password = generate_password_hash(password)
        
        try:
            cursor = db.connection.cursor()
            
            # 2. Validar si el usuario ya existe
            cursor.execute("SELECT id FROM user WHERE username = %s", (username,))
            user_exists = cursor.fetchone()
            
            if user_exists:
                flash("El nombre de usuario ya está registrado...")
                return render_template('auth/register.html')
            
            # 3. Insertar el nuevo usuario en la base de datos
            cursor.execute(
                "INSERT INTO user (username, password, fullname) VALUES (%s, %s, %s)",
                (username, hashed_password, fullname)
            )
            db.connection.commit()
            
            flash("¡Registro exitoso! Ya puedes iniciar sesión.")
            return redirect(url_for('login'))
            
        except Exception as ex:
            flash("Ocurrió un error durante el registro.")
            return render_template('auth/register.html')
            
    return render_template('auth/register.html')

if __name__ == '__main__':
    app.run()

