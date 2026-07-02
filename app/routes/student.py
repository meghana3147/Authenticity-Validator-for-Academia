from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user
from functools import wraps
from app import get_db
from app.blockchain import BlockchainService
from bson import ObjectId
import qrcode, io, base64

student_bp = Blueprint('student', __name__, url_prefix='/student')

def student_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('Student access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*a, **kw)
    return dec

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    db      = get_db()
    student = db.students.find_one({'user_id': ObjectId(current_user.id)})
    certs   = list(db.certificates.find({'student_id': student['_id']}).sort('issued_at', -1)) if student else []
    for c in certs:
        uni = db.universities.find_one({'_id': c.get('university_id')})
        c['issuer'] = uni
    return render_template('student/dashboard.html', student=student, certificates=certs)

@student_bp.route('/certificate/<cert_id>')
@login_required
@student_required
def certificate_detail(cert_id):
    db      = get_db()
    student = db.students.find_one({'user_id': ObjectId(current_user.id)})
    cert    = db.certificates.find_one({'certificate_id': cert_id, 'student_id': student['_id']})
    if not cert:
        flash('Certificate not found.', 'danger')
        return redirect(url_for('student.dashboard'))
    block = db.blockchain_records.find_one({'certificate_id': cert_id})
    uni   = db.universities.find_one({'_id': cert.get('university_id')})

    qr_url = BlockchainService.generate_qr_url(cert['certificate_id'], cert['cert_hash'], request.host_url)
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO(); img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template('student/cert_detail.html', cert=cert, block=block,
                           uni=uni, qr_code=qr_b64, qr_url=qr_url)

@student_bp.route('/download/<cert_id>')
@login_required
@student_required
def download_certificate(cert_id):
    db      = get_db()
    student = db.students.find_one({'user_id': ObjectId(current_user.id)})
    cert    = db.certificates.find_one({'certificate_id': cert_id, 'student_id': student['_id']})
    if cert and cert.get('file_path'):
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], cert['file_path'],
                                   as_attachment=True, download_name=cert['file_path'])
    flash('No file attached to this certificate.', 'warning')
    return redirect(url_for('student.certificate_detail', cert_id=cert_id))
