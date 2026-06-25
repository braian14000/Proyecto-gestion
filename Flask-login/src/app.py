from flask import Flask, render_template, request, redirect, url_for, flash, session
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

    try:
        if str(id) == '0' or str(id) == 'admin':
            return User(0, 'admin', 'admin', None, '')
        return ModelUser.get_by_id(db, id)
    except Exception:
        return None

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

        email = request.form.get('email') or request.form.get('usuario')
        password = request.form.get('password') or request.form.get('contraseña')


        if email == 'admin' and password == 'admin':
            admin_user = User(0, 'admin', 'admin', None, '')
            login_user(admin_user)
            return redirect(url_for('ver_eventos'))

        user = User(0, "", email, password)
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
            
            
            cursor.execute("SELECT id FROM `user` WHERE username = %s OR email = %s", (username, email))
            user_exists = cursor.fetchone()
            
            if user_exists:
                flash("El usuario o correo electrónico ya está registrado.")
                return render_template('auth/register.html')
            
           
            cursor.execute(
                "INSERT INTO `user` (username, password, telefono, email, dni) VALUES (%s, %s, %s, %s, %s)",
                (username, hashed_password, telefono, email, dni)
            )
            db.connection.commit()
            
            flash("¡Registro exitoso! Ya puedes iniciar sesión.", "success")
            return redirect(url_for('login'))
            
        except Exception as ex:
            flash("Ocurrió un error durante el registro.")
            return render_template('auth/register.html')
            
    return render_template('auth/register.html')

def get_events_from_db():
    try:
        cursor = db.connection.cursor()
        cursor.execute("SELECT id, titulo, fecha, descripcion, lugar FROM event ORDER BY fecha")
        rows = cursor.fetchall()
        events = []
        for r in rows:
            events.append({
                'id': r[0],
                'titulo': r[1],
                'fecha': r[2].strftime('%Y-%m-%d') if hasattr(r[2], 'strftime') else str(r[2]),
                'descripcion': r[3],
                'lugar': r[4]
            })
        return events
    except Exception:
        return []


def get_event_from_db(event_id):
    try:
        cursor = db.connection.cursor()
        cursor.execute("SELECT id, titulo, fecha, descripcion, lugar FROM event WHERE id = %s", (event_id,))
        r = cursor.fetchone()
        if not r:
            return None
        return {
            'id': r[0],
            'titulo': r[1],
            'fecha': r[2].strftime('%Y-%m-%d') if hasattr(r[2], 'strftime') else str(r[2]),
            'descripcion': r[3],
            'lugar': r[4]
        }
    except Exception:
        return None


def is_user_registered(db, evento_id, dni):
    try:
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT 1 FROM registrados WHERE evento_id = %s AND dni_usuario = %s LIMIT 1",
            (evento_id, dni)
        )
        return cursor.fetchone() is not None
    except Exception:
        return False


def get_registered_users(db, evento_id):
    try:
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, dni_usuario, nombre_usuario, created_at FROM registrados WHERE evento_id = %s ORDER BY created_at",
            (evento_id,)
        )
        rows = cursor.fetchall()
        return [
            {
                'id': r[0],
                'dni': r[1],
                'nombre': r[2],
                'created_at': r[3].strftime('%Y-%m-%d %H:%M') if hasattr(r[3], 'strftime') else str(r[3])
            }
            for r in rows
        ]
    except Exception:
        return []


@app.route('/evento/<int:evento_id>/usuarios')
@login_required
def ver_usuarios_evento(evento_id):
    if not current_user.is_authenticated or getattr(current_user, 'email', '') != 'admin':
        return redirect(url_for('login'))

    evento = get_event_from_db(evento_id)
    if evento is None:
        return "Evento no encontrado", 404

    usuarios = get_registered_users(db, evento_id)
    return render_template('usuarios_registrados.html', evento=evento, usuarios=usuarios)


@app.route('/evento/<int:evento_id>/usuarios/eliminar/<int:registro_id>', methods=['POST'])
@login_required
def eliminar_usuario_registrado(evento_id, registro_id):
    if not current_user.is_authenticated or getattr(current_user, 'email', '') != 'admin':
        return redirect(url_for('login'))

    try:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM registrados WHERE id = %s AND evento_id = %s", (registro_id, evento_id))
        db.connection.commit()
        flash("Usuario eliminado del evento.", "success")
    except Exception:
        flash("Ocurrió un error al eliminar al usuario.", "error")

    return redirect(url_for('ver_usuarios_evento', evento_id=evento_id))


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():

    
    if not current_user.is_authenticated or getattr(current_user, 'email', '') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        titulo = request.form.get('titulo')
        fecha = request.form.get('fecha')
        descripcion = request.form.get('descripcion')
        lugar = request.form.get('lugar')

        try:
            cursor = db.connection.cursor()
            cursor.execute(
                "INSERT INTO event (titulo, fecha, descripcion, lugar) VALUES (%s, %s, %s, %s)",
                (titulo, fecha, descripcion, lugar)
            )
            db.connection.commit()
        except Exception:
            pass

        return redirect(url_for('ver_eventos'))

    return render_template('admin.html')


@app.route('/eventos')
@login_required
def ver_eventos():
    eventos = get_events_from_db()
   
    if not eventos:
        eventos = [{
            'id': 1,
            'titulo': 'Concierto de Rock',
            'fecha': '2026-07-15',
            'descripcion': 'Una noche increíble con las mejores bandas locales.',
            'lugar': 'Estadio Principal'
        }]

    usuario_display = getattr(current_user, 'username', None) or getattr(current_user, 'email', '')
    return render_template('eventos.html', eventos=eventos, usuario=usuario_display)


@app.route('/evento/<int:evento_id>')
@login_required
def detalle_evento(evento_id):
    evento = get_event_from_db(evento_id)
    if evento is None:
        return "Evento no encontrado", 404
    user_dni = getattr(current_user, 'dni', None)
    registrado = False
    if user_dni:
        registrado = is_user_registered(db, evento_id, user_dni)
    return render_template('detalle.html', evento=evento, registrado=registrado)


@app.route('/evento/registrar/<int:evento_id>', methods=['POST'])
@login_required
def registrar_evento(evento_id):
    if request.method == 'POST':
        dni = getattr(current_user, 'dni', None)
        if not dni:
            flash('No se encontró tu DNI. Por favor, actualiza tu perfil.', 'error')
            return redirect(url_for('detalle_evento', evento_id=evento_id))

        try:
            cursor = db.connection.cursor()
            cursor.execute(
                "INSERT INTO registrados (evento_id, dni_usuario, nombre_usuario) VALUES (%s, %s, %s)",
                (evento_id, dni, current_user.username)
            )
            db.connection.commit()
            flash('Te has anotado correctamente al evento.', 'success')
        except Exception as ex:
            db.connection.rollback()
            if 'Duplicate entry' in str(ex):
                flash('Ya te has anotado en este evento.', 'error')
            else:
                flash('Ocurrió un error al anotarte. Intenta nuevamente.', 'error')

    return redirect(url_for('detalle_evento', evento_id=evento_id))


@app.route('/evento/editar/<int:evento_id>', methods=['GET', 'POST'])
@login_required
def editar_evento(evento_id):
    if not current_user.is_authenticated or getattr(current_user, 'email', '') != 'admin':
        return redirect(url_for('login'))
    
    evento = get_event_from_db(evento_id)
    if evento is None:
        return "Evento no encontrado", 404
    
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        fecha = request.form.get('fecha')
        descripcion = request.form.get('descripcion')
        lugar = request.form.get('lugar')

        try:
            cursor = db.connection.cursor()
            cursor.execute(
                "UPDATE event SET titulo = %s, fecha = %s, descripcion = %s, lugar = %s WHERE id = %s",
                (titulo, fecha, descripcion, lugar, evento_id)
            )
            db.connection.commit()
            flash("Evento actualizado exitosamente.", "success")
            return redirect(url_for('ver_eventos'))
        except Exception as ex:
            flash("Ocurrió un error al actualizar el evento.", "error")
            return render_template('editar_evento.html', evento=evento)

    return render_template('editar_evento.html', evento=evento)


@app.route('/evento/eliminar/<int:evento_id>', methods=['POST'])
@login_required
def eliminar_evento(evento_id):
    if not current_user.is_authenticated or getattr(current_user, 'email', '') != 'admin':
        return redirect(url_for('login'))
    
    try:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM event WHERE id = %s", (evento_id,))
        db.connection.commit()
        flash("Evento eliminado exitosamente.", "success")
    except Exception as ex:
        flash("Ocurrió un error al eliminar el evento.", "error")
    
    return redirect(url_for('ver_eventos'))

@app.route('/home')
@login_required
def home():
    if getattr(current_user, 'email', '') == 'admin' or getattr(current_user, 'username', '') == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('ver_eventos'))

@app.route('/logout')
@login_required
def logout():
    session.pop('_flashes', None)
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()

