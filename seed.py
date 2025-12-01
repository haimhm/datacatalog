import pandas as pd
from app import app, db
from models import DataProduct, ColumnOption

# Columns that should have dropdowns
# Will be auto-detected for multi-value based on comma-separated values in data
DROPDOWN_COLUMNS = [
    'asset_class',
    'datatype',
    'delivery_frequency',
    'delivery_lag',
    'delivery_method',
    'region',
    'stage',
    'status',
]

def seed_database():
    with app.app_context():
        # Clear existing data
        DataProduct.query.delete()
        ColumnOption.query.delete()
        
        # Read Excel file
        df = pd.read_excel('./datalibrary_v2.xlsx')
        
        # Detect multi-value columns (those with comma-separated values)
        multi_value_columns = set()
        for col_name in DROPDOWN_COLUMNS:
            if col_name in df.columns:
                has_commas = df[col_name].astype(str).str.contains(',', na=False).any()
                if has_commas:
                    multi_value_columns.add(col_name)
        
        # Extract unique values for dropdown columns
        for col_name in DROPDOWN_COLUMNS:
            if col_name in df.columns:
                is_multi = col_name in multi_value_columns
                unique_values = set()
                
                # Get all values, splitting by comma if multi-value
                for val in df[col_name].dropna():
                    if pd.notna(val):
                        val_str = str(val).strip()
                        # Skip empty strings and 'nan' strings
                        if val_str and val_str.lower() not in ['nan', 'none', '']:
                            if is_multi:
                                # Split by comma and add each value
                                parts = [v.strip() for v in val_str.split(',') 
                                        if v.strip() and v.strip().lower() not in ['nan', 'none', '']]
                                unique_values.update(parts)
                            else:
                                unique_values.add(val_str)
                
                # Add each unique value to ColumnOption
                for val_str in unique_values:
                    # Check if already exists
                    existing = ColumnOption.query.filter_by(
                        column_name=col_name,
                        value=val_str
                    ).first()
                    if not existing:
                        option = ColumnOption(
                            column_name=col_name,
                            value=val_str,
                            is_multi_value=is_multi
                        )
                        db.session.add(option)
                
                print(f"  {col_name}: {len(unique_values)} unique values (multi: {is_multi})")
        
        # Convert date columns
        date_columns = ['prod_date', 'trial_date', 'created_date', 'end_date', 
                        'pit_date', 'history_start', 'contract_start', 'contract_end']
        
        for _, row in df.iterrows():
            product = DataProduct()
            for col in df.columns:
                val = row[col]
                # Handle NaN values
                if pd.isna(val):
                    val = None
                # Handle date conversion
                elif col in date_columns and val is not None:
                    if hasattr(val, 'date'):
                        val = val.date()
                    else:
                        val = None
                setattr(product, col, val)
            db.session.add(product)
        
        db.session.commit()
        print(f"Seeded {len(df)} data products")
        print(f"Seeded {ColumnOption.query.count()} column options")
        
        # Verify each column has options
        for col_name in DROPDOWN_COLUMNS:
            count = ColumnOption.query.filter_by(column_name=col_name).count()
            print(f"  {col_name}: {count} options")

if __name__ == '__main__':
    seed_database()

