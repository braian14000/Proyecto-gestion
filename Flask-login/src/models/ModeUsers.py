from .entities.users import User

class ModelUser():

    @classmethod
    def login(cls, db, user):
        try:
            cursor = db.connection.cursor()
            sql = "SELECT id, username, email, password, telefono, dni, rol FROM `user` WHERE email = %s OR username = %s"
            cursor.execute(sql, (user.email, user.email))
            row = cursor.fetchone()
            
            if row != None:
                hashed_password = row[3]
                rol = (row[6] or 'estudiante').strip().lower() if len(row) > 6 else 'estudiante'
                user_match = User(
                    row[0],
                    row[1],
                    row[2],
                    User.check_password(hashed_password, user.password),
                    row[4],
                    row[5],
                    rol
                )
                return user_match
            else:
                return None
        except Exception as ex:
            raise Exception(ex)

    @classmethod
    def get_by_id(cls, db, id):
        try:
            cursor = db.connection.cursor()
            sql = "SELECT id, username, email, telefono, dni, rol FROM `user` WHERE id = %s"
            cursor.execute(sql, (id,))
            row = cursor.fetchone()
            
            if row != None:
                rol = (row[5] or 'estudiante').strip().lower() if len(row) > 5 else 'estudiante'
                return User(row[0], row[1], row[2], None, row[3], row[4], rol)
            else:
                return None
        except Exception as ex:
            raise Exception(ex)
    
    @classmethod
    def get_all_users(cls, db):
        """Obtiene todos los usuarios de la base de datos"""
        try:
            cursor = db.connection.cursor()
            # Usar id DESC para ordenar por ID descendente en lugar de created_at
            sql = "SELECT id, username, email, telefono, dni, rol FROM `user` ORDER BY id DESC"
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            users = []
            if rows:
                for row in rows:
                    rol = (row[5] or 'estudiante').strip().lower() if len(row) > 5 else 'estudiante'
                    user = User(row[0], row[1], row[2], None, row[3], row[4], rol)
                    users.append(user)
            
            return users
        except Exception as ex:
            print(f"[ERROR] get_all_users: {ex}")
            return []
    
    @classmethod
    def update_rol(cls, db, user_id, new_rol):
        """Actualiza el rol de un usuario"""
        try:
            cursor = db.connection.cursor()
            sql = "UPDATE `user` SET rol = %s WHERE id = %s"
            cursor.execute(sql, (new_rol, user_id))
            db.connection.commit()
            return True
        except Exception as ex:
            raise Exception(ex)