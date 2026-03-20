# Task Tracker - Flask Blueprint
# This is a stub for a new blueprint to handle monthly task tracking with recurrence and completion.
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from datetime import datetime, timedelta
import json
import os
from utils import login_required

tracker_bp = Blueprint('tracker', __name__)


# Use a simple in-memory list for tasks (for demo/fix purposes)
TASKS_FILE = 'instance/tasks.json'

def load_tasks():
    try:
        if not os.path.exists(TASKS_FILE):
            return []
        with open(TASKS_FILE, 'r') as f:
            tasks = json.load(f)
            # Remove any task with a field of type Undefined
            tasks = [t for t in tasks if all(type(v).__name__ != 'Undefined' for v in t.values())]
            # Ensure all tasks have required fields and only valid serializable values
            for t in tasks:
                if 'id' not in t or t['id'] is None:
                    t['id'] = str(int(datetime.now().timestamp() * 1000))
                if 'name' not in t or t['name'] is None:
                    t['name'] = ''
                if 'frequency' not in t or t['frequency'] is None:
                    t['frequency'] = 'daily'
                if 'interval' not in t or t['interval'] is None or not isinstance(t['interval'], int):
                    t['interval'] = 1
                if 'completed' not in t or t['completed'] is None or not isinstance(t['completed'], dict):
                    t['completed'] = {}
                if t['frequency'] == 'weekly' and ('weekday' not in t or t['weekday'] is None):
                    t['weekday'] = 0
                if 'deleted_dates' not in t or not isinstance(t['deleted_dates'], list):
                    t['deleted_dates'] = []
                if 'deleted_months' not in t or not isinstance(t['deleted_months'], list):
                    t['deleted_months'] = []
            
            # Remove duplicate tasks (keep first occurrence by id)
            seen_ids = set()
            unique_tasks = []
            for t in tasks:
                if t['id'] not in seen_ids:
                    unique_tasks.append(t)
                    seen_ids.add(t['id'])
            
            return unique_tasks
    except Exception as e:
        print('TASK LOAD ERROR:', e)
        return []

def save_tasks(tasks):
    try:
        # Ensure all tasks have required fields and only valid serializable values
        for t in tasks:
            if 'id' not in t or t['id'] is None:
                t['id'] = str(int(datetime.now().timestamp() * 1000))
            if 'name' not in t or t['name'] is None:
                t['name'] = ''
            if 'frequency' not in t or t['frequency'] is None:
                t['frequency'] = 'daily'
            if 'interval' not in t or t['interval'] is None or not isinstance(t['interval'], int):
                t['interval'] = 1
            if 'completed' not in t or t['completed'] is None or not isinstance(t['completed'], dict):
                t['completed'] = {}
            if t['frequency'] == 'one-time' and ('date' not in t or t['date'] is None):
                t['date'] = ''
            if t['frequency'] == 'weekly' and ('weekday' not in t or t['weekday'] is None):
                t['weekday'] = 0
            if 'deleted_dates' not in t or not isinstance(t['deleted_dates'], list):
                t['deleted_dates'] = []
            if 'deleted_months' not in t or not isinstance(t['deleted_months'], list):
                t['deleted_months'] = []
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks, f, indent=2)
    except Exception as e:
        print('TASK SAVE ERROR:', e)

@tracker_bp.route('/tasks', methods=['GET', 'POST'])
@login_required
def tracker_tasks():
    # Ensure all tasks have required fields and only valid serializable values
    tasks = load_tasks()
    for t in tasks:
        if 'id' not in t or t['id'] is None:
            t['id'] = str(int(datetime.now().timestamp() * 1000))
        if 'name' not in t or t['name'] is None:
            t['name'] = ''
        if 'frequency' not in t or t['frequency'] is None:
            t['frequency'] = 'daily'
        if 'interval' not in t or t['interval'] is None or not isinstance(t['interval'], int):
            t['interval'] = 1
        if 'completed' not in t or t['completed'] is None or not isinstance(t['completed'], dict):
            t['completed'] = {}
        if t['frequency'] == 'one-time' and ('date' not in t or t['date'] is None):
            t['date'] = ''
        if t['frequency'] == 'weekly' and ('weekday' not in t or t['weekday'] is None):
            t['weekday'] = 0
        if 'deleted_dates' not in t or not isinstance(t['deleted_dates'], list):
            t['deleted_dates'] = []
        if 'deleted_months' not in t or not isinstance(t['deleted_months'], list):
            t['deleted_months'] = []

    # Get month and year from query params, default to current month/year
    try:
        month = int(request.args.get('month', datetime.now().month))
        year = int(request.args.get('year', datetime.now().year))
    except Exception:
        month = datetime.now().month
        year = datetime.now().year
    today = datetime(year, month, 1).date()
    # Calculate all days in the selected month
    month_days = []
    d = today
    while d.month == month:
        month_days.append(d)
        d += timedelta(days=1)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            # Add new task - prevent duplicates
            name = request.form['name']
            frequency = request.form['frequency']
            interval = int(request.form.get('interval', 1))
            task_date = request.form.get('date', '')
            task_id = str(int(datetime.now().timestamp() * 1000))
            
            # Check if task with same name and frequency already exists
            existing_task = next((t for t in tasks if t['name'] == name and t['frequency'] == frequency and t.get('date') == task_date), None)
            if not existing_task:
                new_task = {
                    'id': task_id,
                    'name': name,
                    'frequency': frequency,
                    'interval': interval,
                    'completed': {}
                }
                if frequency == 'one-time' and task_date:
                    new_task['date'] = task_date
                if frequency == 'weekly' and task_date:
                    task_date_obj = datetime.strptime(task_date, '%Y-%m-%d').date()
                    new_task['weekday'] = task_date_obj.weekday()
                tasks.append(new_task)
                save_tasks(tasks)
            return redirect(url_for('tracker.tracker_tasks'))
        elif action == 'edit':
            # Edit task
            task_id = request.form['id']
            task_date = request.form.get('date', '')
            for t in tasks:
                if t['id'] == task_id:
                    t['name'] = request.form['name']
                    t['frequency'] = request.form['frequency']
                    t['interval'] = int(request.form.get('interval', 1))
                    if request.form['frequency'] == 'one-time' and task_date:
                        t['date'] = task_date
                    elif 'date' in t:
                        del t['date']
                    if request.form['frequency'] == 'weekly' and task_date:
                        task_date_obj = datetime.strptime(task_date, '%Y-%m-%d').date()
                        t['weekday'] = task_date_obj.weekday()
                    elif 'weekday' in t and request.form['frequency'] != 'weekly':
                        del t['weekday']
            save_tasks(tasks)
            return redirect(url_for('tracker.tracker_tasks'))
        elif action == 'delete':
            # Delete task with scope: 'day', 'month', or 'all'
            task_id = request.form['id']
            delete_scope = request.form.get('delete_scope', 'all')
            delete_date = request.form.get('date', '')
            
            if delete_scope == 'all':
                # Delete entire task
                tasks = [t for t in tasks if t['id'] != task_id]
            elif delete_scope == 'day' and delete_date:
                # Delete task for just this day
                for t in tasks:
                    if t['id'] == task_id:
                        if delete_date not in t.get('deleted_dates', []):
                            t['deleted_dates'].append(delete_date)
            elif delete_scope == 'month' and delete_date:
                # Delete task for entire month (format: YYYY-MM)
                month_key = delete_date[:7]  # Get YYYY-MM from YYYY-MM-DD
                for t in tasks:
                    if t['id'] == task_id:
                        if month_key not in t.get('deleted_months', []):
                            t['deleted_months'].append(month_key)
            save_tasks(tasks)
            return redirect(url_for('tracker.tracker_tasks'))
    return render_template('tasks.html', tasks=tasks, month_days=month_days, today=today, month=month, year=year)

@tracker_bp.route('/tasks/complete', methods=['POST'])
@login_required
def complete_task():
    # Mark a task as complete/incomplete for a date
    data = request.json
    tasks = load_tasks()
    for t in tasks:
        if t['id'] == data['task_id']:
            t['completed'][data['date']] = data['done']
    save_tasks(tasks)
    return jsonify({'success': True})

# Add more endpoints for editing, adding, removing tasks as needed
