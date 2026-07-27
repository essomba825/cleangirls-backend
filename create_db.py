import pymysql

def create_database():
    try:
        # Connect to MySQL Server (without specifying a database)
        connection = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='',
            port=3306
        )
        try:
            with connection.cursor() as cursor:
                # Create database if it does not exist
                cursor.execute("CREATE DATABASE IF NOT EXISTS cleangirls_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            connection.commit()
            print("Base de données 'cleangirls_db' créée ou déjà existante.")
        finally:
            connection.close()
    except Exception as e:
        print(f"Erreur lors de la création de la base de données MySQL: {e}")
        print("Assurez-vous que XAMPP (MySQL) est démarré sur le port 3306 et accessible sans mot de passe pour l'utilisateur root.")

if __name__ == '__main__':
    create_database()
