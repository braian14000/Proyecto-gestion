from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  


EVENTOS = [
    {
        'id': 1,
        'titulo': 'Concierto de Rock',
        'fecha': '2026-07-15',
        'descripcion': 'Una noche increíble con las mejores bandas locales.',
        'lugar': 'Estadio Principal'
    }
]

@app.route('/')
def home():

    if 'usuario' in session:
        if session['usuario'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('ver_eventos'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    usuario = request.form.get('usuario')
    contraseña = request.form.get('contrasena')


    if usuario == 'admin' and contraseña == 'admin':
        session['usuario'] = 'admin'
        return redirect(url_for('admin_dashboard'))
    elif usuario and contraseña:  
        session['usuario'] = usuario
        return redirect(url_for('ver_eventos'))
    
    return "Usuario o contraseña incorrectos", 401


@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if session.get('usuario') != 'admin':
        return redirect(url_for('home'))

    if request.method == 'POST':
        
        nuevo_evento = {
            'id': len(EVENTOS) + 1,
            'titulo': request.form.get('titulo'),
            'fecha': request.form.get('fecha'),
            'descripcion': request.form.get('descripcion'),
            'lugar': request.form.get('lugar')
        }
        EVENTOS.append(nuevo_evento)
        return redirect(url_for('ver_eventos')) 

    return render_template('admin.html')


@app.route('/eventos')
def ver_eventos():
    if 'usuario' not in session:
        return redirect(url_for('home'))
    
    return render_template('eventos.html', eventos=EVENTOS, usuario=session['usuario'])


@app.route('/evento/<int:evento_id>')
def detalle_evento(evento_id):
    if 'usuario' not in session:
        return redirect(url_for('home'))
    

    evento = next((e for e in EVENTOS if e['id'] == evento_id), None)
    
    if evento is None:
        return "Evento no encontrado", 404
        
    return render_template('detalle.html', evento=evento)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
