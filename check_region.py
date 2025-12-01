import pandas as pd
from app import app, db
from models import ColumnOption

with app.app_context():
    # Check Excel
    df = pd.read_excel('./datalibrary_v2.xlsx')
    if 'region' in df.columns:
        regions = df['region'].dropna().unique()
        print(f'Excel has {len(regions)} unique regions: {list(regions)}')
        
        # Check database
        db_regions = ColumnOption.query.filter_by(column_name='region').all()
        print(f'Database has {len(db_regions)} region options')
        
        # Add missing ones
        for region in regions:
            if pd.notna(region) and str(region).strip():
                val_str = str(region).strip()
                existing = ColumnOption.query.filter_by(
                    column_name='region',
                    value=val_str
                ).first()
                if not existing:
                    option = ColumnOption(
                        column_name='region',
                        value=val_str,
                        is_multi_value=False
                    )
                    db.session.add(option)
                    print(f'Added: {val_str}')
        
        db.session.commit()
        print('Done!')

