from werkzeug.security import check_password_hash
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, email, password, telefono="", dni="", rol="estudiante"):
        self.id = id
        self.username = username  
        self.email = email        
        self.password = password
        self.telefono = telefono
        self.dni = dni
        self.rol = rol
    
    def is_admin(self):
        return self.rol == 'admin'
    
    def is_organizador(self):
        return self.rol == 'organizador'
    
    def is_estudiante(self):
        return self.rol == 'estudiante'

    @classmethod
    def check_password(cls, hashed_password, password):
        return check_password_hash(hashed_password, password)
