from flask import Blueprint, render_template, redirect, request, flash
from utils import get_db, login_required, create_backup

leaves_admin_bp = Blueprint('leaves_admin', __name__)

@leaves_admin_bp.route('/leaves/weekoff')
@login_required
def weekoff_leaves():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, coach_id, from_date, to_date, leave_type, remarks, year FROM coach_leaves WHERE leave_type='Week Off' AND year=2026 ORDER BY from_date")
    leaves = cur.fetchall()
    conn.close()
    return render_template('weekoff_leaves.html', leaves=leaves)

# Delete Week Off leave record
@leaves_admin_bp.route('/leaves/weekoff/delete/<int:leave_id>', methods=['POST'])
@login_required
def delete_weekoff_leave(leave_id):
    create_backup('delete_weekoff_leave')
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM coach_leaves WHERE id=?', (leave_id,))
    conn.commit()
    conn.close()
    flash('Week Off leave record deleted!', 'success')
    return redirect('/leaves/weekoff')
