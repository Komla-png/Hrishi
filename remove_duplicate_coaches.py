"""
Remove duplicate coaches from the database.

This script identifies coaches with identical names and keeps only the first one,
merging any associated data (salaries, leaves) to the kept coach.
"""

import sqlite3

def remove_duplicate_coaches():
    """Remove duplicate coaches from the database."""
    conn = sqlite3.connect('instance/academy.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("🧹 Starting duplicate coach removal process...\n")
    
    # Find duplicate coach names
    cur.execute('''
        SELECT LOWER(TRIM(name)) as clean_name, COUNT(*) as count
        FROM coaches
        GROUP BY LOWER(TRIM(name))
        HAVING count > 1
    ''')
    
    duplicate_groups = cur.fetchall()
    total_deleted = 0
    
    if not duplicate_groups:
        print("✅ No duplicate coaches found!")
        conn.close()
        return 0
    
    print(f"Found {len(duplicate_groups)} groups of duplicate coaches:\n")
    
    for group in duplicate_groups:
        clean_name = group[0]
        count = group[1]
        
        # Find all coaches with this name (case-insensitive, trimmed)
        cur.execute('''
            SELECT id, name FROM coaches 
            WHERE LOWER(TRIM(name)) = ?
            ORDER BY id
        ''', (clean_name,))
        
        coaches_with_name = cur.fetchall()
        print(f"\n🔍 '{clean_name}' appears {count} times:")
        
        # Keep the first one, merge others into it
        keeper_id = coaches_with_name[0]['id']
        keeper_name = coaches_with_name[0]['name']
        print(f"   ✅ Keeping: ID {keeper_id} ('{keeper_name}')")
        
        duplicates_to_remove = coaches_with_name[1:]
        
        for dup in duplicates_to_remove:
            dup_id = dup['id']
            dup_name = dup['name']
            print(f"   ❌ Removing: ID {dup_id} ('{dup_name}')")
            
            # Merge coach_salaries (handle conflicts by keeping keeper's salary)
            cur.execute('''
                SELECT id, month, year, salary FROM coach_salaries 
                WHERE coach_id = ?
            ''', (dup_id,))
            dup_salaries = cur.fetchall()
            
            merge_salary_count = 0
            conflict_salary_count = 0
            for sal in dup_salaries:
                # Check if keeper already has salary for this month/year
                cur.execute('''
                    SELECT id FROM coach_salaries 
                    WHERE coach_id = ? AND month = ? AND year = ?
                ''', (keeper_id, sal[1], sal[2]))
                
                if cur.fetchone():
                    # Conflict - keep keeper's salary, delete duplicate
                    conflict_salary_count += 1
                else:
                    # No conflict - merge it
                    cur.execute('''
                        UPDATE coach_salaries SET coach_id = ? 
                        WHERE id = ?
                    ''', (keeper_id, sal[0]))
                    merge_salary_count += 1
            
            if merge_salary_count > 0:
                print(f"      └─ Merged {merge_salary_count} salary entries")
            if conflict_salary_count > 0:
                print(f"      └─ Skipped {conflict_salary_count} conflicting salary entries (kept keeper's)")
            
            # Delete any remaining salaries for the duplicate coach
            cur.execute('DELETE FROM coach_salaries WHERE coach_id = ?', (dup_id,))
            
            # Merge coach_leaves (handle conflicts similarly)
            cur.execute('''
                SELECT id, from_date, to_date FROM coach_leaves 
                WHERE coach_id = ?
            ''', (dup_id,))
            dup_leaves = cur.fetchall()
            
            merge_leaves_count = 0
            conflict_leaves_count = 0
            for leave in dup_leaves:
                # Check if keeper already has leave for this date range
                cur.execute('''
                    SELECT id FROM coach_leaves 
                    WHERE coach_id = ? AND from_date = ? AND to_date = ?
                ''', (keeper_id, leave[1], leave[2]))
                
                if cur.fetchone():
                    # Conflict - skip it
                    conflict_leaves_count += 1
                else:
                    # No conflict - merge it
                    cur.execute('''
                        UPDATE coach_leaves SET coach_id = ? 
                        WHERE id = ?
                    ''', (keeper_id, leave[0]))
                    merge_leaves_count += 1
            
            if merge_leaves_count > 0:
                print(f"      └─ Merged {merge_leaves_count} leave entries")
            if conflict_leaves_count > 0:
                print(f"      └─ Skipped {conflict_leaves_count} conflicting leave entries (kept keeper's)")
            
            # Delete any remaining leaves for the duplicate coach
            cur.execute('DELETE FROM coach_leaves WHERE coach_id = ?', (dup_id,))
            
            # Delete the duplicate coach
            cur.execute('DELETE FROM coaches WHERE id = ?', (dup_id,))
            total_deleted += 1
            print(f"      └─ Deleted duplicate coach")
    
    conn.commit()
    
    print(f"\n{'='*50}")
    print(f"🎉 Duplicate coach removal complete!")
    print(f"   Total duplicate coaches deleted: {total_deleted}")
    print(f"{'='*50}\n")
    
    # Show final coach counts
    cur.execute('SELECT COUNT(*) FROM coaches')
    final_count = cur.fetchone()[0]
    print(f"Final coach count: {final_count}\n")
    
    # Show final breakdown
    cur.execute('''
        SELECT name, COUNT(*) as coach_count
        FROM coaches
        GROUP BY LOWER(TRIM(name))
        ORDER BY name
    ''')
    
    print("Coaches (after deduplication):")
    for row in cur.fetchall():
        print(f"  • {row[0]}")
    
    conn.close()
    return total_deleted

if __name__ == "__main__":
    remove_duplicate_coaches()
