
from flask import Blueprint, render_template, request, jsonify, redirect, session, url_for
from utils import get_db, login_required
from datetime import datetime, date, timedelta

tasks_bp = Blueprint('tasks', __name__)



@tasks_bp.route('/tasks')
@login_required
def tasks_page():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    if month and year:
        return redirect(url_for('tracker.tracker_tasks', month=month, year=year))
    return redirect(url_for('tracker.tracker_tasks'))

@tasks_bp.route('/tasks/api', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def tasks_api():
    conn = get_db()
    cur = conn.cursor()
    user_id = session['user_id']
    if request.method == 'GET':
        cur.execute('SELECT * FROM tasks WHERE user_id=? ORDER BY due_date', (user_id,))
        tasks = [dict(row) for row in cur.fetchall()]
        conn.close()
        return jsonify(tasks)
    elif request.method == 'POST':
        data = request.json
        cur.execute('INSERT INTO tasks (title, description, due_date, status, user_id) VALUES (?, ?, ?, ?, ?)',
                    (data['title'], data.get('description', ''), data.get('due_date'), data.get('status', 'pending'), user_id))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    elif request.method == 'PUT':
        data = request.json
        cur.execute('UPDATE tasks SET title=?, description=?, due_date=?, status=?, updated_at=? WHERE id=? AND user_id=?',
                    (data['title'], data.get('description', ''), data.get('due_date'), data.get('status', 'pending'), datetime.now(), data['id'], user_id))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    elif request.method == 'DELETE':
        data = request.json
        cur.execute('DELETE FROM tasks WHERE id=? AND user_id=?', (data['id'], user_id))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
