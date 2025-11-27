from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='standard')  # admin, standard, guest

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class DataProduct(db.Model):
    __tablename__ = 'data_products'
    
    id = db.Column(db.Integer, primary_key=True)
    data_ID = db.Column(db.String(200), unique=True)
    short_desc = db.Column(db.String(500))
    long_desc = db.Column(db.Text)
    stage = db.Column(db.String(100))
    status = db.Column(db.String(100))
    vendor_type = db.Column(db.String(100))
    datatype = db.Column(db.String(200))
    sub_datatype = db.Column(db.String(200))
    asset_class = db.Column(db.String(200))
    coverage_details = db.Column(db.String(500))
    sector = db.Column(db.String(200))
    region = db.Column(db.String(100))
    sub_region = db.Column(db.String(100))
    s3_location = db.Column(db.String(500))
    internal_location = db.Column(db.String(500))
    delivery_frequency = db.Column(db.String(100))
    delivery_lag = db.Column(db.String(100))
    vendor = db.Column(db.String(200))
    prod_date = db.Column(db.Date)
    trial_date = db.Column(db.Date)
    created_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    pit_date = db.Column(db.Date)
    history_start = db.Column(db.Date)
    delivery_method = db.Column(db.String(200))
    linked_docs = db.Column(db.Text)
    # Sensitive columns (Z-AG)
    user = db.Column(db.String(100))
    contract_start = db.Column(db.Date)
    contract_end = db.Column(db.Date)
    term = db.Column(db.String(100))
    annual_cost = db.Column(db.String(100))
    price_cap = db.Column(db.String(100))
    use_permissions = db.Column(db.Text)
    notes = db.Column(db.Text)

    def to_dict(self, include_sensitive=False):
        from config import SENSITIVE_COLUMNS
        result = {}
        for column in self.__table__.columns:
            if column.name == 'id':
                result[column.name] = getattr(self, column.name)
            elif column.name in SENSITIVE_COLUMNS and not include_sensitive:
                continue
            else:
                val = getattr(self, column.name)
                if hasattr(val, 'isoformat'):
                    val = val.isoformat() if val else None
                result[column.name] = val
        return result

