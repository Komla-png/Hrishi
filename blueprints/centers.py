from flask import Blueprint, render_template, redirect, request, flash
from utils import get_db, login_required, create_backup

centers_bp = Blueprint('centers', __name__)


@centers_bp.route('/centers')
@login_required
def centers_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM centers ORDER BY id')
    centers = cur.fetchall()
    conn.close()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return JSON for AJAX/live update
        return {"centers": [dict(id=c[0], name=c[1]) for c in centers]}
    return render_template('centers_list.html', centers=centers)

# Delete center route
@centers_bp.route('/centers/edit/<int:center_id>', methods=['POST'])
@login_required
def edit_center(center_id):
    new_name = request.form.get('new_name', '').strip()
    if not new_name:
        flash('Center name cannot be empty.', 'danger')
        return redirect('/centers')
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id FROM centers WHERE LOWER(TRIM(name)) = LOWER(TRIM(?)) AND id != ?', (new_name, center_id))
    if cur.fetchone():
        conn.close()
        flash('Center name already exists.', 'danger')
        return redirect('/centers')
    cur.execute('UPDATE centers SET name=? WHERE id=?', (new_name, center_id))
    conn.commit()
    conn.close()
    flash('Center name updated successfully!', 'success')
    return redirect('/centers')
@centers_bp.route('/centers/delete/<int:center_id>', methods=['POST'])
@login_required
def delete_center(center_id):
    create_backup('delete_center')
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM monthly_data WHERE center_id=?', (center_id,))
    cur.execute('DELETE FROM coach_salaries WHERE coach_id IN (SELECT id FROM coaches WHERE center_id=?)', (center_id,))
    cur.execute('DELETE FROM coaches WHERE center_id=?', (center_id,))
    cur.execute('DELETE FROM centers WHERE id=?', (center_id,))
    conn.commit()
    conn.close()
    flash('Center deleted successfully!', 'success')
    return redirect('/centers')
