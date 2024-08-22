from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import io
import base64
from functools import wraps
import config

app = Flask(__name__)
app.config.from_object(config.Config)
db.init_app(app)
mail = Mail(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        is_admin = 'is_admin' in request.form
        hashed_password = generate_password_hash(password, method='sha256')
        user = User(username=username, email=email, password=hashed_password, is_admin=is_admin)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/admin/items', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_items():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        item = MenuItem(name=name, price=price)
        db.session.add(item)
        db.session.commit()
        return redirect(url_for('manage_items'))
    items = MenuItem.query.all()
    return render_template('admin_items.html', items=items)

@app.route('/admin/orders', methods=['GET'])
@login_required
@admin_required
def manage_orders():
    search_query = request.args.get('search')
    if search_query:
        orders = Order.query.filter(
            Order.id.like(f'%{search_query}%') |
            Order.table_number.like(f'%{search_query}%') |
            Order.items.like(f'%{search_query}%')
        ).all()
    else:
        orders = Order.query.all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/customers')
@login_required
@admin_required
def manage_customers():
    customers = Customer.query.all()
    return render_template('admin_customers.html', customers=customers)

@app.route('/admin/update_upi', methods=['GET', 'POST'])
@login_required
@admin_required
def update_upi():
    if request.method == 'POST':
        new_upi_id = request.form['upi_id']
        app.config['UPI_ID'] = new_upi_id
        return redirect(url_for('update_upi'))
    return render_template('update_upi.html', upi_id=app.config.get('UPI_ID', ''))

@app.route('/order', methods=['GET', 'POST'])
@login_required
def order():
    if request.method == 'POST':
        table_number = request.form['table_number']
        item_ids = request.form.getlist('item_ids')
        total_price = float(request.form['total_price'])
        items = ', '.join(MenuItem.query.filter(MenuItem.id.in_(item_ids)).all())
        customer_id = request.form.get('customer_id')
        new_order = Order(
            table_number=table_number,
            items=items,
            total_price=total_price,
            customer_id=customer_id,
            user_id=current_user.id
        )
        db.session.add(new_order)
        db.session.commit()
        send_order_confirmation_email(new_order)
        return redirect(url_for('receipt', order_id=new_order.id))
    items = MenuItem.query.all()
    customers = Customer.query.all()
    return render_template('order.html', items=items, customers=customers)

@app.route('/receipt/<int:order_id>')
@login_required
def receipt(order_id):
    order = Order.query.get_or_404(order_id)
    qr_img = generate_upi_qr_code(app.config.get('UPI_ID', ''), order.total_price)
    qr_img_base64 = base64.b64encode(qr_img.getvalue()).decode('utf-8')
    return render_template('receipt.html', order=order, qr_code=qr_img_base64)

def generate_upi_qr_code(upi_id, amount):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f'upi://pay?pa={upi_id}&pn=Restaurant&mc=0000&tid=00000000&tr=000000&tn=Order&am={amount}&cu=INR&url=')
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return buf

def send_order_confirmation_email(order):
    msg = Message('Order Confirmation', sender='your-email@gmail.com', recipients=['recipient-email@gmail.com'])
    msg.body = f'Order ID: {order.id}\nTable Number: {order.table_number}\nTotal Price: ₹{order.total_price}\nItems: {order.items}'
    mail.send(msg)

if __name__ == '__main__':
    app.run(debug=True)
