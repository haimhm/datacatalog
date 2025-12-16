from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from models import db, User, DataProduct, ColumnOption
from config import Config, SENSITIVE_COLUMNS
from datetime import datetime
import os
import re
from werkzeug.utils import secure_filename

DATE_FIELDS = ['prod_date', 'trial_date', 'created_date', 'end_date', 'pit_date', 
               'history_start', 'contract_start', 'contract_end']

def parse_value(key, value):
    """Convert empty strings to None and date strings to date objects"""
    if value == '' or value is None:
        return None
    if key in DATE_FIELDS:
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except (ValueError, TypeError) as e:
            return None
    return value

# Input validation functions
def validate_username(username):
    """Validate username: alphanumeric, underscore, 3-80 characters"""
    if not username or not isinstance(username, str):
        return False, 'Username is required'
    if len(username) < 3 or len(username) > 80:
        return False, 'Username must be between 3 and 80 characters'
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, 'Username can only contain letters, numbers, and underscores'
    return True, None

def validate_password(password):
    """Validate password: minimum 8 characters"""
    if not password or not isinstance(password, str):
        return False, 'Password is required'
    if len(password) < 8:
        return False, 'Password must be at least 8 characters long'
    if len(password) > 256:
        return False, 'Password is too long (max 256 characters)'
    return True, None

def validate_role(role):
    """Validate user role"""
    valid_roles = ['admin', 'standard', 'guest']
    if role not in valid_roles:
        return False, f'Role must be one of: {", ".join(valid_roles)}'
    return True, None

def sanitize_string(value, max_length=None):
    """Sanitize string input by stripping whitespace and limiting length"""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if max_length and len(value) > max_length:
        value = value[:max_length]
    return value

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables and default users (only in development)
with app.app_context():
    db.create_all()
    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Only create default users if explicitly enabled via environment variable
    if os.environ.get('CREATE_DEFAULT_USERS', '').lower() == 'true':
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
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password are required'}), 400
    
    # Validate username format
    is_valid, error_msg = validate_username(username)
    if not is_valid:
        return jsonify({'success': False, 'error': error_msg}), 400
    
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
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
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    
    product = DataProduct()
    for key, value in data.items():
        if hasattr(product, key) and key != 'id':
            # Sanitize string values
            if isinstance(value, str):
                # Get max length from model if available
                column = getattr(product.__table__.columns, key, None)
                max_length = column.type.length if column and hasattr(column.type, 'length') else None
                value = sanitize_string(value, max_length)
            setattr(product, key, parse_value(key, value))
    
    try:
        db.session.add(product)
        db.session.commit()
        return jsonify(product.to_dict(include_sensitive=True)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create product'}), 500

@app.route('/api/products/<int:id>', methods=['PUT'])
@login_required
def update_product(id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    product = DataProduct.query.get_or_404(id)
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    
    for key, value in data.items():
        if hasattr(product, key) and key != 'id':
            # Sanitize string values
            if isinstance(value, str):
                # Get max length from model if available
                column = getattr(product.__table__.columns, key, None)
                max_length = column.type.length if column and hasattr(column.type, 'length') else None
                value = sanitize_string(value, max_length)
            setattr(product, key, parse_value(key, value))
    
    try:
        db.session.commit()
        return jsonify(product.to_dict(include_sensitive=True))
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update product'}), 500

@app.route('/api/products/<int:id>', methods=['DELETE'])
@login_required
def delete_product(id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    try:
        product = DataProduct.query.get_or_404(id)
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete product'}), 500

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
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'standard')
    
    # Validate inputs
    is_valid, error_msg = validate_username(username)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    is_valid, error_msg = validate_role(role)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    user = User(username=username, role=role)
    user.set_password(password)
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
    try:
        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete user'}), 500

@app.route('/api/column-options')
def get_column_options():
    """Get all column options grouped by column name"""
    options = ColumnOption.query.all()
    result = {}
    for opt in options:
        if opt.column_name not in result:
            result[opt.column_name] = {
                'values': [],
                'is_multi_value': opt.is_multi_value
            }
        result[opt.column_name]['values'].append(opt.value)
    # Sort values
    for col in result:
        result[col]['values'].sort()
    return jsonify(result)

@app.route('/api/column-options/all')
def get_all_column_options():
    """Get all column options with IDs"""
    options = ColumnOption.query.all()
    return jsonify([opt.to_dict() for opt in options])

@app.route('/api/column-options', methods=['POST'])
@login_required
def create_column_option():
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    
    column_name = sanitize_string(data.get('column_name'), max_length=100)
    value = sanitize_string(data.get('value'), max_length=500)
    is_multi_value = bool(data.get('is_multi_value', False))
    
    if not column_name or not value:
        return jsonify({'error': 'Column name and value are required'}), 400
    
    try:
        option = ColumnOption(
            column_name=column_name,
            value=value,
            is_multi_value=is_multi_value
        )
        db.session.add(option)
        db.session.commit()
        return jsonify(option.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create column option'}), 500

@app.route('/api/column-options/<int:id>', methods=['DELETE'])
@login_required
def delete_column_option(id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    option = ColumnOption.query.get_or_404(id)
    db.session.delete(option)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/column-options/delete', methods=['POST'])
@login_required
def delete_column_option_by_value():
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    
    column_name = sanitize_string(data.get('column_name'), max_length=100)
    value = sanitize_string(data.get('value'), max_length=500)
    
    if not column_name or not value:
        return jsonify({'error': 'Column name and value are required'}), 400
    
    try:
        option = ColumnOption.query.filter_by(
            column_name=column_name,
            value=value
        ).first()
        if option:
            db.session.delete(option)
            db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete column option'}), 500

@app.route('/dataset/<int:id>')
def dataset_detail(id):
    """Render the dataset detail page"""
    product = DataProduct.query.get_or_404(id)
    is_admin = current_user.is_authenticated and current_user.role == 'admin'
    
    # Parse linked_docs string into a list
    linked_docs = []
    if product.linked_docs:
        # Split by newline or comma
        docs_str = str(product.linked_docs).strip()
        if docs_str:
            linked_docs = [d.strip() for d in docs_str.replace('\r', '').split('\n') if d.strip()]
            if not linked_docs:
                # Try comma separation if no newlines
                linked_docs = [d.strip() for d in docs_str.split(',') if d.strip()]
    
    return render_template('dataset_detail.html', 
                         product=product, 
                         linked_docs=linked_docs,
                         is_admin=is_admin)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/api/dataset/<int:id>/upload', methods=['POST'])
@login_required
def upload_document(id):
    """Upload a document for a dataset"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    product = DataProduct.query.get_or_404(id)
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        # Ensure upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Secure filename and create unique name
        filename = secure_filename(file.filename)
        # Add timestamp to make filename unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Create URL for the file
        file_url = f"/uploads/{filename}"
        
        # Add to linked_docs
        if product.linked_docs:
            product.linked_docs = product.linked_docs + '\n' + file_url
        else:
            product.linked_docs = file_url
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'url': file_url,
            'filename': filename
        })
    else:
        return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/dataset/<int:id>/documents', methods=['DELETE'])
@login_required
def delete_document(id):
    """Delete a document from a dataset"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    product = DataProduct.query.get_or_404(id)
    data = request.get_json()
    url_to_delete = data.get('url', '')
    
    if not url_to_delete:
        return jsonify({'error': 'No URL provided'}), 400
    
    # Remove from linked_docs
    if product.linked_docs:
        docs = [d.strip() for d in product.linked_docs.replace('\r', '').split('\n') if d.strip()]
        if not docs:
            docs = [d.strip() for d in product.linked_docs.split(',') if d.strip()]
        
        docs = [d for d in docs if d != url_to_delete]
        product.linked_docs = '\n'.join(docs) if docs else None
        
        # Try to delete file from filesystem
        if url_to_delete.startswith('/uploads/'):
            filename = url_to_delete.replace('/uploads/', '')
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as e:
                    # Log error but don't fail the request
                    print(f"Error deleting file {filepath}: {e}")
        
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'No documents found'}), 404

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/filters')
def get_filters():
    """Get unique values for filter dropdowns"""
    products = DataProduct.query.all()
    
    def extract_values(field_value):
        """Extract individual values from a field, splitting by comma if needed"""
        if not field_value:
            return []
        # Convert to string and split by comma
        value_str = str(field_value).strip()
        if not value_str or value_str.lower() in ['nan', 'none', '']:
            return []
        # Split by comma and clean up each value
        values = [v.strip() for v in value_str.split(',') if v.strip() and v.strip().lower() not in ['nan', 'none']]
        return values
    
    # Collect all unique values, splitting comma-separated ones
    categories = set()
    vendors = set()
    regions = set()
    statuses = set()
    stages = set()
    asset_classes = set()
    
    for p in products:
        if p.datatype:
            categories.update(extract_values(p.datatype))
        if p.vendor:
            vendors.update(extract_values(p.vendor))
        if p.region:
            regions.update(extract_values(p.region))
        if p.status:
            statuses.update(extract_values(p.status))
        if p.stage:
            stages.update(extract_values(p.stage))
        if p.asset_class:
            asset_classes.update(extract_values(p.asset_class))
    
    filters = {
        'categories': sorted(categories),
        'vendors': sorted(vendors),
        'regions': sorted(regions),
        'statuses': sorted(statuses),
        'stages': sorted(stages),
        'asset_classes': sorted(asset_classes),
    }
    return jsonify(filters)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

