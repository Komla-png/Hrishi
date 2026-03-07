#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect(r'instance/academy.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== Monthly Revenue Data (2026) ===")
monthly_data = cur.execute("""
    SELECT month,
           COALESCE(SUM(revenue), 0) AS total_revenue,
           COALESCE(SUM(target), 0) AS total_target
    FROM monthly_data
    WHERE year = 2026 
      AND month IN ('January', 'February', 'March')
    GROUP BY month
    ORDER BY 
        CASE month
            WHEN 'January' THEN 1
            WHEN 'February' THEN 2
            WHEN 'March' THEN 3
        END
""").fetchall()

previous_revenue = None
for row in monthly_data:
    revenue = row['total_revenue']
    
    if previous_revenue is None or previous_revenue == 0:
        growth = None
        growth_str = "N/A (baseline)"
    else:
        growth = ((revenue - previous_revenue) / previous_revenue) * 100
        growth_str = f"{growth:.1f}%"
    
    print(f"{row['month']}: Revenue ₹{revenue:,.0f}, Growth: {growth_str}")
    previous_revenue = revenue

print("\n=== December 2025 Data (for January 2026 growth comparison) ===")
dec_data = cur.execute("""
    SELECT COALESCE(SUM(revenue), 0) AS total_revenue
    FROM monthly_data
    WHERE year = 2025 AND month = 'December'
""").fetchone()

if dec_data and dec_data['total_revenue'] > 0:
    print(f"December 2025: Revenue ₹{dec_data['total_revenue']:,.0f}")
    jan_revenue = [r['total_revenue'] for r in monthly_data if r['month'] == 'January'][0]
    jan_growth = ((jan_revenue - dec_data['total_revenue']) / dec_data['total_revenue']) * 100
    print(f"January 2026 growth from Dec 2025: {jan_growth:.1f}%")
else:
    print("No December 2025 data available")

conn.close()
