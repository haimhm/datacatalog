import pandas as pd
from app import app, db
from models import DataProduct

def seed_database():
    with app.app_context():
        # Clear existing data
        DataProduct.query.delete()
        
        # Read Excel file
        df = pd.read_excel('./datalibrary_v2.xlsx')
        
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

if __name__ == '__main__':
    seed_database()

