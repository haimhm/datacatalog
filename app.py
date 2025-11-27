from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from models import db, User, DataProduct
from config import Config, SENSITIVE_COLUMNS
from datetime import datetime

DATE_FIELDS = ['prod_date', 'trial_date', 'created_date', 'end_date', 'pit_date', 
               'history_start', 'contract_start', 'contract_end']

def parse_value(key, value):
    """Convert empty strings to None and date strings to date objects"""
    if value == '' or value is None:
        return None
    if key in DATE_FIELDS:
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except:
            return None
    return value

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables and default users
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin')
        admin.set_password('admin')
        user = User(username='user', role='standard')
        user.set_password('user')
        db.session.add(admin)
        db.session.add(user)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if user and user.check_password(data.get('password')):
        login_user(user)
        return jsonify({'success': True, 'role': user.role, 'username': user.username})
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    logout_user()
    return jsonify({'success': True})

@app.route('/api/user')
def get_user():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'username': current_user.username, 'role': current_user.role})
    return jsonify({'authenticated': False, 'role': 'guest'})

@app.route('/api/products')
def get_products():
    products = DataProduct.query.all()
    is_admin = current_user.is_authenticated and current_user.role == 'admin'
    return jsonify([p.to_dict(include_sensitive=is_admin) for p in products])

@app.route('/api/products/<int:id>')
def get_product(id):
    product = DataProduct.query.get_or_404(id)
    is_admin = current_user.is_authenticated and current_user.role == 'admin'
    return jsonify(product.to_dict(include_sensitive=is_admin))

@app.route('/api/products', methods=['POST'])
@login_required
def create_product():
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    data = request.get_json()
    product = DataProduct()
    for key, value in data.items():
        if hasattr(product, key):
            setattr(product, key, parse_value(key, value))
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict(include_sensitive=True)), 201

@app.route('/api/products/<int:id>', methods=['PUT'])
@login_required
def update_product(id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    product = DataProduct.query.get_or_404(id)
    data = request.get_json()
    for key, value in data.items():
        if hasattr(product, key) and key != 'id':
            setattr(product, key, parse_value(key, value))
    db.session.commit()
    return jsonify(product.to_dict(include_sensitive=True))

@app.route('/api/products/<int:id>', methods=['DELETE'])
@login_required
def delete_product(id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    product = DataProduct.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/users')
@login_required
def get_users():
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username, 'role': u.role} for u in users])

@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    data = request.get_json()
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({'error': 'Username already exists'}), 400
    user = User(username=data['username'], role=data.get('role', 'standard'))
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'id': user.id, 'username': user.username, 'role': user.role}), 201

@app.route('/api/users/<int:id>', methods=['DELETE'])
@login_required
def delete_user(id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    if id == current_user.id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/filters')
def get_filters():
    """Get unique values for filter dropdowns"""
    products = DataProduct.query.all()
    filters = {
        'categories': sorted(set(p.datatype for p in products if p.datatype)),
        'vendors': sorted(set(p.vendor for p in products if p.vendor)),
        'regions': sorted(set(p.region for p in products if p.region)),
        'statuses': sorted(set(p.status for p in products if p.status)),
        'stages': sorted(set(p.stage for p in products if p.stage)),
    }
    return jsonify(filters)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

