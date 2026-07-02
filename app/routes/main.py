from flask import Blueprint, render_template, request
from app import get_db
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    db = get_db()
    stats = {
        'certificates': db.certificates.count_documents({}),
        'institutions': db.universities.count_documents({'is_verified': True}),
        'verifications':db.verification_logs.count_documents({}),
    }
    return render_template('main/index.html', stats=stats)

@main_bp.route('/verify')
def public_verify():
    db      = get_db()
    cert_id = request.args.get('cert_id', '')
    h_prefix= request.args.get('h', '')
    result  = None; cert = None; block = None

    if cert_id:
        cert = db.certificates.find_one({'certificate_id': cert_id})
        if cert:
            if h_prefix and not cert['cert_hash'].startswith(h_prefix):
                result = 'tampered'
            elif cert.get('is_revoked'):
                result = 'revoked'
            else:
                result = 'authentic'
            block = db.blockchain_records.find_one({'certificate_id': cert_id})
        else:
            result = 'not_found'
        db.verification_logs.insert_one({
            'certificate_id': str(cert['_id']) if cert else None,
            'cert_ref': cert_id,
            'verifier_email': 'public', 'verifier_name': 'Public',
            'result': result, 'ip_address': request.remote_addr,
            'timestamp': datetime.utcnow(),
        })

    return render_template('main/verify.html', result=result, cert=cert, block=block, cert_id=cert_id)

@main_bp.route('/explorer')
def blockchain_explorer():
    db     = get_db()
    blocks = list(db.blockchain_records.find().sort('block_number', -1).limit(30))
    return render_template('main/explorer.html', blocks=blocks)
