from main import app, db, User

with app.app_context():
    existente = User.query.filter_by(username="admin").first()
    if existente:
        db.session.delete(existente)
        db.session.commit()
        print("🗑️ Usuario anterior eliminado.")

    # Crear nuevo usuario
    nuevo = User(username="admin", password="23682844")
    db.session.add(nuevo)
    db.session.commit()
    print("✅ Usuario creado correctamente en easyboy.db")
