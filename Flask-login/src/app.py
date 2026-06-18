from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Configuración básica de desarrollo integrada para evitar dependencias
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'clave_secreta_temporal'

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        print(request.form['username'])
        print(request.form['password'])
        return render_template('auth/login.html')
    else:
        return render_template('auth/login.html')

if __name__ == '__main__':
    app.run()