import sqlite3


def merge_center_monthly_data(cur, keeper_center_id, duplicate_center_id):
    cur.execute(
        """
        SELECT id, month, year, revenue, target
        FROM monthly_data
        WHERE center_id=?
        """,
        (duplicate_center_id,),
    )
    duplicate_rows = cur.fetchall()

    for row_id, month, year, dup_revenue, dup_target in duplicate_rows:
        cur.execute(
            """
            SELECT id, revenue, target
            FROM monthly_data
            WHERE center_id=? AND month=? AND year=?
            """,
            (keeper_center_id, month, year),
        )
        keeper_row = cur.fetchone()

        if keeper_row:
            keeper_row_id, keeper_revenue, keeper_target = keeper_row
            merged_revenue = max(float(keeper_revenue or 0), float(dup_revenue or 0))
            merged_target = max(float(keeper_target or 0), float(dup_target or 0))
            cur.execute(
                "UPDATE monthly_data SET revenue=?, target=? WHERE id=?",
                (merged_revenue, merged_target, keeper_row_id),
            )
            cur.execute("DELETE FROM monthly_data WHERE id=?", (row_id,))
        else:
            cur.execute(
                "UPDATE monthly_data SET center_id=? WHERE id=?",
                (keeper_center_id, row_id),
            )


def merge_coach_data(cur, keeper_coach_id, duplicate_coach_id):
    cur.execute(
        """
        SELECT id, month, year, salary
        FROM coach_salaries
        WHERE coach_id=?
        """,
        (duplicate_coach_id,),
    )
    salary_rows = cur.fetchall()

    for salary_id, month, year, salary in salary_rows:
        cur.execute(
            """
            SELECT id, salary FROM coach_salaries
            WHERE coach_id=? AND month=? AND year=?
            """,
            (keeper_coach_id, month, year),
        )
        keeper_salary = cur.fetchone()
        if keeper_salary:
            keeper_salary_id, keeper_salary_value = keeper_salary
            merged_salary = max(float(keeper_salary_value or 0), float(salary or 0))
            cur.execute("UPDATE coach_salaries SET salary=? WHERE id=?", (merged_salary, keeper_salary_id))
            cur.execute("DELETE FROM coach_salaries WHERE id=?", (salary_id,))
        else:
            cur.execute("UPDATE coach_salaries SET coach_id=? WHERE id=?", (keeper_coach_id, salary_id))

    cur.execute(
        """
        SELECT id, from_date, to_date
        FROM coach_leaves
        WHERE coach_id=?
        """,
        (duplicate_coach_id,),
    )
    leave_rows = cur.fetchall()

    for leave_id, from_date, to_date in leave_rows:
        cur.execute(
            """
            SELECT id FROM coach_leaves
            WHERE coach_id=? AND from_date=? AND to_date=?
            """,
            (keeper_coach_id, from_date, to_date),
        )
        if cur.fetchone():
            cur.execute("DELETE FROM coach_leaves WHERE id=?", (leave_id,))
        else:
            cur.execute("UPDATE coach_leaves SET coach_id=? WHERE id=?", (keeper_coach_id, leave_id))

    cur.execute("DELETE FROM coaches WHERE id=?", (duplicate_coach_id,))


def merge_center_coaches(cur, keeper_center_id, duplicate_center_id):
    cur.execute("SELECT id, name FROM coaches WHERE center_id=? ORDER BY id", (duplicate_center_id,))
    duplicate_coaches = cur.fetchall()

    for duplicate_coach_id, duplicate_coach_name in duplicate_coaches:
        normalized_name = (duplicate_coach_name or "").strip().lower()
        cur.execute("SELECT id FROM coaches WHERE center_id=?", (keeper_center_id,))
        keeper_candidates = cur.fetchall()

        keeper_coach_id = None
        for (candidate_id,) in keeper_candidates:
            cur.execute("SELECT name FROM coaches WHERE id=?", (candidate_id,))
            candidate_name = (cur.fetchone()[0] or "").strip().lower()
            if candidate_name == normalized_name:
                keeper_coach_id = candidate_id
                break

        if keeper_coach_id:
            merge_coach_data(cur, keeper_coach_id, duplicate_coach_id)
        else:
            cur.execute("UPDATE coaches SET center_id=? WHERE id=?", (keeper_center_id, duplicate_coach_id))


def remove_duplicate_centers():
    conn = sqlite3.connect("instance/academy.db")
    cur = conn.cursor()

    cur.execute(
        """
        SELECT LOWER(TRIM(name)) AS clean_name, COUNT(*) as count
        FROM centers
        GROUP BY LOWER(TRIM(name))
        HAVING count > 1
        """
    )
    duplicate_groups = cur.fetchall()

    if not duplicate_groups:
        print("No duplicate centers found.")
        conn.close()
        return

    print(f"Found {len(duplicate_groups)} duplicate center groups")

    deleted_centers = 0
    for clean_name, count in duplicate_groups:
        cur.execute(
            """
            SELECT id, name
            FROM centers
            WHERE LOWER(TRIM(name))=?
            ORDER BY id
            """,
            (clean_name,),
        )
        centers = cur.fetchall()
        keeper_center_id, keeper_name = centers[0]
        duplicates = centers[1:]

        print(f"Merging center '{keeper_name}' ({count} entries): keeping ID {keeper_center_id}")

        for duplicate_center_id, duplicate_name in duplicates:
            merge_center_monthly_data(cur, keeper_center_id, duplicate_center_id)
            merge_center_coaches(cur, keeper_center_id, duplicate_center_id)
            cur.execute("DELETE FROM centers WHERE id=?", (duplicate_center_id,))
            deleted_centers += 1
            print(f"  Removed duplicate center ID {duplicate_center_id} ({duplicate_name})")

    conn.commit()

    cur.execute(
        """
        SELECT LOWER(TRIM(name)), COUNT(*)
        FROM centers
        GROUP BY LOWER(TRIM(name))
        HAVING COUNT(*) > 1
        """
    )
    still_dupes = cur.fetchall()

    print(f"Done. Deleted {deleted_centers} duplicate centers.")
    print(f"Remaining duplicate groups: {len(still_dupes)}")

    conn.close()


if __name__ == "__main__":
    remove_duplicate_centers()
