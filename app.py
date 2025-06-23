# app.py
import os
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

# --- CẤU HÌNH DATABASE ---
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise RuntimeError("FATAL ERROR: DATABASE_URL environment variable is not set.")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-very-secret-key-that-you-should-change')

db = SQLAlchemy(app)

# --- MÔ HÌNH DATABASE ---
class LicenseKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key_string = db.Column(db.String(100), unique=True, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- GIAO DIỆN QUẢN TRỊ ADMIN ---
ADMIN_TEMPLATE = """
<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Bảng Điều Khiển Key</title>
<style>:root{--bg-color:#1a1a2e;--card-color:#16213e;--primary-color:#0f3460;--accent-color:#e94560;--text-color:#e0e0e0}body{font-family:-apple-system,sans-serif;background-color:var(--bg-color);color:var(--text-color);margin:0;padding:1rem}.container{max-width:1200px;margin:auto}h1,h2{color:var(--accent-color);text-align:center}.card{background-color:var(--card-color);padding:1.5rem;border-radius:8px;margin-bottom:2rem}table{width:100%;border-collapse:collapse;margin-top:1.5rem}th,td{padding:12px 15px;text-align:left;border-bottom:1px solid var(--primary-color)}th{background-color:var(--primary-color)}form{display:flex;flex-wrap:wrap;gap:1rem;align-items:flex-end}input,button{background-color:var(--bg-color);border:1px solid var(--primary-color);color:var(--text-color);padding:10px;border-radius:8px;font-size:1rem}button{background-color:var(--accent-color);cursor:pointer;font-weight:bold}</style>
</head><body><div class="container"><h1>Bảng Điều Khiển Quản Lý Key</h1><div class="card"><h2>Tạo Key Mới</h2>
<form action="{{ url_for('admin_add_key') }}" method="POST">
    <input type="text" name="key_string" placeholder="Chuỗi Key (để trống để tự tạo)">
    <input type="number" name="duration_days" value="30" required>
    <input type="text" name="notes" placeholder="Ghi chú">
    <button type="submit">Tạo Key</button></form></div>
<div class="card"><h2>Danh Sách Key</h2><div style="overflow-x:auto"><table><thead><tr><th>Key</th><th>Ngày Hết Hạn</th><th>Ghi Chú</th><th>Hành Động</th></tr></thead><tbody>
{% for key in keys %}<tr><td>{{ key.key_string }}</td>
<td><form action="{{ url_for('admin_edit_key', key_id=key.id) }}" method="POST" style="display:inline-flex;gap:5px;"><input type="date" name="expiry_date" value="{{ key.expiry_date.strftime('%Y-%m-%d') }}"><button type="submit">Lưu</button></form></td>
<td>{{ key.notes }}</td>
<td><form action="{{ url_for('admin_delete_key', key_id=key.id) }}" method="POST" onsubmit="return confirm('Xóa key này?');"><button type="submit">Xóa</button></form></td></tr>
{% else %}<tr><td colspan="4" style="text-align:center;">Chưa có key nào.</td></tr>{% endfor %}
</tbody></table></div></div></div></body></html>
"""

@app.route('/admin')
def admin_panel():
    keys = LicenseKey.query.order_by(LicenseKey.created_at.desc()).all()
    return render_template_string(ADMIN_TEMPLATE, keys=keys)

@app.route('/admin/add', methods=['POST'])
def admin_add_key():
    key_string = request.form.get('key_string')
    if not key_string:
        key_string = f"PRO-{uuid.uuid4().hex[:8].upper()}"
    duration = int(request.form.get('duration_days', 30))
    expiry = datetime.utcnow().date() + timedelta(days=duration)
    notes = request.form.get('notes')
    new_key = LicenseKey(key_string=key_string, expiry_date=expiry, notes=notes)
    db.session.add(new_key)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/edit/<int:key_id>', methods=['POST'])
def admin_edit_key(key_id):
    key = LicenseKey.query.get_or_404(key_id)
    new_expiry_str = request.form.get('expiry_date')
    key.expiry_date = datetime.strptime(new_expiry_str, '%Y-%m-%d').date()
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete/<int:key_id>', methods=['POST'])
def admin_delete_key(key_id):
    key = LicenseKey.query.get_or_404(key_id)
    db.session.delete(key)
    db.session.commit()
    return redirect(url_for('admin_panel'))

# --- API ENDPOINT CHO TWEAK ---
@app.route('/verify_key', methods=['POST'])
def verify_key():
    data = request.get_json()
    if not data or 'key' not in data:
        return jsonify({"status": "error", "message": "Invalid request"}), 400

    user_key = data['key']
    key_entry = LicenseKey.query.filter_by(key_string=user_key).first()

    if key_entry and key_entry.expiry_date >= datetime.utcnow().date():
        return jsonify({
            "status": "success",
            "key": user_key,
            "expiry_date": key_entry.expiry_date.strftime('%Y-%m-%d')
        })
    else:
        message = "Key has expired." if key_entry else "Invalid or unknown key."
        return jsonify({"status": "failure", "message": message})

# Lệnh này sẽ tự động tạo bảng database khi ứng dụng khởi động
with app.app_context():
    db.create_all()
