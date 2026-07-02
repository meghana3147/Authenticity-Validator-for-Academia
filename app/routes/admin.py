# -------------------- IMPORTS --------------------

# Blueprint → used to organize routes into modules (admin part of app)
from flask import Blueprint, render_template, redirect, url_for, flash, request

# login_required → ensures user must be logged in
# current_user → gives info about logged-in user
from flask_login import login_required, current_user

# wraps → used when creating custom decorators
from functools import wraps

# Function to access MongoDB
from app import get_db

# Used to convert string → MongoDB ObjectId
from bson import ObjectId

# For timestamps (not heavily used here but imported)
from datetime import datetime


# -------------------- CREATE BLUEPRINT --------------------

# All routes here will start with /admin
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# -------------------- CUSTOM ADMIN CHECK --------------------

def admin_required(f):
    """
    Custom decorator to allow ONLY admin users

    Works like:
    @admin_required
    def some_route():
        ...
    """

    @wraps(f)
    def dec(*a, **kw):

        # Check:
        # 1. user is logged in
        # 2. user role is 'admin'
        if not current_user.is_authenticated or current_user.role != 'admin':

            # Show error message
            flash('Admin access required.', 'danger')

            # Redirect to login page
            return redirect(url_for('auth.login'))

        # If admin → allow access
        return f(*a, **kw)

    return dec


# -------------------- ADMIN DASHBOARD --------------------

@admin_bp.route('/dashboard')
@login_required       # must be logged in
@admin_required       # must be admin
def dashboard():

    db = get_db()  # get MongoDB connection

    # -------------------- STATS --------------------

    # Count various things from database
    stats = {
        'total_users': db.users.count_documents({}),

        # Universities waiting for approval
        'pending_universities': db.universities.count_documents({'is_verified': False}),

        'total_certificates': db.certificates.count_documents({}),
        'total_blocks': db.blockchain_records.count_documents({}),
        'total_verifications': db.verification_logs.count_documents({}),

        # Only successful verifications
        'authentic_verifications': db.verification_logs.count_documents({'result': 'authentic'}),
    }

    # -------------------- RECENT DATA --------------------

    # Get latest 5 certificates (newest first)
    recent_certs = list(
        db.certificates.find().sort('issued_at', -1).limit(5)
    )

    # Get latest 5 verification logs
    recent_logs = list(
        db.verification_logs.find().sort('timestamp', -1).limit(5)
    )

    # Get universities waiting for approval
    pending_unis = list(
        db.universities.find({'is_verified': False})
    )

    # Attach user info to each university
    for u in pending_unis:
        u['user'] = db.users.find_one({'_id': u['user_id']})

    # Attach issuer info to each certificate
    for c in recent_certs:
        uni = db.universities.find_one({'_id': c.get('university_id')})
        c['issuer'] = uni

    # Render dashboard page with all data
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_certs=recent_certs,
        recent_logs=recent_logs,
        pending_unis=pending_unis
    )


# -------------------- VIEW ALL INSTITUTIONS --------------------

@admin_bp.route('/institutions')
@login_required
@admin_required
def institutions():

    db = get_db()

    # Get all universities
    unis = list(db.universities.find())

    # Attach user info to each
    for u in unis:
        u['user'] = db.users.find_one({'_id': u['user_id']})

    return render_template('admin/institutions.html', universities=unis)


# -------------------- APPROVE UNIVERSITY --------------------

@admin_bp.route('/approve/<uni_id>', methods=['POST'])
@login_required
@admin_required
def approve_university(uni_id):

    db = get_db()

    # Find university by ID
    uni = db.universities.find_one({'_id': ObjectId(uni_id)})

    if uni:
        # Mark university as verified
        db.universities.update_one(
            {'_id': ObjectId(uni_id)},
            {'$set': {'is_verified': True}}
        )

        # Also approve the linked user account
        db.users.update_one(
            {'_id': uni['user_id']},
            {'$set': {'is_approved': True}}
        )

        flash('Institution approved!', 'success')

    return redirect(url_for('admin.institutions'))


# -------------------- REVOKE UNIVERSITY --------------------

@admin_bp.route('/revoke-uni/<uni_id>', methods=['POST'])
@login_required
@admin_required
def revoke_university(uni_id):

    db = get_db()

    uni = db.universities.find_one({'_id': ObjectId(uni_id)})

    if uni:
        # Remove verification
        db.universities.update_one(
            {'_id': ObjectId(uni_id)},
            {'$set': {'is_verified': False}}
        )

        # Also mark user as not approved
        db.users.update_one(
            {'_id': uni['user_id']},
            {'$set': {'is_approved': False}}
        )

        flash('Institution revoked.', 'warning')

    return redirect(url_for('admin.institutions'))


# -------------------- VIEW ALL USERS --------------------

@admin_bp.route('/users')
@login_required
@admin_required
def users():

    db = get_db()

    # Get all users sorted by newest first
    all_users = list(
        db.users.find().sort('created_at', -1)
    )

    return render_template('admin/users.html', users=all_users)


# -------------------- BLOCKCHAIN EXPLORER --------------------

@admin_bp.route('/blockchain')
@login_required
@admin_required
def blockchain_explorer():

    db = get_db()

    # Get blockchain records (latest blocks first)
    blocks = list(
        db.blockchain_records.find().sort('block_number', -1)
    )

    return render_template('admin/blockchain.html', blocks=blocks)


# -------------------- VIEW CERTIFICATES --------------------

@admin_bp.route('/certificates')
@login_required
@admin_required
def certificates():

    db = get_db()

    # Get all certificates (latest first)
    certs = list(
        db.certificates.find().sort('issued_at', -1)
    )

    # Attach university info
    for c in certs:
        uni = db.universities.find_one({'_id': c.get('university_id')})
        c['issuer'] = uni

    return render_template('admin/certificates.html', certificates=certs)


# -------------------- REVOKE CERTIFICATE --------------------

@admin_bp.route('/revoke-cert/<cert_id>', methods=['POST'])
@login_required
@admin_required
def revoke_certificate(cert_id):

    db = get_db()

    # Mark certificate as revoked
    db.certificates.update_one(
        {'certificate_id': cert_id},
        {'$set': {'is_revoked': True}}
    )

    flash('Certificate revoked.', 'warning')

    return redirect(url_for('admin.certificates'))


# -------------------- VIEW VERIFICATION LOGS --------------------

@admin_bp.route('/logs')
@login_required
@admin_required
def logs():

    db = get_db()

    # Get all verification logs (latest first)
    logs = list(
        db.verification_logs.find().sort('timestamp', -1)
    )

    return render_template('admin/logs.html', logs=logs)