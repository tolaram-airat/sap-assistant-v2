# setup_db.py
import sqlite3
import json
import os

# Ensure data directory exists
os.makedirs("sap-kb-app", exist_ok=True)
DB_PATH = "sap-kb-app/errors.db"

# === ONLY CREATE DB IF IT DOESN'T EXIST ===
if os.path.exists(DB_PATH):
    print("errors.db already exists. Skipping creation.")
else:
    print("Creating errors.db from errors.json and company.json...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create errors table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module TEXT,
        issuename TEXT,
        issuedescription TEXT,
        solutiontype TEXT,
        stepbystep TEXT,
        logcategory INTEGER,
        logsubcategory INTEGER,
        notes TEXT
    )
    """)

    # Create mappings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        code TEXT,
        name TEXT,
        logcategory INTEGER,
        logsubcategory INTEGER
    )
    """)

    # Load and insert errors
    try:
        with open("data/errors.json", 'r', encoding='utf-8') as f:
            errors = json.load(f)
            for error in errors:
                cursor.execute("""
                INSERT INTO errors 
                (module, issuename, issuedescription, solutiontype, stepbystep, logcategory, logsubcategory, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    error.get('module'),
                    error.get('issuename'),
                    error.get('issuedescription'),
                    error.get('solutiontype'),
                    error.get('stepbystep'),
                    error.get('logcategory'),
                    error.get('logsubcategory'),
                    error.get('notes')
                ))
        print(f"Loaded {len(errors)} errors.")
    except Exception as e:
        print(f"Error loading errors.json: {e}")

    # Load and insert company/profit center mappings
    try:
        with open("data/company.json", 'r', encoding='utf-8') as f:
            companies = json.load(f)
            company_count = 0
            profit_center_count = 0
            for item in companies:
                cursor.execute("""
                INSERT INTO mappings (type, code, name, logcategory, logsubcategory)
                VALUES (?, ?, ?, ?, ?)
                """, ('company', str(item['companyID']), item['companyname'], 3421, 3422))
                company_count += 1
                cursor.execute("""
                INSERT INTO mappings (type, code, name, logcategory, logsubcategory)
                VALUES (?, ?, ?, ?, ?)
                """, ('profit_center', str(item['ProfitCenterID']), item['ProfitCenterName'], 3421, 3423))
                profit_center_count += 1
            print(f"Loaded {company_count} companies, {profit_center_count} profit centers.")
    except Exception as e:
        print(f"Error loading company.json: {e}")

    conn.commit()
    conn.close()
    print("Database created successfully.")