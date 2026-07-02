from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from functools import wraps
from werkzeug.utils import secure_filename
from app import get_db
from app.blockchain import BlockchainService
from bson import ObjectId
from datetime import datetime
import os

university_bp = Blueprint('university', __name__, url_prefix='/university')
ALLOWED = {'pdf', 'png', 'jpg', 'jpeg'}

def university_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if not current_user.is_authenticated or current_user.role != 'university':
            flash('University access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*a, **kw)
    return dec

def allowed(fn):
    return '.' in fn and fn.rsplit('.', 1)[1].lower() in ALLOWED

@university_bp.route('/dashboard')
@login_required
@university_required
def dashboard():
    db  = get_db()
    uni = db.universities.find_one({'user_id': ObjectId(current_user.id)})
    if not uni:
        flash('University profile not found.', 'danger')
        return redirect(url_for('auth.login'))
    certs = list(db.certificates.find({'university_id': uni['_id']}).sort('issued_at', -1))
    now   = datetime.utcnow()
    stats = {
        'total_issued': len(certs),
        'this_month':   sum(1 for c in certs if c['issued_at'].month == now.month),
        'revoked':      sum(1 for c in certs if c.get('is_revoked')),
    }
    return render_template('university/dashboard.html', uni=uni, certificates=certs, stats=stats,
                           sepolia_live=BlockchainService.is_sepolia_live())

@university_bp.route('/issue', methods=['GET', 'POST'])
@login_required
@university_required
def issue_certificate():
    db  = get_db()
    uni = db.universities.find_one({'user_id': ObjectId(current_user.id)})
    if not uni or not uni.get('is_verified'):
        flash('Your institution must be verified before issuing certificates.', 'warning')
        return redirect(url_for('university.dashboard'))

    if request.method == 'POST':
        student_email   = request.form.get('student_email', '').strip().lower()
        degree          = request.form.get('degree', '')
        major           = request.form.get('major', '')
        graduation_year = request.form.get('graduation_year', '')
        cgpa            = request.form.get('cgpa', '')

        student_user = db.users.find_one({'email': student_email, 'role': 'student'})
        if not student_user:
            flash('No student found with that email.', 'danger')
            return render_template('university/issue.html', uni=uni)
        student = db.students.find_one({'user_id': student_user['_id']})
        if not student:
            flash('Student profile not found.', 'danger')
            return render_template('university/issue.html', uni=uni)

        file_path = None
        f = request.files.get('certificate_file')
        if f and f.filename and allowed(f.filename):
            ext      = f.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{student['student_id']}_{int(datetime.utcnow().timestamp())}.{ext}")
            f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            file_path = filename

        cert_data = {
            'student_name': student_user['name'], 'student_email': student_email,
            'degree': degree, 'major': major, 'graduation_year': graduation_year,
            'cgpa': cgpa, 'institution': uni['institution_name'],
        }
        cert_hash = BlockchainService.generate_certificate_hash(cert_data)

        if db.certificates.find_one({'cert_hash': cert_hash}):
            flash('This certificate already exists on the blockchain.', 'warning')
            return render_template('university/issue.html', uni=uni)

        issuer_wallet = uni.get('wallet_address') or BlockchainService.generate_wallet_address()
        cert_id = BlockchainService.generate_certificate_id()

        bc = BlockchainService.record_certificate(
            db, cert_hash, cert_id, student_user['name'],
            degree, uni['institution_name'], issuer_wallet
        )

        db.certificates.insert_one({
            'certificate_id': cert_id, 'student_id': student['_id'],
            'university_id': uni['_id'], 'student_name': student_user['name'],
            'degree': degree, 'major': major, 'graduation_year': graduation_year,
            'cgpa': cgpa, 'file_path': file_path, 'cert_hash': cert_hash,
            'tx_hash': bc.get('tx_hash'), 'block_number': bc.get('block_number'),
            'issuer_wallet': issuer_wallet, 'blockchain_mode': bc.get('mode', 'local'),
            'is_revoked': False, 'issued_at': datetime.utcnow(),
        })

        mode_label = '🌐 Sepolia Testnet' if bc.get('mode') == 'sepolia' else '🔗 Local Chain'
        flash(f'Certificate issued on {mode_label}! TX: {bc.get("tx_hash","")[:20]}...', 'success')
        return redirect(url_for('university.certificate_detail', cert_id=cert_id))

    return render_template('university/issue.html', uni=uni)

@university_bp.route('/certificate/<cert_id>')
@login_required
@university_required
def certificate_detail(cert_id):
    db   = get_db()
    cert = db.certificates.find_one({'certificate_id': cert_id})
    if not cert:
        flash('Certificate not found.', 'danger')
        return redirect(url_for('university.dashboard'))
    block = db.blockchain_records.find_one({'certificate_id': cert_id})
    return render_template('university/cert_detail.html', cert=cert, block=block)

@university_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@university_required
def profile():
    db  = get_db()
    uni = db.universities.find_one({'user_id': ObjectId(current_user.id)})
    if request.method == 'POST':
        updates = {
            'institution_name': request.form.get('institution_name', uni['institution_name']),
            'address': request.form.get('address', ''),
            'website': request.form.get('website', ''),
        }
        if not uni.get('wallet_address'):
            updates['wallet_address'] = BlockchainService.generate_wallet_address()
        db.universities.update_one({'_id': uni['_id']}, {'$set': updates})
        flash('Profile updated!', 'success')
        uni = db.universities.find_one({'user_id': ObjectId(current_user.id)})
    return render_template('university/profile.html', uni=uni)
