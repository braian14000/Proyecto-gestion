from .entities.users import User

class ModelUser():

    @classmethod
    def login(cls, db, user):
        try:
            cursor = db.connection.cursor()
            # Buscamos por email y seleccionamos las columnas correctas
            sql = "SELECT id, username, email, password, telefono FROM `user` WHERE email = %s"
            cursor.execute(sql, (user.email,))
            row = cursor.fetchone()
            
            if row != None:
                # Mapeamos los datos respetando el constructor de User
                user_match = User(row[0], row[1], row[2], User.check_password(row[3], user.password), row[4])
                return user_match
            else:
                return None
        except Exception as ex:
            raise Exception(ex)

    @classmethod
    def get_by_id(cls, db, id):
        try:
            cursor = db.connection.cursor()
            sql = "SELECT id, username, email, telefono FROM `user` WHERE id = %s"
            cursor.execute(sql, (id,))
            row = cursor.fetchone()
            
            if row != None:
                return User(row[0], row[1], row[2], None, row[3])
            else:
                return None
        except Exception as ex:
            raise Exception(ex)
