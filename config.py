import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database configuration - easily switchable between SQLite/PostgreSQL/MySQL
    # SQLite (default): sqlite:///data_catalog.db
    # PostgreSQL: postgresql://user:password@localhost/data_catalog
    # MySQL: mysql+pymysql://user:password@localhost/data_catalog
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///data_catalog.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# Sensitive columns (Z-AG) - hidden from non-admin users
SENSITIVE_COLUMNS = [
    'user', 'contract_start', 'contract_end', 'term',
    'annual_cost', 'price_cap', 'use_permissions', 'notes'
]

