from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import jsonify
import os
import json
import uuid
import requests

app = Flask(__name__)
app.secret_key = 'Edwin-148*'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///easyboy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

UPLOAD_FOLDER = 'static/uploads/comprobantes'
IMAGE_UPLOAD_FOLDER = 'static/imagenes'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['IMAGE_UPLOAD_FOLDER'] = IMAGE_UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# --- MODELOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    talla = db.Column(db.String(10))
    anime = db.Column(db.String(50))
    imagen = db.Column(db.String(100))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    destacado = db.Column(db.Boolean, default=False)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    cedula = db.Column(db.String(30), nullable=False)
    telefono = db.Column(db.String(30), nullable=False)
    direccion = db.Column(db.String(200))
    metodo_pago = db.Column(db.String(50), nullable=False)
    comprobante = db.Column(db.String(200))
    productos = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class ConfiguracionInicio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    anime1 = db.Column(db.String(50), nullable=False, default='kimetsu')
    anime2 = db.Column(db.String(50), nullable=False, default='naruto')
    

# --- PLUGINS BCV ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def obtener_tasa_bcv():
    def es_tasa_valida(tasa):
        return tasa and tasa > 80

    try:
        respuesta = requests.get("https://pydolarvenezuela-api.vercel.app/api/v1/dollar/official", timeout=5)
        if respuesta.status_code == 200:
            data = respuesta.json()
            tasa = float(data.get("price", 0))
            if es_tasa_valida(tasa):
                return tasa
    except:
        pass

    try:
        respuesta2 = requests.get("https://s3.amazonaws.com/dolartoday/data.json", timeout=5)
        if respuesta2.status_code == 200:
            data2 = respuesta2.json()
            tasa = float(data2.get("USD", {}).get("promedio", 0))
            if es_tasa_valida(tasa):
                return tasa
    except:
        pass

    return  102.16

@app.context_processor
def cantidad_total_carrito():
    carrito = session.get('carrito', {})
    total_cantidad = sum(carrito.values())
    return dict(cart_item_count=total_cantidad)

@app.route('/')
def index():
    ultimos_productos = Producto.query.order_by(Producto.fecha_creacion.desc()).limit(10).all()
    productos_destacados = Producto.query.filter_by(destacado=True).limit(10).all()

    config = ConfiguracionInicio.query.first()
    anime1 = config.anime1 if config else 'kimetsu'
    anime2 = config.anime2 if config else 'naruto'

    productos_anime1 = Producto.query.filter(Producto.anime.ilike(f'%{anime1}%')).limit(10).all()
    productos_anime2 = Producto.query.filter(Producto.anime.ilike(f'%{anime2}%')).limit(10).all()

    tasa_bcv = obtener_tasa_bcv()
    return render_template('index.html',fullwidth=True,
                           ultimos_productos=ultimos_productos,
                           productos_destacados=productos_destacados,
                           productos_anime1=productos_anime1,
                           productos_anime2=productos_anime2,
                           anime1=anime1,
                           anime2=anime2,
                           tasa_bcv=tasa_bcv)

def get_animes_disponibles():
    return ['Naruto', 'Dragon Ball', 'One Piece', 'Attack on Titan', 'Kimetsu', 'Jujutsu Kaisen', 'Tokyo Revengers', 'Boku no hero', 'Blue lock']

@app.route('/admin/configurar-secciones', methods=['GET', 'POST'])
def configurar_secciones():
    config = ConfiguracionInicio.query.first()
    if not config:
        config = ConfiguracionInicio()
        db.session.add(config)

    if request.method == 'POST':
        config.anime1 = request.form.get('anime1', 'kimetsu')
        config.anime2 = request.form.get('anime2', 'naruto')
        db.session.commit()
        flash('Secciones actualizadas correctamente.', 'success')
        return redirect(url_for('index'))

    return render_template('admin_configurar_secciones.html', config=config, animes_disponibles=get_animes_disponibles())

@app.route('/products')
def products():
    anime_filter = request.args.get('anime', None)
    page = request.args.get('page', 1, type=int)
    per_page = 12
    query = Producto.query
    if anime_filter:
        query = query.filter(Producto.anime.ilike(f'%{anime_filter}%'))
    pagination = query.paginate(page=page, per_page=per_page)
    productos = pagination.items
    tasa_bcv = obtener_tasa_bcv()
    return render_template('products.html', productos=productos, anime_filter=anime_filter, pagination=pagination, tasa_bcv=tasa_bcv)

@app.route('/add_to_cart/<int:producto_id>')
def add_to_cart(producto_id):
    carrito = session.get('carrito', {})
    carrito[str(producto_id)] = carrito.get(str(producto_id), 0) + 1
    session['carrito'] = carrito
    flash('Producto agregado al carrito', 'success')
    return redirect(request.referrer or url_for('products'))

@app.route('/agregar_al_carrito_ajax/<int:producto_id>', methods=['POST'])
def agregar_al_carrito_ajax(producto_id):
    producto = Producto.query.get(producto_id)
    if not producto:
        return jsonify({'success': False, 'mensaje': 'Producto no encontrado'}), 404

    carrito = session.get('carrito', {})
    carrito[str(producto_id)] = carrito.get(str(producto_id), 0) + 1
    session['carrito'] = carrito

    total_items = sum(carrito.values())

    return jsonify({
        'success': True,
        'cart_item_count': total_items,  # <- nombre esperado por el JS
        'mensaje': 'Producto agregado al carrito'
    })

@app.route('/carrito')
def carrito():
    carrito = session.get('carrito', {})
    productos_carrito = []
    total = 0
    for prod_id, cantidad in carrito.items():
        producto = Producto.query.get(int(prod_id))
        if producto:
            subtotal = producto.precio * cantidad
            total += subtotal
            productos_carrito.append({'producto': producto, 'cantidad': cantidad, 'subtotal': subtotal})
    tasa_bcv = obtener_tasa_bcv()
    return render_template('carrito.html', productos_carrito=productos_carrito, total=total, tasa_bcv=tasa_bcv)

@app.route('/remove_from_cart/<int:producto_id>')
def remove_from_cart(producto_id):
    carrito = session.get('carrito', {})
    carrito.pop(str(producto_id), None)
    session['carrito'] = carrito
    flash('Producto removido del carrito', 'info')
    return redirect(url_for('carrito'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    carrito = session.get('carrito', {})
    if not carrito:
        flash('Tu carrito está vacío', 'warning')
        return redirect(url_for('products'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        cedula = request.form.get('cedula', '').strip()
        telefono = request.form.get('telefono', '').strip()
        direccion = request.form.get('direccion', '').strip()
        metodo_pago = request.form.get('metodo_pago', '').strip()
        comprobante_file = request.files.get('comprobante')
        comprobante_filename = None

        errores = []
        if not nombre:
            errores.append('El nombre es obligatorio.')
        if not cedula:
            errores.append('La cédula es obligatoria.')
        if not telefono:
            errores.append('El teléfono es obligatorio.')
        if not metodo_pago:
            errores.append('Debe seleccionar un método de pago.')

        if metodo_pago == 'Pago Móvil':
            if not comprobante_file or comprobante_file.filename == '':
                errores.append('Debes subir un comprobante para Pago Móvil.')
            elif not allowed_file(comprobante_file.filename):
                errores.append('El comprobante debe ser imagen o PDF.')

        if errores:
            for e in errores:
                flash(e, 'danger')
            return redirect(url_for('checkout'))

        if comprobante_file and comprobante_file.filename:
            filename = secure_filename(comprobante_file.filename)
            unique = f"{uuid.uuid4().hex}_{filename}"
            path = os.path.join(app.config['UPLOAD_FOLDER'], unique)
            comprobante_file.save(path)
            comprobante_filename = path.replace('static/', '', 1)

        pedido = Pedido(
            nombre=nombre,
            cedula=cedula,
            telefono=telefono,
            direccion=direccion,
            metodo_pago=metodo_pago,
            comprobante=comprobante_filename,
            productos=json.dumps(carrito)
        )
        db.session.add(pedido)
        db.session.commit()
        session.pop('carrito')
        flash('Pedido recibido, gracias por comprar con nosotros!', 'success')
        return redirect(url_for('products'))

    productos_carrito = []
    total = 0
    for prod_id, cantidad in carrito.items():
        producto = Producto.query.get(int(prod_id))
        if producto:
            subtotal = producto.precio * cantidad
            total += subtotal
            productos_carrito.append({'producto': producto, 'cantidad': cantidad, 'subtotal': subtotal})
    tasa_bcv = obtener_tasa_bcv()
    return render_template('checkout.html', productos_carrito=productos_carrito, total=total, tasa_bcv=tasa_bcv)

@app.route('/admin/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        talla = request.form['talla']
        anime = request.form['anime']
        destacado = 'destacado' in request.form
        img = request.files.get('imagen')

        if not img or not allowed_file(img.filename):
            flash('Imagen inválida.', 'danger')
            return redirect(request.url)
        fn = secure_filename(img.filename)
        unique_fn = f"{uuid.uuid4().hex}_{fn}"
        img.save(os.path.join(app.config['IMAGE_UPLOAD_FOLDER'], unique_fn))

        nuevo_producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            talla=talla,
            anime=anime,
            imagen=unique_fn,
            destacado=destacado
        )
        db.session.add(nuevo_producto)
        db.session.commit()
        flash('Producto agregado.', 'success')
        return redirect(url_for('products'))
    return render_template('admin_agregar_producto.html')

@app.route('/admin/pedidos')
def admin_pedidos():
    pedidos = Pedido.query.order_by(Pedido.fecha.desc()).all()
    detalles = []
    for ped in pedidos:
        productos = []
        try:
            pd = json.loads(ped.productos)
        except:
            pd = {}
        for pid, qty in pd.items():
            pr = Producto.query.get(int(pid))
            productos.append({'nombre': pr.nombre if pr else '---', 'cantidad': qty, 'imagen': pr.imagen if pr else None})
        detalles.append({'pedido': ped, 'productos_detalle': productos})
    return render_template('admin_pedidos.html', pedidos_con_productos=detalles)

@app.route('/producto/<int:producto_id>')
def product_detail(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    tasa_bcv = obtener_tasa_bcv()
    return render_template('product_detail.html', producto=producto, tasa_bcv=tasa_bcv)

@app.route('/admin/productos/editar/<int:producto_id>', methods=['GET', 'POST'])
def editar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)

    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.descripcion = request.form['descripcion']
        producto.precio = float(request.form['precio'])
        producto.talla = request.form['talla']
        producto.anime = request.form['anime']
        producto.destacado = 'destacado' in request.form

        imagen = request.files.get('imagen')
        if imagen and allowed_file(imagen.filename):
            filename = secure_filename(imagen.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            imagen.save(os.path.join(app.config['IMAGE_UPLOAD_FOLDER'], unique_filename))
            producto.imagen = unique_filename

        db.session.commit()
        flash('Producto actualizado correctamente.', 'success')
        return redirect(url_for('products'))

    return render_template('admin_editar_producto.html', producto=producto)

@app.route('/admin/productos/eliminar/<int:producto_id>', methods=['POST'])
def eliminar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado correctamente.', 'success')
    return redirect(url_for('admin_productos'))

@app.route('/admin/productos')
def admin_productos():
    productos = Producto.query.order_by(Producto.fecha_creacion.desc()).all()
    return render_template('admin_productos.html', productos=productos)

# ===================== LOGIN Y PROTECCIÓN ADMIN =====================

@app.before_request
def proteger_rutas_admin():
    ruta = request.path
    if ruta.startswith('/admin') and 'user_id' not in session and not ruta.startswith('/admin/static'):
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            flash('Has iniciado sesión correctamente.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Credenciales inválidas', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Sesión cerrada exitosamente.', 'info')
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

# ===================== FIN LOGIN Y ADMIN PANEL =====================


if __name__ == '__main__':
    app.run(debug=True)
else:
    with app.app_context():
        try:
            # Verificamos si existe alguna tabla antes de crear
            db.session.execute('SELECT 1 FROM producto LIMIT 1')
        except Exception:
            print("🔧 No existen tablas. Creando todas las tablas...")
            db.create_all()

