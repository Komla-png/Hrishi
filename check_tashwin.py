#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect(r'instance/academy.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Find Tashwin center
tashwin = cur.execute("SELECT id, name FROM centers WHERE name LIKE '%Tashwin%'").fetchone()
if not tashwin:
    print("Tashwin center not found!")
    exit(1)

center_id = tashwin['id']
print(f"Tashwin Center ID: {center_id}")
print(f"Tashwin Center Name: {tashwin['name']}")
print()

# Check coaches assigned to Tashwin
print("=== Coaches at Tashwin ===")
coaches = cur.execute("""
    SELECT id, name, end_month, end_year 
    FROM coaches 
    WHERE center_id = ?
""", (center_id,)).fetchall()

for coach in coaches:
    status = "ACTIVE" if coach['end_month'] is None else f"INACTIVE (ended {coach['end_month']} {coach['end_year']})"
    print(f"Coach ID {coach['id']}: {coach['name']} - {status}")

if not coaches:
    print("No coaches found for Tashwin!")
else:
    print(f"\nTotal coaches: {len(coaches)}")
    active_coaches = [c for c in coaches if c['end_month'] is None]
    print(f"Active coaches: {len(active_coaches)}")

print()

# Check salary data for Tashwin coaches
print("=== Salary Data for Tashwin Coaches (2026, Jan-Mar) ===")
salary_data = cur.execute("""
    SELECT cs.coach_id, co.name, cs.month, cs.salary
    FROM coach_salaries cs
    JOIN coaches co ON cs.coach_id = co.id
    WHERE co.center_id = ? 
      AND cs.year = 2026 
      AND cs.month IN ('January', 'February', 'March')
    ORDER BY cs.month, co.name
""", (center_id,)).fetchall()

if salary_data:
    for row in salary_data:
        print(f"{row['month']}: {row['name']} - ₹{row['salary']:,}")
else:
    print("No salary data found for Tashwin coaches in Jan-Mar 2026!")

# Check only active coaches
print("\n=== Salary Data for ACTIVE Tashwin Coaches ===")
active_salary = cur.execute("""
    SELECT cs.coach_id, co.name, cs.month, cs.salary
    FROM coach_salaries cs
    JOIN coaches co ON cs.coach_id = co.id
    WHERE co.center_id = ? 
      AND cs.year = 2026 
      AND cs.month IN ('January', 'February', 'March')
      AND co.end_month IS NULL
      AND co.end_year IS NULL
    ORDER BY cs.month, co.name
""", (center_id,)).fetchall()

if active_salary:
    total = 0
    for row in active_salary:
        print(f"{row['month']}: {row['name']} - ₹{row['salary']:,}")
        total += row['salary']
    print(f"\nTotal active coach salary (Jan-Mar): ₹{total:,}")
else:
    print("No salary data found for ACTIVE Tashwin coaches!")

print()

# Check revenue data for Tashwin
print("=== Revenue Data for Tashwin (2026, Jan-Mar) ===")
revenue_data = cur.execute("""
    SELECT month, revenue, target
    FROM monthly_data
    WHERE center_id = ? 
      AND year = 2026 
      AND month IN ('January', 'February', 'March')
    ORDER BY 
        CASE month
            WHEN 'January' THEN 1
            WHEN 'February' THEN 2
            WHEN 'March' THEN 3
        END
""", (center_id,)).fetchall()

if revenue_data:
    for row in revenue_data:
        print(f"{row['month']}: Revenue ₹{row['revenue']:,}, Target ₹{row['target']:,}")
else:
    print("No revenue data found for Tashwin!")

conn.close()
