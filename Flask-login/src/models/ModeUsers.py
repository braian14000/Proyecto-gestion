from .entities.users import User

class ModelUser():

    @classmethod
    def login(cls, db, user):
        try:
            cursor = db.connection.cursor()
            sql = "SELECT id, username, email, password, telefono, dni FROM `user` WHERE email = %s OR username = %s"
            cursor.execute(sql, (user.email, user.email))
            row = cursor.fetchone()
            
            if row != None:
                hashed_password = row[3]
                user_match = User(
                    row[0],
                    row[1],
                    row[2],
                    User.check_password(hashed_password, user.password),
                    row[4],
                    row[5]
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
            sql = "SELECT id, username, email, telefono, dni FROM `user` WHERE id = %s"
            cursor.execute(sql, (id,))
            row = cursor.fetchone()
            
            if row != None:
                return User(row[0], row[1], row[2], None, row[3], row[4])
            else:
                return None
        except Exception as ex:
            raise Exception(ex)
