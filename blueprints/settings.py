"""Settings blueprint - User account settings, password change, backup management."""

from flask import Blueprint, render_template, request, redirect, session, flash, send_file, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
import shutil
import time

from utils import get_db, login_required, sanitize_input, create_backup, list_backups, restore_backup, DB_PATH

settings_bp = Blueprint('settings', __name__)


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User settings page - change username and password."""
    conn = None
    message = None
    error = None
    current_username = ""
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Get current user info
        user_id = session.get("user_id")
        cur.execute("SELECT username FROM users WHERE id=?", (user_id,))
        user = cur.fetchone()
        current_username = user["username"] if user else ""
        
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "change_username":
                new_username = sanitize_input(request.form.get("new_username", ""), 50)
                current_password = request.form.get("current_password", "")
                
                if not new_username or not current_password:
                    error = "Please fill in all fields"
                else:
                    # Verify current password
                    cur.execute("SELECT password_hash FROM users WHERE id=?", (user_id,))
                    user_data = cur.fetchone()
                    
                    if user_data and check_password_hash(user_data["password_hash"], current_password):
                        # Check if username already exists
                        cur.execute("SELECT id FROM users WHERE username=? AND id!=?", (new_username, user_id))
                        if cur.fetchone():
                            error = "Username already taken"
                        else:
                            try:
                                cur.execute("UPDATE users SET username=? WHERE id=?", (new_username, user_id))
                                conn.commit()
                                session["user"] = new_username
                                current_username = new_username
                                message = "Username updated successfully!"
                            except Exception as e:
                                conn.rollback()
                                error = f"Failed to update username: {str(e)}"
                    else:
                        error = "Current password is incorrect"
            
            elif action == "change_password":
                current_password = request.form.get("current_password_pwd", "")
                new_password = request.form.get("new_password", "")
                confirm_password = request.form.get("confirm_password", "")
                
                if not current_password or not new_password or not confirm_password:
                    error = "Please fill in all password fields"
                elif new_password != confirm_password:
                    error = "New passwords do not match"
                elif len(new_password) < 4:
                    error = "Password must be at least 4 characters"
                else:
                    # Verify current password
                    cur.execute("SELECT password_hash FROM users WHERE id=?", (user_id,))
                    user_data = cur.fetchone()
                    
                    if user_data and check_password_hash(user_data["password_hash"], current_password):
                        try:
                            new_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
                            cur.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))
                            conn.commit()
                            message = "Password updated successfully!"
                        except Exception as e:
                            conn.rollback()
                            error = f"Failed to update password: {str(e)}"
                    else:
                        error = "Current password is incorrect"
    
    except Exception as e:
        error = f"Database error: {str(e)}"
    
    finally:
        if conn:
            conn.close()
    
    return render_template(
        "settings.html",
        current_username=current_username,
        message=message,
        error=error
    )


# ================= BACKUP MANAGEMENT ROUTES =================

@settings_bp.route("/backups")
@login_required
def backups():
    """View all available database backups."""
    backup_list = list_backups()
    return render_template("backups.html", backups=backup_list)


@settings_bp.route("/backups/create", methods=["POST"])
@login_required
def create_backup_route():
    """Create a manual backup."""
    reason = sanitize_input(request.form.get("reason", "manual"), 50)
    reason = reason.replace(" ", "_").replace("/", "_")  # Clean filename
    backup_path = create_backup(reason)
    
    if backup_path:
        flash(f"Backup created successfully: {os.path.basename(backup_path)}", "success")
    else:
        flash("Failed to create backup", "error")
    
    return redirect("/backups")


@settings_bp.route("/backups/restore/<path:filename>", methods=["POST"])
@login_required
def restore_backup_route(filename):
    """Restore database from a backup file."""
    backup_path = os.path.join("backups", filename)
    
    if restore_backup(backup_path):
        flash(f"Database restored from {filename}. Please restart the application.", "success")
    else:
        flash("Failed to restore backup", "error")
    
    return redirect("/backups")


@settings_bp.route("/backups/download/<path:filename>")
@login_required
def download_backup(filename):
    """Download a backup file."""
    backup_path = os.path.join("backups", filename)
    
    if os.path.exists(backup_path):
        return send_file(
            os.path.abspath(backup_path),
            as_attachment=True,
            download_name=filename
        )
    else:
        flash("Backup file not found", "error")
        return redirect("/backups")


@settings_bp.route("/backups/upload-restore", methods=["POST"])
@login_required
def upload_restore_backup_route():
    """Upload a .db file and restore it as the active database."""
    uploaded_file = request.files.get("db_file")
    if not uploaded_file or not uploaded_file.filename:
        flash("Please select a backup file (.db)", "error")
        return redirect("/backups")

    filename = secure_filename(uploaded_file.filename)
    if not filename.lower().endswith(".db"):
        flash("Invalid file type. Please upload a .db file", "error")
        return redirect("/backups")

    uploads_dir = os.path.join("instance", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    temp_path = os.path.join(uploads_dir, f"restore_{int(time.time())}_{filename}")

    try:
        uploaded_file.save(temp_path)

        # Validate SQLite file header before restoring.
        with open(temp_path, "rb") as f:
            header = f.read(16)
        if header != b"SQLite format 3\x00":
            flash("Uploaded file is not a valid SQLite database", "error")
            return redirect("/backups")

        # Backup current DB before replacing.
        create_backup("before_upload_restore")

        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        shutil.copy2(temp_path, DB_PATH)

        # Remove WAL/SHM files to avoid mismatch with replaced DB.
        for sidecar in (DB_PATH + "-wal", DB_PATH + "-shm"):
            if os.path.exists(sidecar):
                os.remove(sidecar)

        flash("Database restored successfully from uploaded backup", "success")
    except Exception as e:
        flash(f"Failed to restore uploaded backup: {str(e)}", "error")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

    return redirect("/backups")
