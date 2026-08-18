from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_mysqldb import MySQL
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

import qrcode
import os
import random
from datetime import datetime, timedelta
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import config
from models.ModeUsers import ModelUser
from models.entities.users import User
from certificates import generar_certificado

app = Flask(__name__)
app.config.from_object(config['development'])

# Configuración de Gmail para soporte
GMAIL_USER = "gestioneventocontrasena12@gmail.com"
GMAIL_PASS = "jlrwsofpaxaksxoq" 
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", GMAIL_USER)

db = MySQL(app)


def ensure_event_table_has_capacity():
    try:
        with app.app_context():
            cursor = db.connection.cursor()
            cursor.execute("SHOW TABLES LIKE 'event'")
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS `event` (
                      `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
                      `titulo` VARCHAR(200) NOT NULL,
                      `fecha` DATE NOT NULL,
                      `descripcion` TEXT,
                      `lugar` VARCHAR(200),
                      `capacidad_maxima` INT NOT NULL DEFAULT 1,
                      `finalizado` TINYINT(1) NOT NULL DEFAULT 0,
                      `created_by` INT UNSIGNED NULL,
                      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """
                )
                db.connection.commit()
                print("[INFO] Se creó la tabla event con capacidad_maxima y finalizado.")
                return

            cursor.execute("SHOW COLUMNS FROM `event` LIKE 'capacidad_maxima'")
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE `event` ADD COLUMN `capacidad_maxima` INT NOT NULL DEFAULT 1")
                db.connection.commit()
                print("[INFO] Se agregó la columna capacidad_maxima a la tabla event.")

            cursor.execute("SHOW COLUMNS FROM `event` LIKE 'finalizado'")
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE `event` ADD COLUMN `finalizado` TINYINT(1) NOT NULL DEFAULT 0")
                db.connection.commit()
                print("[INFO] Se agregó la columna finalizado a la tabla event.")
    except Exception as ex:
        print(f"[WARN] No se pudo asegurar la estructura de la tabla event: {ex}")


ensure_event_table_has_capacity()
csrf = CSRFProtect(app)
login_manager_app = LoginManager(app)
login_manager_app.login_view = 'login'

@login_manager_app.user_loader
def load_user(id):
    try:
        if str(id) == '0' or str(id) == 'admin':
            # Crear usuario admin en memoria con rol 'admin' para que las plantillas lo detecten
            return User(0, 'admin', 'admin', None, '', '', 'admin')
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
        cursor.execute("SELECT id, titulo, fecha, descripcion, lugar, capacidad_maxima, finalizado FROM event ORDER BY fecha")
        rows = cursor.fetchall()
        events = []
        for r in rows:
            events.append({
                'id': r[0],
                'titulo': r[1],
                'fecha': r[2].strftime('%Y-%m-%d') if hasattr(r[2], 'strftime') else str(r[2]),
                'descripcion': r[3],
                'lugar': r[4],
                'capacidad_maxima': int(r[5]) if r[5] is not None else 0,
                'finalizado': bool(r[6])
            })
        return events
    except Exception:
        return []


def get_events_created_by_user(db_connection, user_id):
    try:
        cursor = db_connection.connection.cursor()
        cursor.execute(
            "SELECT id, titulo, fecha, descripcion, lugar, capacidad_maxima, finalizado FROM event WHERE created_by = %s ORDER BY fecha DESC, id DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        events = []
        for r in rows:
            evento_id = r[0]
            cursor2 = db_connection.connection.cursor()
            cursor2.execute("SELECT COUNT(*) FROM registrados WHERE evento_id = %s", (evento_id,))
            inscritos_count = cursor2.fetchone()[0]
            events.append({
                'id': evento_id,
                'titulo': r[1],
                'fecha': r[2].strftime('%Y-%m-%d') if hasattr(r[2], 'strftime') else str(r[2]),
                'descripcion': r[3],
                'lugar': r[4],
                'capacidad_maxima': int(r[5]) if r[5] is not None else 0,
                'finalizado': bool(r[6]),
                'inscritos_count': inscritos_count
            })
        return events
    except Exception:
        return []

def get_event_from_db(event_id):
    try:
        cursor = db.connection.cursor()
        cursor.execute(
            """
            SELECT e.id, e.titulo, e.fecha, e.descripcion, e.lugar, e.capacidad_maxima, e.finalizado, e.created_by,
                   (SELECT COUNT(*) FROM registrados r WHERE r.evento_id = e.id) AS inscritos_count
            FROM event e
            WHERE e.id = %s
            """,
            (event_id,)
        )
        r = cursor.fetchone()
        if not r:
            return None
        return {
            'id': r[0],
            'titulo': r[1],
            'fecha': r[2].strftime('%Y-%m-%d') if hasattr(r[2], 'strftime') else str(r[2]),
            'descripcion': r[3],
            'lugar': r[4],
            'capacidad_maxima': int(r[5]) if r[5] is not None else 0,
            'finalizado': bool(r[6]),
            'created_by': r[7],
            'inscritos_count': int(r[8]) if r[8] is not None else 0
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
            "SELECT id, dni_usuario, nombre_usuario, created_at, asistido FROM registrados WHERE evento_id = %s ORDER BY created_at",
            (evento_id,)
        )
        rows = cursor.fetchall()
        return [    
            {
                'id': r[0],
                'dni': r[1],
                'nombre': r[2],
                'created_at': r[3].strftime('%Y-%m-%d %H:%M') if hasattr(r[3], 'strftime') else str(r[3]),
                'asistido': bool(r[4])
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
            SELECT r.id, r.evento_id, r.dni_usuario, r.nombre_usuario, r.qr_code, r.asistido, e.titulo, e.fecha, e.descripcion, e.lugar
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
                'asistido': bool(r[5]),
                'titulo': r[6],
                'fecha': r[7].strftime('%Y-%m-%d') if hasattr(r[7], 'strftime') else str(r[7]),
                'descripcion': r[8],
                'lugar': r[9]
            })
        return regs
    except Exception as ex:
        print(f"[ERROR] get_user_registrations: {ex}")
        return []


def delete_finished_events_and_qr():
    """Elimina eventos ya finalizados, sus registros y sus QR asociados."""
    try:
        cursor = db.connection.cursor()
        cursor.execute(
            """
            SELECT id
            FROM event
            WHERE finalizado = 1 OR fecha < CURDATE()
            ORDER BY id
            """
        )
        events = cursor.fetchall()

        if not events:
            return {'deleted_events': 0, 'deleted_registrations': 0, 'deleted_qr_files': 0}

        event_ids = [row[0] for row in events]
        qr_paths_to_remove = []
        for event_id in event_ids:
            cursor2 = db.connection.cursor()
            cursor2.execute("SELECT qr_code FROM registrados WHERE evento_id = %s", (event_id,))
            for (qr_code,) in cursor2.fetchall():
                if qr_code:
                    qr_paths_to_remove.append(qr_code)

        seen_qr_paths = []
        for qr_path in qr_paths_to_remove:
            if qr_path in seen_qr_paths:
                continue
            seen_qr_paths.append(qr_path)
            try:
                normalized_path = qr_path.replace('/static/qr/', '').replace('static/qr/', '')
                filename = os.path.basename(normalized_path)
                if not filename:
                    continue
                full_path = os.path.join(app.static_folder, 'qr', filename)
                if os.path.exists(full_path):
                    os.remove(full_path)
            except Exception as ex:
                print(f"[WARN] No se pudo eliminar el QR {qr_path}: {ex}")

        placeholders = ', '.join(['%s'] * len(event_ids))
        cursor.execute(f"DELETE FROM registrados WHERE evento_id IN ({placeholders})", tuple(event_ids))
        cursor.execute(f"DELETE FROM event WHERE id IN ({placeholders})", tuple(event_ids))
        db.connection.commit()

        return {
            'deleted_events': len(event_ids),
            'deleted_registrations': cursor.rowcount if hasattr(cursor, 'rowcount') else len(event_ids),
            'deleted_qr_files': len(seen_qr_paths)
        }
    except Exception as ex:
        db.connection.rollback()
        print(f"[ERROR] delete_finished_events_and_qr: {ex}")
        raise


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

# Usar GMAIL_USER y GMAIL_PASS definidos arriba (no cargar .env)
app.config.update({
    'MAIL_SERVER': 'smtp.gmail.com',
    'MAIL_PORT': 587,
    'MAIL_USE_TLS': True,
    'MAIL_USE_SSL': False,
    'MAIL_USERNAME': GMAIL_USER,
    'MAIL_PASSWORD': GMAIL_PASS,
    'MAIL_DEFAULT_SENDER': GMAIL_USER
})
mail = Mail(app)
print(f"[INFO] Mail configurado con usuario: {GMAIL_USER}")

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

    remembered_email = request.cookies.get('remembered_user', '')

    if request.method == 'POST':
        email = request.form.get('email') or request.form.get('usuario')
        password = request.form.get('password') or request.form.get('contraseña')
        remember_me = request.form.get('remember_me') == '1'

        if email == 'admin' and password == 'admin':
            admin_user = User(0, 'admin', 'admin', None, '')
            login_user(admin_user)
            response = redirect(url_for('home'))
            if remember_me:
                response.set_cookie('remembered_user', email, max_age=60*60*24*30, httponly=True, samesite='Lax')
            else:
                response.delete_cookie('remembered_user')
            return response

        user = User(0, "", email, password)
        logged_user = ModelUser.login(db, user)

        if logged_user != None:
            if logged_user.password:
                login_user(logged_user)
                response = redirect(url_for('home'))
                if remember_me:
                    response.set_cookie('remembered_user', email, max_age=60*60*24*30, httponly=True, samesite='Lax')
                else:
                    response.delete_cookie('remembered_user')
                return response
            else:
                flash("La contraseña ingresada es incorrecta.")
                return render_template('auth/login.html', remembered_email=remembered_email)
        else:
            flash("El correo ingresado no existe.")
            return render_template('auth/login.html', remembered_email=remembered_email)
    else:
        return render_template('auth/login.html', remembered_email=remembered_email)

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
        if not dni.isdigit() or len(dni) > 8:
            flash("El DNI debe contener solo números y como máximo 8 dígitos.")
            return render_template('auth/register.html')
        if len(telefono) > 10 or not re.fullmatch(r'[0-9+\-() ]+', telefono):
            flash("El Teléfono sólo puede contener números y los signos + - ( ) y espacios, con un máximo de 10 caracteres.")
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
        dni = request.form.get('dni', '').strip()
        if not dni:
            flash('Ingrese el DNI asociado.')
            return render_template('auth/forgot.html')

        if not dni.isdigit():
            flash('El DNI debe contener solo números.')
            return render_template('auth/forgot.html')

        try:
            cursor = db.connection.cursor()
            cursor.execute("SELECT id, email FROM `user` WHERE dni = %s LIMIT 1", (dni,))
            user = cursor.fetchone()
            if not user:
                flash('No se encontró una cuenta asociada al DNI ingresado.')
                return render_template('auth/forgot.html')

            user_id, user_email = user[0], user[1]
            code = f"{random.randint(100000, 999999)}"
            expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            session[f'pw_reset_{user_id}'] = {'code': code, 'expires': expires}
            session['reset_request_user_id'] = user_id
            session['reset_request_identifier'] = dni
            session['reset_request_email'] = user_email

            if user_email:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = GMAIL_USER
                    msg['To'] = user_email
                    msg['Subject'] = 'Código de recuperación'
                    msg.attach(MIMEText(f'Tu código de recuperación es: {code} (válido 15 minutos).', 'plain'))

                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(GMAIL_USER, GMAIL_PASS)
                    server.send_message(msg)
                    server.quit()

                    flash('Se envió un nuevo código al correo asociado.')
                except Exception as ex:
                    print(f'Error SMTP al enviar correo: {ex}')
                    flash('No se pudo enviar el correo. Revisa la configuración SMTP y vuelve a intentarlo.')
            else:
                flash('No se encontró un correo electrónico válido asociado a ese DNI.')

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
    if (not current_user.is_authenticated) or (getattr(current_user, 'rol', '') not in ('admin', 'organizador')):
        return redirect(url_for('login'))

    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        fecha = request.form.get('fecha', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        lugar = request.form.get('lugar', '').strip()
        capacidad_maxima = request.form.get('capacidad_maxima', '').strip()

        try:
            capacidad = int(capacidad_maxima)
            if not titulo or not fecha or not descripcion or not lugar or capacidad <= 0:
                raise ValueError
        except ValueError:
            flash('La capacidad máxima es obligatoria y debe ser un número mayor a 0.', 'error')
            return render_template('admin.html')

        try:
            cursor = db.connection.cursor()
            user_id = getattr(current_user, 'id', None)
            if user_id in (None, 0):
                cursor.execute(
                    "INSERT INTO event (titulo, fecha, descripcion, lugar, capacidad_maxima) VALUES (%s, %s, %s, %s, %s)",
                    (titulo, fecha, descripcion, lugar, capacidad)
                )
            else:
                try:
                    cursor.execute(
                        "INSERT INTO event (titulo, fecha, descripcion, lugar, capacidad_maxima, created_by) VALUES (%s, %s, %s, %s, %s, %s)",
                        (titulo, fecha, descripcion, lugar, capacidad, user_id)
                    )
                except Exception:
                    cursor.execute(
                        "INSERT INTO event (titulo, fecha, descripcion, lugar, capacidad_maxima) VALUES (%s, %s, %s, %s, %s)",
                        (titulo, fecha, descripcion, lugar, capacidad)
                    )
            db.connection.commit()
        except Exception as ex:
            flash(f'No se pudo crear el evento: {ex}', 'error')
            return render_template('admin.html')

        return redirect(url_for('ver_eventos'))

    return render_template('admin.html')


@app.route('/crear-evento-organizador', methods=['GET', 'POST'])
@login_required
def crear_evento_organizador():
    if (not current_user.is_authenticated) or (getattr(current_user, 'rol', '') not in ('admin', 'organizador')):
        return redirect(url_for('login'))

    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        fecha = request.form.get('fecha', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        lugar = request.form.get('lugar', '').strip()
        capacidad_maxima = request.form.get('capacidad_maxima', '').strip()

        try:
            capacidad = int(capacidad_maxima)
            if not titulo or not fecha or not descripcion or not lugar or capacidad <= 0:
                raise ValueError
        except ValueError:
            flash('Completá todos los campos y la capacidad máxima debe ser un número mayor a 0.', 'error')
            return render_template('crear_evento_organizador.html')

        try:
            cursor = db.connection.cursor()
            user_id = getattr(current_user, 'id', None)
            if user_id in (None, 0):
                cursor.execute(
                    "INSERT INTO event (titulo, fecha, descripcion, lugar, capacidad_maxima) VALUES (%s, %s, %s, %s, %s)",
                    (titulo, fecha, descripcion, lugar, capacidad)
                )
            else:
                try:
                    cursor.execute(
                        "INSERT INTO event (titulo, fecha, descripcion, lugar, capacidad_maxima, created_by) VALUES (%s, %s, %s, %s, %s, %s)",
                        (titulo, fecha, descripcion, lugar, capacidad, user_id)
                    )
                except Exception:
                    cursor.execute(
                        "INSERT INTO event (titulo, fecha, descripcion, lugar, capacidad_maxima) VALUES (%s, %s, %s, %s, %s)",
                        (titulo, fecha, descripcion, lugar, capacidad)
                    )
            db.connection.commit()
            flash('Evento creado correctamente.', 'success')
            return redirect(url_for('eventos_organizador'))
        except Exception as ex:
            flash(f'No se pudo crear el evento: {ex}', 'error')
            return render_template('crear_evento_organizador.html')

    return render_template('crear_evento_organizador.html')

@app.route('/gestionar-organizadores', methods=['GET', 'POST'])
@login_required
def gestionar_organizadores():
    if not current_user.is_authenticated or getattr(current_user, 'email', '') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        nuevo_rol = request.form.get('rol')

        if user_id and nuevo_rol in ('organizador', 'estudiante'):
            try:
                ModelUser.update_rol(db, user_id, nuevo_rol)
                flash('Rol actualizado correctamente.', 'success')
            except Exception as ex:
                flash(f'No se pudo actualizar el rol: {ex}', 'error')
        else:
            flash('No se recibió un cambio de rol válido.', 'error')

        return redirect(url_for('gestionar_organizadores'))

    usuarios = ModelUser.get_all_users(db)
    return render_template('admin_organizadores.html', usuarios=usuarios)

@app.route('/admin/borrar-historial', methods=['POST'])
@login_required
def borrar_historial_admin():
    if not current_user.is_authenticated or getattr(current_user, 'rol', '') != 'admin':
        return redirect(url_for('login'))

    try:
        result = delete_finished_events_and_qr()
        flash(
            f"Historial limpiado. Se eliminaron {result['deleted_events']} eventos, {result['deleted_registrations']} inscripciones y {result['deleted_qr_files']} QR.",
            'success'
        )
    except Exception as ex:
        flash(f'No se pudo borrar el historial: {ex}', 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/evento/<int:evento_id>/usuarios')
@login_required
def ver_usuarios_evento(evento_id):
    if not current_user.is_authenticated or getattr(current_user, 'rol', '') not in ('admin', 'organizador'):
        return redirect(url_for('login'))

    evento = get_event_from_db(evento_id)
    if evento is None:
        return "Evento no encontrado", 404

    if evento.get('finalizado'):
        flash('Este evento ya finalizó, por lo que no se pueden hacer cambios sobre sus inscripciones.', 'warning')
        if getattr(current_user, 'rol', '') == 'admin':
            return redirect(url_for('ver_eventos'))
        return redirect(url_for('eventos_organizador'))

    usuarios = get_registered_users(db, evento_id)
    return render_template('usuarios_registrados.html', evento=evento, usuarios=usuarios)

@app.route('/evento/<int:evento_id>/usuarios/eliminar/<int:registro_id>', methods=['POST'])
@login_required
def eliminar_usuario_registrado(evento_id, registro_id):
    if not current_user.is_authenticated or getattr(current_user, 'rol', '') not in ('admin', 'organizador'):
        return redirect(url_for('login'))

    evento = get_event_from_db(evento_id)
    if evento is None:
        return "Evento no encontrado", 404
    if evento.get('finalizado'):
        flash('Este evento ya finalizó y no se pueden eliminar usuarios.', 'error')
        return redirect(url_for('ver_usuarios_evento', evento_id=evento_id))

    try:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM registrados WHERE id = %s AND evento_id = %s", (registro_id, evento_id))
        db.connection.commit()
        flash("Usuario eliminado del evento.", "success")
    except Exception:
        flash("Ocurrió un error al eliminar al usuario.", "error")

    return redirect(url_for('ver_usuarios_evento', evento_id=evento_id))

@app.route('/evento/<int:evento_id>/editar-ubicacion', methods=['GET', 'POST'])
@login_required
def editar_ubicacion_evento(evento_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    evento = get_event_from_db(evento_id)
    if evento is None:
        return "Evento no encontrado", 404

    es_admin = getattr(current_user, 'rol', '') == 'admin' or getattr(current_user, 'email', '') == 'admin'
    es_organizador = getattr(current_user, 'rol', '') == 'organizador'
    es_propietario = getattr(evento, 'get', lambda *args, **kwargs: None)('created_by') in (None, getattr(current_user, 'id', None))

    if not es_admin and not (es_organizador and es_propietario):
        flash('No tenés permiso para cambiar la ubicación de este evento.', 'error')
        return redirect(url_for('detalle_evento', evento_id=evento_id))

    if evento.get('finalizado'):
        flash('Este evento ya finalizó y no se puede modificar.', 'error')
        return redirect(url_for('detalle_evento', evento_id=evento_id))

    if request.method == 'POST':
        nuevo_lugar = request.form.get('lugar', '').strip()
        if not nuevo_lugar:
            flash('La nueva ubicación es obligatoria.', 'error')
            return render_template('editar_ubicacion.html', evento=evento)

        try:
            cursor = db.connection.cursor()
            cursor.execute("UPDATE event SET lugar = %s WHERE id = %s", (nuevo_lugar, evento_id))
            db.connection.commit()
            flash('La ubicación del evento se actualizó correctamente.', 'success')
            return redirect(url_for('detalle_evento', evento_id=evento_id))
        except Exception as ex:
            flash(f'No se pudo actualizar la ubicación: {ex}', 'error')
            return render_template('editar_ubicacion.html', evento=evento)

    return render_template('editar_ubicacion.html', evento=evento)

@app.route('/evento/editar/<int:evento_id>', methods=['GET', 'POST'])
@login_required
def editar_evento(evento_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    evento = get_event_from_db(evento_id)
    if evento is None:
        return "Evento no encontrado", 404

    es_admin = getattr(current_user, 'rol', '') == 'admin' or getattr(current_user, 'email', '') == 'admin'
    es_propietario = getattr(evento, 'get', lambda *args, **kwargs: None)('created_by') in (None, getattr(current_user, 'id', None))

    if not es_admin and not es_propietario:
        flash("No tenés permiso para editar este evento.", "error")
        return redirect(url_for('eventos_organizador'))

    if evento.get('finalizado'):
        flash('Este evento ya finalizó y no se puede editar.', 'error')
        return redirect(url_for('ver_eventos'))

    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        fecha = request.form.get('fecha', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        lugar = request.form.get('lugar', '').strip()
        capacidad_maxima = request.form.get('capacidad_maxima', '').strip()

        try:
            capacidad = int(capacidad_maxima)
            if not titulo or not fecha or not descripcion or not lugar or capacidad <= 0:
                raise ValueError
        except ValueError:
            flash('La capacidad máxima es obligatoria y debe ser un número mayor a 0.', 'error')
            return render_template('editar_evento.html', evento=evento)

        try:
            cursor = db.connection.cursor()
            cursor.execute(
                "UPDATE event SET titulo = %s, fecha = %s, descripcion = %s, lugar = %s, capacidad_maxima = %s WHERE id = %s",
                (titulo, fecha, descripcion, lugar, capacidad, evento_id)
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
    if not current_user.is_authenticated or getattr(current_user, 'rol', '') not in ('admin', 'organizador'):
        return redirect(url_for('login'))

    evento = get_event_from_db(evento_id)
    if evento is None:
        return "Evento no encontrado", 404

    if evento.get('finalizado'):
        flash('No se puede eliminar un evento finalizado.', 'error')
        if getattr(current_user, 'rol', '') == 'admin':
            return redirect(url_for('ver_eventos'))
        return redirect(url_for('eventos_organizador'))

    es_admin = getattr(current_user, 'rol', '') == 'admin' or getattr(current_user, 'email', '') == 'admin'
    es_propietario = getattr(evento, 'get', lambda *args, **kwargs: None)('created_by') in (None, getattr(current_user, 'id', None))

    if not es_admin and not es_propietario:
        flash("No tenés permiso para eliminar este evento.", "error")
        return redirect(url_for('eventos_organizador'))
    
    try:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM event WHERE id = %s", (evento_id,))
        db.connection.commit()
        flash("Evento eliminado exitosamente.", "success")
    except Exception as ex:
        flash("Ocurrió un error al eliminar el evento.", "error")

    if es_admin:
        return redirect(url_for('ver_eventos'))
    return redirect(url_for('eventos_organizador'))

# ============ RUTAS PROTEGIDAS - USUARIOS ============

@app.route('/home')
@login_required
def home():
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
            'lugar': 'Estadio Principal',
            'capacidad_maxima': 200
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
    cupos_disponibles = max(evento.get('capacidad_maxima', 0) - evento.get('inscritos_count', 0), 0)
    back_url = url_for('mis_eventos') if origin == 'mis_eventos' else url_for('ver_eventos')
    if evento.get('finalizado'):
        flash('Este evento ya finalizó y quedó cerrado para nuevas inscripciones o validaciones.', 'warning')
    return render_template(
        'detalle.html',
        evento=evento,
        registrado=registrado,
        origin=origin,
        back_url=back_url,
        cupos_disponibles=cupos_disponibles
    )

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
            cursor.execute("SELECT capacidad_maxima, finalizado FROM event WHERE id = %s LIMIT 1", (evento_id,))
            evento = cursor.fetchone()
            if not evento:
                flash('Evento no encontrado.', 'error')
                return redirect(url_for('ver_eventos'))

            capacidad_maxima = int(evento[0]) if evento[0] is not None else 0
            finalizado = bool(evento[1])
            if finalizado:
                flash('Este evento ya finalizó y no acepta más inscripciones.', 'error')
                return redirect(url_for('detalle_evento', evento_id=evento_id))

            cursor.execute("SELECT COUNT(*) FROM registrados WHERE evento_id = %s", (evento_id,))
            inscritos_actuales = int(cursor.fetchone()[0])

            if capacidad_maxima <= 0:
                flash('Este evento no tiene una capacidad máxima válida.', 'error')
                return redirect(url_for('detalle_evento', evento_id=evento_id))

            if inscritos_actuales >= capacidad_maxima:
                flash('El evento ya alcanzó su capacidad máxima.', 'error')
                return redirect(url_for('detalle_evento', evento_id=evento_id))

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

@app.route('/eventos-organizador')
@login_required
def eventos_organizador():
    """Muestra los eventos creados por el organizador autenticado."""
    if not current_user.is_authenticated or getattr(current_user, 'rol', '') not in ('admin', 'organizador'):
        return redirect(url_for('login'))

    user_id = getattr(current_user, 'id', None)
    eventos = []
    if user_id not in (None, 0):
        eventos = get_events_created_by_user(db, user_id)

    return render_template('eventos_organizador.html', eventos=eventos)

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


@app.route('/evento/<int:evento_id>/finalizar', methods=['POST'])
@login_required
def finalizar_evento(evento_id):
    if not current_user.is_authenticated or getattr(current_user, 'rol', '') not in ('admin', 'organizador'):
        return redirect(url_for('login'))

    evento = get_event_from_db(evento_id)
    if evento is None:
        return "Evento no encontrado", 404

    es_admin = getattr(current_user, 'rol', '') == 'admin' or getattr(current_user, 'email', '') == 'admin'
    es_propietario = getattr(evento, 'get', lambda *args, **kwargs: None)('created_by') in (None, getattr(current_user, 'id', None))
    if not es_admin and not es_propietario:
        flash('No tenés permiso para finalizar este evento.', 'error')
        return redirect(url_for('eventos_organizador'))

    if evento.get('finalizado'):
        flash('Este evento ya está finalizado.', 'warning')
        return redirect(url_for('ver_eventos'))

    try:
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT dni_usuario, nombre_usuario FROM registrados WHERE evento_id = %s AND asistido = 1 ORDER BY created_at",
            (evento_id,)
        )
        registrados = cursor.fetchall()

        if not registrados:
            flash('El evento fue finalizado, pero no hay usuarios validados para recibir certificados.', 'warning')
        else:
            for dni_usuario, nombre_usuario in registrados:
                try:
                    cursor2 = db.connection.cursor()
                    cursor2.execute("SELECT email FROM `user` WHERE dni = %s LIMIT 1", (dni_usuario,))
                    usuario = cursor2.fetchone()
                    email_destino = usuario[0] if usuario else None
                    if not email_destino:
                        continue

                    nombre_partes = (nombre_usuario or '').split()
                    nombre = nombre_partes[0] if nombre_partes else ''
                    apellido = ' '.join(nombre_partes[1:]) if len(nombre_partes) > 1 else ''
                    cert_path = generar_certificado(nombre, apellido, dni_usuario, evento['titulo'])

                    msg = Message(subject=f'Certificado de asistencia - {evento["titulo"]}', recipients=[email_destino])
                    msg.body = (
                        f"Hola {nombre_usuario},\n\n"
                        f"Adjuntamos tu certificado de asistencia al evento '{evento['titulo']}'.\n\n"
                        "Saludos,\nEquipo de Gestión de Eventos"
                    )
                    with open(cert_path, 'rb') as file:
                        msg.attach(os.path.basename(cert_path), 'image/png', file.read())
                    mail.send(msg)
                except Exception as ex:
                    print(f"[ERROR] finalizando evento {evento_id}, usuario {dni_usuario}: {ex}")

            flash('Evento finalizado correctamente. Los certificados fueron enviados solo a los usuarios validados.', 'success')

        cursor.execute("UPDATE event SET finalizado = 1 WHERE id = %s", (evento_id,))
        db.connection.commit()
    except Exception as ex:
        db.connection.rollback()
        flash(f'No se pudo finalizar el evento: {ex}', 'error')

    if es_admin:
        return redirect(url_for('ver_eventos'))
    return redirect(url_for('eventos_organizador'))


@app.route('/evento/<int:evento_id>/validar-qr')
@login_required
def validar_qr_evento(evento_id):
    """Muestra la vista para validar entrada de un evento mediante QR o DNI."""
    evento = get_event_from_db(evento_id)
    if evento is None:
        return "Evento no encontrado", 404
    if evento.get('finalizado'):
        flash('Este evento ya finalizó y no se puede validar más.', 'error')
        return redirect(url_for('eventos_organizador'))
    return render_template('validar_qr.html', evento=evento, evento_id=evento_id)


@app.route('/api/validar-qr-entrada', methods=['POST'])
@login_required
def validar_qr_entrada():
    """Valida si un usuario está registrado en un evento usando QR o DNI.
    Solo marca asistido y devuelve el email, sin generar certificado aún.
    """
    data = request.get_json(silent=True) or {}
    evento_id = data.get('evento_id')
    qr_data = data.get('qr_data')
    dni = data.get('dni')

    if not evento_id:
        return jsonify({'success': False, 'message': 'No se indicó el evento.'}), 400

    try:
        cursor = db.connection.cursor()
        if qr_data:
            import re
            match = re.search(r'\|DNI:(.+?)\|', str(qr_data))
            dni = match.group(1).strip() if match else None

        if not dni:
            return jsonify({'success': False, 'message': 'No se pudo leer el DNI del QR o no se ingresó el DNI.'}), 400

        cursor.execute("SELECT finalizado FROM event WHERE id = %s LIMIT 1", (evento_id,))
        evento_row = cursor.fetchone()
        if evento_row and bool(evento_row[0]):
            return jsonify({'success': False, 'message': 'Este evento ya finalizó y no acepta más validaciones.'}), 403

        cursor.execute(
            "SELECT 1 FROM registrados WHERE evento_id = %s AND dni_usuario = %s LIMIT 1",
            (evento_id, dni)
        )
        existe = cursor.fetchone() is not None

        if existe:
            cursor.execute(
                "UPDATE registrados SET asistido = 1 WHERE evento_id = %s AND dni_usuario = %s",
                (evento_id, dni)
            )
            db.connection.commit()

            # Obtener email actual del usuario
            try:
                cursor.execute("SELECT email FROM `user` WHERE dni = %s LIMIT 1", (dni,))
                user_row = cursor.fetchone()
                user_email = user_row[0] if user_row else None
            except Exception:
                user_email = None

            print(f"[INFO] Usuario {dni} marcado como asistido en evento {evento_id}. Email: {user_email}")
            
            return jsonify({
                'success': True,
                'message': f'✓ Usuario validado. Email: {user_email or "(no registrado)"}',
                'current_email': user_email,
                'evento_id': evento_id,
                'dni': dni
            })

        return jsonify({'success': False, 'message': 'No se encontró un registro para este usuario en el evento.'})
    except Exception as ex:
        print(f"[ERROR] validar_qr_entrada: {ex}")
        return jsonify({'success': False, 'message': 'Ocurrió un error al validar el QR.'}), 500


@app.route('/api/enviar-certificados-lote', methods=['POST'])
@login_required
def enviar_certificados_lote():
    """Envía certificados a múltiples usuarios de una vez."""
    data = request.get_json(silent=True) or {}
    evento_id = data.get('evento_id')
    usuarios = data.get('usuarios', [])  # Lista de {dni, email}

    if not evento_id or not usuarios:
        return jsonify({'success': False, 'message': 'Faltan datos requeridos.'}), 400

    results = []
    cursor = db.connection.cursor()

    try:
        # Obtener título del evento
        cursor.execute("SELECT titulo FROM event WHERE id = %s LIMIT 1", (evento_id,))
        evt_row = cursor.fetchone()
        evento_titulo = evt_row[0] if evt_row else f'Evento {evento_id}'
    except Exception:
        evento_titulo = f'Evento {evento_id}'

    for user_data in usuarios:
        dni = user_data.get('dni')
        email_destino = user_data.get('email')

        if not dni or not email_destino:
            results.append({'dni': dni, 'success': False, 'message': 'Datos incompletos'})
            continue

        try:
            cursor.execute(
                "SELECT nombre_usuario FROM registrados WHERE evento_id = %s AND dni_usuario = %s AND asistido = 1 LIMIT 1",
                (evento_id, dni)
            )
            nombre_row = cursor.fetchone()
            if not nombre_row:
                results.append({'dni': dni, 'success': False, 'message': 'Usuario no validado'})
                continue
            nombre_usuario = nombre_row[0] if nombre_row else ''

            # Separar nombre y apellido
            nombre_partes = nombre_usuario.split()
            nombre = nombre_partes[0] if len(nombre_partes) > 0 else ''
            apellido = ' '.join(nombre_partes[1:]) if len(nombre_partes) > 1 else ''

            # Generar certificado
            salida_cert = generar_certificado(nombre, apellido, dni, evento_titulo)

            # Enviar por email
            try:
                subj = f"Certificado de asistencia - {evento_titulo}"
                body = f"Hola {nombre_usuario},\n\nAdjuntamos tu certificado de asistencia al evento '{evento_titulo}'.\n\nSaludos,\nEquipo de Gestión de Eventos"
                msg = Message(subject=subj, recipients=[email_destino])
                msg.body = body
                with open(salida_cert, 'rb') as fp:
                    cert_data = fp.read()
                    msg.attach(os.path.basename(salida_cert), 'image/png', cert_data)
                
                print(f"[INFO] Enviando certificado a {email_destino} (DNI: {dni})")
                mail.send(msg)
                print(f"[INFO] Email enviado a {email_destino}")
                results.append({'dni': dni, 'success': True, 'message': f'Enviado a {email_destino}'})
            except Exception as mail_ex:
                print(f"[ERROR] No se pudo enviar email a {email_destino}: {mail_ex}")
                results.append({'dni': dni, 'success': False, 'message': f'Error: {str(mail_ex)[:50]}'})
        except Exception as ex:
            print(f"[ERROR] Error procesando DNI {dni}: {ex}")
            results.append({'dni': dni, 'success': False, 'message': str(ex)[:50]})

    success_count = sum(1 for r in results if r['success'])
    return jsonify({
        'success': True,
        'message': f'Certificados enviados: {success_count}/{len(usuarios)}',
        'results': results
    })


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
            "SELECT e.finalizado, r.evento_id FROM registrados r JOIN event e ON e.id = r.evento_id WHERE r.id = %s AND r.dni_usuario = %s LIMIT 1",
            (registro_id, dni)
        )
        registro = cursor.fetchone()
        if not registro:
            flash('No se encontró tu registro para cancelar.', 'error')
            return redirect(url_for('mis_eventos'))

        finalizado, evento_id = bool(registro[0]), registro[1]
        if finalizado:
            flash('Este evento ya finalizó y no se puede cancelar la asistencia.', 'error')
            return redirect(url_for('mis_eventos'))

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
        cursor.execute(
            "SELECT r.qr_code, r.dni_usuario, e.finalizado, r.evento_id FROM registrados r JOIN event e ON e.id = r.evento_id WHERE r.id = %s LIMIT 1",
            (registro_id,)
        )
        r = cursor.fetchone()
        if not r:
            print(f"[ERROR] mostrar_qr - registro {registro_id} no encontrado en DB")
            return "Registro no encontrado", 404
        qr_path, dni, evento_finalizado, evento_id = r[0], r[1], bool(r[2]), r[3]
        print(f"[DEBUG] mostrar_qr - qr_path={qr_path} registro_dni={dni} evento_finalizado={evento_finalizado}")

        current_dni, _ = get_current_user_dni_username()
        
        if getattr(current_user, 'email', '') != 'admin' and str(dni) != str(current_dni):
            print(f"[ERROR] mostrar_qr - intento acceso no autorizado registro {registro_id} por user dni={current_dni}")
            return redirect(url_for('login'))

        if evento_finalizado:
            flash('Este evento ya finalizó, por lo que no se puede consultar ni validar el QR.', 'warning')
            return redirect(url_for('mis_eventos'))

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

@app.route('/soporte')
def soporte():
    """Página de soporte y reporte de problemas"""
    return render_template('soporte.html')

@app.route('/enviar-ticket', methods=['POST'])
def enviar_ticket():
    """Procesa el envío de tickets de soporte"""
    nombre_usuario = request.form.get('nombre')
    email_usuario = request.form.get('email')
    categoria = request.form.get('categoria')
    mensaje = request.form.get('descripcion')

    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = SUPPORT_EMAIL
    msg['Reply-To'] = email_usuario
    msg['Subject'] = f"TICKET [{categoria}] - De: {nombre_usuario}"

    cuerpo_correo = f"""
NUEVO TICKET DE SOPORTE

Nombre: {nombre_usuario}
Correo: {email_usuario}
Categoría: {categoria}

Descripción del problema:

{mensaje}

----------------------------------------
Sistema de Gestión de Eventos
UTN Facultad Regional San Francisco
"""

    msg.attach(MIMEText(cuerpo_correo, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        flash('¡Ticket enviado correctamente! El equipo de soporte fue notificado.', 'success')
        return redirect(url_for('soporte'))

    except Exception as e:
        print("Error:", e)
        flash(f'Error al enviar el ticket: {str(e)}', 'error')
        return redirect(url_for('soporte'))


@app.route('/generar-certificado', methods=['GET', 'POST'])
@login_required
def generar_certificado_view():
    """Formulario simple para generar un certificado y devolverlo como descarga."""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        dni = request.form.get('dni', '').strip()
        evento = request.form.get('evento', '').strip()

        if not nombre or not apellido or not dni or not evento:
            flash('Completa todos los campos.', 'error')
            return render_template('generar_certificado.html', nombre=nombre, apellido=apellido, dni=dni, evento=evento)

        try:
            salida = generar_certificado(nombre, apellido, dni, evento)
            return send_file(salida, as_attachment=True)
        except Exception as ex:
            print(f"[ERROR] generar_certificado_view: {ex}")
            flash('Ocurrió un error generando el certificado. Revisa que exista la plantilla y las fuentes.', 'error')
            return render_template('generar_certificado.html', nombre=nombre, apellido=apellido, dni=dni, evento=evento)

    return render_template('generar_certificado.html')

if __name__ == '__main__':
    app.run()
