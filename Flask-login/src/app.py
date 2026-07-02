from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

import qrcode
import os
import random
from datetime import datetime, timedelta
import re

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

# ============ FUNCIONES HELPER ============

def get_current_user_dni_username():
    """Obtiene DNI y username del usuario actual desde session o BD"""
    dni = getattr(current_user, 'dni', None)
    username = getattr(current_user, 'username', None)
    if not dni or not username:
        try:
            cursor = db.connection.cursor()
            cursor.execute("SELECT dni, username FROM `user` WHERE id = %s LIMIT 1", (current_user.id,))
            row = cursor.fetchone()
            if row:
                if not dni:
                    dni = row[0]
                if not username:
                    username = row[1]
        except Exception as ex:
            print(f"[ERROR] get_current_user_dni_username: {ex}")
    return dni, username

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

def get_user_registrations(db, dni_usuario):
    """Devuelve las inscripciones (registros) de un usuario junto con información del evento."""
    try:
        cursor = db.connection.cursor()
        cursor.execute(
            """
            SELECT r.id, r.evento_id, r.dni_usuario, r.nombre_usuario, r.qr_code, e.titulo, e.fecha, e.descripcion, e.lugar
            FROM registrados r
            LEFT JOIN event e ON e.id = r.evento_id
            WHERE r.dni_usuario = %s
            ORDER BY e.fecha
            """,
            (dni_usuario,)
        )
        rows = cursor.fetchall()
        regs = []
        for r in rows:
            regs.append({
                'registro_id': r[0],
                'evento_id': r[1],
                'dni': r[2],
                'nombre': r[3],
                'qr_code': r[4],
                'titulo': r[5],
                'fecha': r[6].strftime('%Y-%m-%d') if hasattr(r[6], 'strftime') else str(r[6]),
                'descripcion': r[7],
                'lugar': r[8]
            })
        return regs
    except Exception as ex:
        print(f"[ERROR] get_user_registrations: {ex}")
        return []

def generate_qr_code(evento_id, dni_usuario, nombre_usuario, registro_id):
    """Genera un código QR para el registro de un usuario en un evento"""
    try:
        qr_folder = os.path.join(app.static_folder, 'qr')
        if not os.path.exists(qr_folder):
            os.makedirs(qr_folder)
        
        qr_data = f"Evento:{evento_id}|DNI:{dni_usuario}|Nombre:{nombre_usuario}|Registro:{registro_id}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        filename = f"qr_evento_{evento_id}_user_{dni_usuario}_{registro_id}.png"
        filepath = os.path.join(qr_folder, filename)
        img.save(filepath)
        
        return f"/static/qr/{filename}"
    except Exception as ex:
        print(f"Error generando QR: {ex}")
        return None

# ============ MAIL CONFIG ============

from flask_mail import Mail, Message
from dotenv import load_dotenv

load_dotenv()
app.config.update({
    'MAIL_SERVER': os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
    'MAIL_PORT': int(os.getenv('MAIL_PORT', 587)),
    'MAIL_USE_TLS': os.getenv('MAIL_USE_TLS', 'True').lower() in ('true','1','yes'),
    'MAIL_USERNAME': os.getenv('MAIL_USER'),
    'MAIL_PASSWORD': os.getenv('MAIL_PASS'),
    'MAIL_DEFAULT_SENDER': os.getenv('MAIL_USER')
})
mail = Mail(app)

# ============ RUTAS PÚBLICAS ============

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

        telefono = telefono.strip()
        dni = dni.strip()
        if not dni.isdigit():
            flash("El DNI debe contener solo números.")
            return render_template('auth/register.html')
        if not re.fullmatch(r'[0-9+\-() ]+', telefono):
            flash("El Teléfono sólo puede contener números y los signos + - ( ) y espacios.")
            return render_template('auth/register.html')

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

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        if not identifier:
            flash('Ingrese correo o DNI.')
            return render_template('auth/forgot.html')

        try:
            cursor = db.connection.cursor()
            cursor.execute("SELECT id, email FROM `user` WHERE email = %s OR dni = %s LIMIT 1", (identifier, identifier))
            user = cursor.fetchone()
            if not user:
                flash('No se encontró una cuenta asociada.')
                return render_template('auth/forgot.html')

            user_id, user_email = user[0], user[1]
            code = f"{random.randint(100000, 999999)}"
            expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            session[f'pw_reset_{user_id}'] = {'code': code, 'expires': expires}
            session['reset_request_user_id'] = user_id
            session['reset_request_identifier'] = identifier
            session['reset_request_email'] = user_email

            if app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD') and user_email:
                try:
                    msg = Message('Código de recuperación', recipients=[user_email])
                    msg.body = f'Tu código de recuperación es: {code} (válido 15 minutos).'
                    mail.send(msg)
                    flash('Se envió un código al correo asociado.')
                except Exception as ex:
                    print(f'Error SMTP al enviar correo: {ex}')
                    flash(f'No se pudo enviar el correo. Código (modo prueba): {code}')
            else:
                flash(f'Código (modo prueba): {code}')

            return redirect(url_for('reset_password'))
        except Exception:
            flash('Ocurrió un error procesando la solicitud.')
            return render_template('auth/forgot.html')

    return render_template('auth/forgot.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        user_id = session.get('reset_request_user_id')
        identifier = session.get('reset_request_identifier')
        if not user_id or not identifier:
            flash('Primero solicita un código en la página de recuperación.')
            return redirect(url_for('forgot_password'))

        if not code:
            flash('Ingrese el código enviado a su correo.')
            return render_template('auth/reset_password.html')

        reset_data = session.get(f'pw_reset_{user_id}')
        if not reset_data:
            flash('No hay solicitud de recuperación activa para esta cuenta.')
            return redirect(url_for('forgot_password'))

        expires = datetime.fromisoformat(reset_data['expires'])
        if datetime.utcnow() > expires:
            session.pop(f'pw_reset_{user_id}', None)
            session.pop('reset_request_user_id', None)
            session.pop('reset_request_identifier', None)
            flash('El código expiró. Solicita uno nuevo.')
            return redirect(url_for('forgot_password'))

        if reset_data['code'] != code:
            flash('Código incorrecto.')
            return render_template('auth/reset_password.html')

        session['reset_user_id'] = user_id
        return redirect(url_for('new_password'))

    return render_template('auth/reset_password.html')

@app.route('/new-password', methods=['GET', 'POST'])
def new_password():
    user_id = session.get('reset_user_id')
    if not user_id:
        flash('No tienes permiso para cambiar la contraseña.')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        if not password or not confirm_password:
            flash('Completa ambos campos de contraseña.')
            return render_template('auth/new_password.html', reset_identifier=session.get('reset_identifier', ''))

        if password != confirm_password:
            flash('Las contraseñas no coinciden.')
            return render_template('auth/new_password.html', reset_identifier=session.get('reset_identifier', ''))

        hashed_password = generate_password_hash(password)
        try:
            cursor = db.connection.cursor()
            cursor.execute("UPDATE `user` SET password = %s WHERE id = %s", (hashed_password, user_id))
            db.connection.commit()
            session.pop('reset_user_id', None)
            flash('Contraseña cambiada correctamente. Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except Exception:
            flash('Ocurrió un error al guardar la nueva contraseña.')
            return render_template('auth/new_password.html', reset_identifier=session.get('reset_identifier', ''))

    return render_template('auth/new_password.html', reset_identifier=session.get('reset_identifier', ''))

# ============ RUTAS PROTEGIDAS - ADMIN ============

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

# ============ RUTAS PROTEGIDAS - USUARIOS ============

@app.route('/home')
@login_required
def home():
    if getattr(current_user, 'email', '') == 'admin' or getattr(current_user, 'username', '') == 'admin':
        return redirect(url_for('admin_dashboard'))

    usuario_display = getattr(current_user, 'username', None) or getattr(current_user, 'email', '')
    return render_template('menu.html', usuario=usuario_display)

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
    origin = request.args.get('origin', None)
    user_dni, _ = get_current_user_dni_username()
    registrado = False
    if user_dni:
        registrado = is_user_registered(db, evento_id, user_dni)
    back_url = url_for('mis_eventos') if origin == 'mis_eventos' else url_for('ver_eventos')
    return render_template('detalle.html', evento=evento, registrado=registrado, origin=origin, back_url=back_url)

@app.route('/evento/registrar/<int:evento_id>', methods=['POST'])
@login_required
def registrar_evento(evento_id):
    if request.method == 'POST':
        dni, username = get_current_user_dni_username()
        if not dni:
            flash('No se encontró tu DNI. Por favor, actualiza tu perfil.', 'error')
            return redirect(url_for('detalle_evento', evento_id=evento_id))

        try:
            cursor = db.connection.cursor()
            cursor.execute(
                "INSERT INTO registrados (evento_id, dni_usuario, nombre_usuario) VALUES (%s, %s, %s)",
                (evento_id, dni, username)
            )
            db.connection.commit()
            
            registro_id = cursor.lastrowid
            print(f"[DEBUG] Registro insertado id={registro_id} evento={evento_id} dni={dni}")
            
            qr_path = generate_qr_code(evento_id, dni, username, registro_id)
            
            if qr_path:
                cursor.execute(
                    "UPDATE registrados SET qr_code = %s WHERE id = %s",
                    (qr_path, registro_id)
                )
                db.connection.commit()
            
            flash('Te has anotado correctamente al evento. Tu código QR ha sido generado.', 'success')
        except Exception as ex:
            db.connection.rollback()
            print(f"[ERROR] Error registrando usuario en evento {evento_id}: {ex}")
            if 'Duplicate entry' in str(ex):
                flash('Ya te has anotado en este evento.', 'error')
            else:
                flash('Ocurrió un error al anotarte. Intenta nuevamente.', 'error')

    return redirect(url_for('detalle_evento', evento_id=evento_id))

@app.route('/mis-eventos')
@login_required
def mis_eventos():
    """Lista los eventos en los que el usuario actual está anotado."""
    dni, username = get_current_user_dni_username()
    print(f"[DEBUG] mis_eventos - current_user.id={getattr(current_user,'id',None)} email={getattr(current_user,'email',None)} dni={dni}")
    if not dni:
        flash('No se encontró tu DNI. Actualiza tu perfil para ver tus inscripciones.', 'error')
        return redirect(url_for('ver_eventos'))

    registros = get_user_registrations(db, dni)
    print(f"[DEBUG] mis_eventos - registros_count={len(registros) if registros is not None else 0}")
    print(f"[DEBUG] mis_eventos - registros={registros}")
    return render_template('mis_eventos.html', registros=registros)


@app.route('/mis-eventos/cancelar/<int:registro_id>', methods=['POST'])
@login_required
def cancelar_asistencia(registro_id):
    dni, _ = get_current_user_dni_username()
    if not dni:
        flash('No se encontró tu DNI. Actualiza tu perfil.', 'error')
        return redirect(url_for('mis_eventos'))

    try:
        cursor = db.connection.cursor()
        cursor.execute(
            "DELETE FROM registrados WHERE id = %s AND dni_usuario = %s",
            (registro_id, dni)
        )
        deleted = cursor.rowcount
        db.connection.commit()

        if deleted:
            flash('Tu asistencia fue cancelada correctamente.', 'success')
        else:
            flash('No se encontró tu registro para cancelar.', 'error')
    except Exception as ex:
        db.connection.rollback()
        print(f"[ERROR] cancelar_asistencia: {ex}")
        flash('Ocurrió un error al cancelar la asistencia.', 'error')

    return redirect(url_for('mis_eventos'))


@app.route('/registro/<int:registro_id>/qr')
@login_required
def mostrar_qr(registro_id):
    """Muestra la imagen QR asociada al registro (si existe)."""
    try:
        origin = request.args.get('origin', None)
        print(f"[DEBUG] mostrar_qr - solicitado registro_id={registro_id} por user id={getattr(current_user,'id',None)} origin={origin}")
        cursor = db.connection.cursor()
        cursor.execute("SELECT qr_code, dni_usuario FROM registrados WHERE id = %s LIMIT 1", (registro_id,))
        r = cursor.fetchone()
        if not r:
            print(f"[ERROR] mostrar_qr - registro {registro_id} no encontrado en DB")
            return "Registro no encontrado", 404
        qr_path, dni = r[0], r[1]
        print(f"[DEBUG] mostrar_qr - qr_path={qr_path} registro_dni={dni}")

        current_dni, _ = get_current_user_dni_username()
        
        if getattr(current_user, 'email', '') != 'admin' and str(dni) != str(current_dni):
            print(f"[ERROR] mostrar_qr - intento acceso no autorizado registro {registro_id} por user dni={current_dni}")
            return redirect(url_for('login'))

        if not qr_path:
            flash('No se encontró un código QR para este registro.', 'error')
            return redirect(url_for('mis_eventos'))

        back_url = url_for('mis_eventos') if origin == 'mis_eventos' else url_for('ver_eventos')
        return render_template('mostrar_qr.html', qr_path=qr_path, back_url=back_url)
    except Exception as ex:
        print(f"[ERROR] mostrar_qr - excepción: {ex}")
        return "Ocurrió un error", 500

@app.route('/debug-user')
@login_required
def debug_user():
    """Ruta temporal para depuración del usuario actual"""
    dni, username = get_current_user_dni_username()
    info = {
        'id': getattr(current_user, 'id', 'N/A'),
        'username': getattr(current_user, 'username', 'N/A'),
        'email': getattr(current_user, 'email', 'N/A'),
        'dni': dni,
        'telefono': getattr(current_user, 'telefono', 'N/A'),
    }
    
    registros_bd = []
    if dni:
        registros_bd = get_user_registrations(db, dni)
    
    return f"""
    <h2>Debug - Información del Usuario</h2>
    <pre>
    {info}
    </pre>
    <h2>Registros en BD (DNI={dni})</h2>
    <pre>
    {registros_bd}
    </pre>
    <hr />
    <a href="{url_for('debug_registros')}">Ver todos los registros</a> | 
    <a href="{url_for('mis_eventos')}">Volver a Mis Eventos</a>
    """

@app.route('/debug-registros')
@login_required
def debug_registros():
    """Muestra todos los registros en la tabla registrados"""
    try:
        cursor = db.connection.cursor()
        cursor.execute("SELECT id, evento_id, dni_usuario, nombre_usuario, qr_code, created_at FROM registrados ORDER BY created_at DESC LIMIT 20")
        rows = cursor.fetchall()
        
        html = "<h2>Últimos 20 Registros en BD</h2><table border='1' cellpadding='5'>"
        html += "<tr><th>ID</th><th>Evento</th><th>DNI</th><th>Nombre</th><th>QR</th><th>Fecha</th></tr>"
        for r in rows:
            html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td></tr>"
        html += "</table><hr />"
        html += f"<a href='{url_for('debug_user')}'>Ver info del usuario</a>"
        return html
    except Exception as ex:
        return f"Error: {ex}"

@app.route('/logout')
@login_required
def logout():
    session.pop('_flashes', None)
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()
