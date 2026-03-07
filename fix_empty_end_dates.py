#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect(r'instance/academy.db')
cur = conn.cursor()

# Find all coaches with empty string end_month or end_year
print("=== Coaches with empty string end dates (should be NULL) ===")
cur.execute("""
    SELECT id, name, center_id, end_month, end_year
    FROM coaches
    WHERE (end_month = '' OR end_year = '')
""")
coaches = cur.fetchall()

if coaches:
    for coach in coaches:
        print(f"Coach ID {coach[0]}: {coach[1]} (Center {coach[2]}) - end_month='{coach[3]}', end_year='{coach[4]}'")
    
    print(f"\nFound {len(coaches)} coaches with empty string end dates")
    print("Fixing by setting empty strings to NULL...")
    
    # Fix by setting empty strings to NULL
    cur.execute("""
        UPDATE coaches 
        SET end_month = NULL, end_year = NULL
        WHERE end_month = '' OR end_year = ''
    """)
    
    conn.commit()
    print(f"✓ Fixed {cur.rowcount} coaches - set empty strings to NULL")
else:
    print("No coaches found with empty string end dates")

conn.close()
