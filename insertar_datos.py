from main import app, db, User, Producto

with app.app_context():
    user = User.query.filter_by(username="admin").first()

    if user:
        db.session.delete(user)
        db.session.commit()
        print("🗑️ Usuario eliminado.")

    nuevo = User(username="hola", password="1234")
    db.session.add(nuevo)
    db.session.commit()
    
    # Agregar un producto
p = Producto(
        nombre='Franela Naruto',
        descripcion='Franela 100% algodón',
        precio=15.0,
        talla='M',
        anime='Naruto',
        imagen='naruto.png'
    )
    

print("✅ Usuario y producto añadidos correctamente.")
    
db.session.commit()