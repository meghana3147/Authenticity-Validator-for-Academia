from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import get_db
from app.blockchain import BlockchainService
from datetime import datetime
import hashlib

employer_bp = Blueprint('employer', __name__, url_prefix='/employer')

def employer_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if not current_user.is_authenticated or current_user.role != 'employer':
            flash('Employer access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*a, **kw)
    return dec

@employer_bp.route('/dashboard')
@login_required
@employer_required
def dashboard():
    db   = get_db()
    logs = list(db.verification_logs.find({'verifier_email': current_user.email}).sort('timestamp', -1).limit(15))
    stats = {
        'total':     len(logs),
        'authentic': sum(1 for l in logs if l['result'] == 'authentic'),
        'failed':    sum(1 for l in logs if l['result'] != 'authentic'),
    }
    return render_template('employer/dashboard.html', logs=logs, stats=stats)

@employer_bp.route('/verify', methods=['GET', 'POST'])
@login_required
@employer_required
def verify():
    db = get_db()
    result = None; cert = None; block = None; chain_data = None

    if request.method == 'POST':
        method = request.form.get('method')
        outcome = 'not_found'

        if method == 'cert_id':
            cert = db.certificates.find_one({'certificate_id': request.form.get('cert_id','').strip()})
        elif method == 'hash':
            cert = db.certificates.find_one({'cert_hash': request.form.get('cert_hash','').strip()})
        elif method == 'upload':
            f = request.files.get('cert_file')
            if f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                cert = db.certificates.find_one({'cert_hash': file_hash})

        if cert:
            block = db.blockchain_records.find_one({'certificate_id': cert['certificate_id']})
            if cert.get('is_revoked'):
                outcome = 'revoked'
            else:
                outcome = 'authentic'
                # cross-check with Sepolia if live
                if BlockchainService.is_sepolia_live():
                    try:
                        chain_data = BlockchainService.verify_on_sepolia(cert['cert_hash'])
                        if chain_data and chain_data.get('isRevoked'):
                            outcome = 'revoked'
                    except Exception:
                        pass

        result = outcome
        db.verification_logs.insert_one({
            'certificate_id':  str(cert['_id']) if cert else None,
            'cert_ref':        cert['certificate_id'] if cert else None,
            'verifier_email':  current_user.email,
            'verifier_name':   current_user.name,
            'result':          outcome,
            'ip_address':      request.remote_addr,
            'timestamp':       datetime.utcnow(),
        })

    return render_template('employer/verify.html', result=result, cert=cert,
                           block=block, chain_data=chain_data)
