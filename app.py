#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Now import config (which will use the environment variables)
from config import *
import csv
import io
import time
import random
import subprocess
import tempfile
import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, Response
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Optional
from ldap3 import Server, Connection, ALL, SUBTREE, MODIFY_REPLACE, MODIFY_DELETE

# ============================================================================
# PSUTIL CHECK - FORCE IMPORT
# ============================================================================
PSUTIL_AVAILABLE = False

# Force import psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
    print("✅ psutil loaded successfully!")
    
    # Test if it actually works
    test_cpu = psutil.cpu_percent(interval=0.1)
    test_memory = psutil.virtual_memory().percent
    test_disk = psutil.disk_usage('/').percent
    print(f"✅ psutil test passed! CPU: {test_cpu}%, Memory: {test_memory}%, Disk: {test_disk}%")
    
except ImportError as e:
    PSUTIL_AVAILABLE = False
    print(f"❌ psutil import error: {e}")
    print("⚠️ Please run: pip install psutil")
    
except Exception as e:
    PSUTIL_AVAILABLE = False
    print(f"❌ psutil error: {e}")
    print("⚠️ Please reinstall psutil: pip install --force-reinstall psutil")

# ============================================================================
# Flask App
# ============================================================================
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
Bootstrap(app)

# ============================================================================
# System Metrics Function - REAL METRICS
# ============================================================================
def get_system_metrics():
    """Get REAL system metrics from psutil"""
    metrics = {
        'cpu': 0,
        'memory': 0,
        'disk': 0,
        'uptime': 'N/A',
        'status': 'success'
    }
    
    # IMPORTANT: Check the global flag
    if PSUTIL_AVAILABLE:
        try:
            # Get REAL CPU usage
            metrics['cpu'] = psutil.cpu_percent(interval=0.5)
            
            # Get REAL memory usage
            mem = psutil.virtual_memory()
            metrics['memory'] = mem.percent
            
            # Get REAL disk usage
            disk = psutil.disk_usage('/')
            metrics['disk'] = disk.percent
            
            # Get REAL uptime
            uptime_seconds = time.time() - psutil.boot_time()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            metrics['uptime'] = f"{days}d {hours}h" if days > 0 else f"{hours}h"
            metrics['status'] = 'success'
            
            print(f"📊 REAL Metrics: CPU={metrics['cpu']}%, Memory={metrics['memory']}%, Disk={metrics['disk']}%")
            
        except Exception as e:
            print(f"⚠️ Error getting metrics: {e}")
            # Fallback to simulated
            metrics['cpu'] = random.randint(15, 60)
            metrics['memory'] = random.randint(40, 80)
            metrics['disk'] = random.randint(30, 70)
            metrics['uptime'] = "2d 14h"
            metrics['status'] = 'simulated'
    else:
        # psutil not available - use simulated data
        print("⚠️ Using simulated metrics (psutil not available)")
        metrics['cpu'] = random.randint(15, 60)
        metrics['memory'] = random.randint(40, 80)
        metrics['disk'] = random.randint(30, 70)
        metrics['uptime'] = "2d 14h"
        metrics['status'] = 'simulated'
    
    return metrics

# ============================================================================
# Context Processors
# ============================================================================
@app.context_processor
def branding_processor():
    """Make branding variables and user count available in all templates"""
    try:
        total_count = get_user_count()
    except Exception as e:
        print(f"Error getting user count: {e}")
        total_count = 0
    
    return {
        'APP_NAME': APP_NAME,
        'APP_SHORT_NAME': APP_SHORT_NAME,
        'APP_VERSION': APP_VERSION,
        'COMPANY_NAME': COMPANY_NAME,
        'BRAND_PRIMARY': BRAND_PRIMARY,
        'BRAND_SECONDARY': BRAND_SECONDARY,
        'COPYRIGHT_YEAR': COPYRIGHT_YEAR,
        'user_count': total_count
    }

print("=" * 60)
print(f"{APP_NAME} v{APP_VERSION} - {COMPANY_NAME}")
print("=" * 60)
print(f"psutil: {'✅ Available - Showing REAL metrics' if PSUTIL_AVAILABLE else '❌ Not available - Showing SIMULATED metrics'}")
print("=" * 60)

# ============================================================================
# LDAP Functions
# ============================================================================
def get_ldap_connection():
    try:
        server = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL)
        conn = Connection(server, user=LDAP_ADMIN, password=LDAP_PASSWORD, auto_bind=True)
        return conn
    except Exception as e:
        print(f"LDAP connection error: {e}")
        return None

def escape_ldap_filter(search_term):
    """Escape special characters in LDAP filter values"""
    if not search_term:
        return ''
    
    escape_chars = {
        '\\': '\\5c',
        '*': '\\2a',
        '(': '\\28',
        ')': '\\29',
        '\0': '\\00'
    }
    
    escaped = ''.join(escape_chars.get(c, c) for c in search_term)
    return escaped

def get_users_paginated(page=1, per_page=DEFAULT_PER_PAGE, search_term='', sort_by='cn'):
    """Get paginated users from LDAP with server-side search"""
    conn = get_ldap_connection()
    if not conn:
        return [], 0, 0
    
    try:
        search_term = search_term.strip() if search_term else ''
        search_filter = '(objectClass=person)'
        
        if search_term:
            escaped_term = escape_ldap_filter(search_term)
            search_filter = f"""
                (&
                    (objectClass=person)
                    (|
                        (uid=*{escaped_term}*)
                        (cn=*{escaped_term}*)
                        (sn=*{escaped_term}*)
                        (givenName=*{escaped_term}*)
                        (telephoneNumber=*{escaped_term}*)
                        (mobile=*{escaped_term}*)
                        (phone2=*{escaped_term}*)
                        (mail=*{escaped_term}*)
                    )
                )
            """
            search_filter = ' '.join(search_filter.split())
        
        total_count = get_user_count(search_filter)
        
        if total_count == 0:
            conn.unbind()
            return [], 0, 0
        
        total_pages = (total_count + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        
        if not conn.search(
            search_base=PEOPLE_OU,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['*']
        ):
            print(f"LDAP search failed: {conn.result}")
            conn.unbind()
            return [], total_count, total_pages
        
        all_users = []
        for entry in conn.entries:
            dn = str(entry.entry_dn)
            uid = ''
            if hasattr(entry, 'uid') and entry.uid:
                uid = str(entry.uid)
            else:
                for part in dn.split(','):
                    if part.startswith('uid='):
                        uid = part.replace('uid=', '')
                        break
            
            user = {
                'dn': dn,
                'uid': uid,
                'cn': str(entry.cn) if hasattr(entry, 'cn') and entry.cn else uid,
                'sn': str(entry.sn) if hasattr(entry, 'sn') and entry.sn else '',
                'givenName': str(entry.givenName) if hasattr(entry, 'givenName') and entry.givenName else '',
                'telephoneNumber': str(entry.telephoneNumber) if hasattr(entry, 'telephoneNumber') and entry.telephoneNumber else '',
                'phone2': str(entry.phone2) if hasattr(entry, 'phone2') and entry.phone2 else '',
                'mobile': str(entry.mobile) if hasattr(entry, 'mobile') and entry.mobile else '',
                'mail': str(entry.mail) if hasattr(entry, 'mail') and entry.mail else '',
                'employeeNumber': str(entry.employeeNumber) if hasattr(entry, 'employeeNumber') and entry.employeeNumber else '',
                'title': str(entry.title) if hasattr(entry, 'title') and entry.title else '',
                'departmentNumber': str(entry.departmentNumber) if hasattr(entry, 'departmentNumber') and entry.departmentNumber else ''
            }
            all_users.append(user)
        
        if sort_by and all_users:
            all_users.sort(key=lambda x: x.get(sort_by, '').lower())
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_users = all_users[start_idx:end_idx]
        
        conn.unbind()
        return paginated_users, total_count, total_pages
        
    except Exception as e:
        print(f"Error in get_users_paginated: {str(e)}")
        if conn:
            conn.unbind()
        return [], 0, 0

def get_user_count(search_filter='(objectClass=person)'):
    """Efficiently count users without retrieving all entries"""
    conn = get_ldap_connection()
    if not conn:
        return 0
    
    try:
        if not conn.search(
            search_base=PEOPLE_OU,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['uid'],
            size_limit=0
        ):
            print(f"Count search failed: {conn.result}")
            conn.unbind()
            return 0
        
        count = len(conn.entries)
        conn.unbind()
        return count
        
    except Exception as e:
        print(f"Error getting user count: {str(e)}")
        if conn:
            conn.unbind()
        return 0

def get_all_users():
    """Get all users from LDAP"""
    conn = get_ldap_connection()
    if not conn:
        return []
    try:
        conn.search(search_base=PEOPLE_OU, search_filter='(objectClass=person)', search_scope=SUBTREE, attributes=['*'])
        users = []
        for entry in conn.entries:
            dn = str(entry.entry_dn)
            uid = ''
            if hasattr(entry, 'uid') and entry.uid:
                uid = str(entry.uid)
            else:
                for part in dn.split(','):
                    if part.startswith('uid='):
                        uid = part.replace('uid=', '')
                        break
            user = {
                'dn': dn, 'uid': uid,
                'cn': str(entry.cn) if hasattr(entry, 'cn') and entry.cn else uid,
                'sn': str(entry.sn) if hasattr(entry, 'sn') and entry.sn else '',
                'givenName': str(entry.givenName) if hasattr(entry, 'givenName') and entry.givenName else '',
                'telephoneNumber': str(entry.telephoneNumber) if hasattr(entry, 'telephoneNumber') and entry.telephoneNumber else '',
                'phone2': str(entry.phone2) if hasattr(entry, 'phone2') and entry.phone2 else '',
                'mobile': str(entry.mobile) if hasattr(entry, 'mobile') and entry.mobile else '',
                'mail': str(entry.mail) if hasattr(entry, 'mail') and entry.mail else '',
                'employeeNumber': str(entry.employeeNumber) if hasattr(entry, 'employeeNumber') and entry.employeeNumber else '',
                'title': str(entry.title) if hasattr(entry, 'title') and entry.title else '',
                'departmentNumber': str(entry.departmentNumber) if hasattr(entry, 'departmentNumber') and entry.departmentNumber else ''
            }
            users.append(user)
        conn.unbind()
        return users
    except Exception as e:
        print(f"Error getting users: {e}")
        if conn:
            conn.unbind()
        return []

def add_user_to_ldap(uid, cn, sn, givenName, password, phone2="", **kwargs):
    """Add user using ldapadd command"""
    ldif = f"""dn: uid={uid},{PEOPLE_OU}
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: inetOrgPerson
objectClass: phone2Object
uid: {uid}
cn: {cn}
sn: {sn}
givenName: {givenName}
userPassword: {password}
"""
    if kwargs.get('telephoneNumber'):
        ldif += f"telephoneNumber: {kwargs['telephoneNumber']}\n"
    if phone2:
        ldif += f"phone2: {phone2}\n"
    if kwargs.get('mobile'):
        ldif += f"mobile: {kwargs['mobile']}\n"
    if kwargs.get('mail'):
        ldif += f"mail: {kwargs['mail']}\n"
    if kwargs.get('employeeNumber'):
        ldif += f"employeeNumber: {kwargs['employeeNumber']}\n"
    if kwargs.get('title'):
        ldif += f"title: {kwargs['title']}\n"
    if kwargs.get('departmentNumber'):
        ldif += f"departmentNumber: {kwargs['departmentNumber']}\n"
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ldif')
    temp_file.write(ldif)
    temp_file.close()

    cmd = [
        'ldapadd',
        '-x',
        '-H', f'ldap://{LDAP_SERVER}:{LDAP_PORT}',
        '-D', LDAP_ADMIN,
        '-w', LDAP_PASSWORD,
        '-f', temp_file.name
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(temp_file.name)
    
    if result.returncode == 0:
        return True, f"User {uid} added successfully!"
    else:
        return False, f"Error: {result.stderr}"

def export_users_to_csv(users):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['uid', 'cn', 'sn', 'givenName', 'employeeNumber', 'telephoneNumber', 'phone2', 'mobile', 'mail', 'title', 'departmentNumber'])
    for user in users:
        writer.writerow([
            user.get('uid', ''),
            user.get('cn', ''),
            user.get('sn', ''),
            user.get('givenName', ''),
            user.get('employeeNumber', ''),
            user.get('telephoneNumber', ''),
            user.get('phone2', ''),
            user.get('mobile', ''),
            user.get('mail', ''),
            user.get('title', ''),
            user.get('departmentNumber', '')
        ])
    return output.getvalue()

def import_users_from_csv(csv_content):
    results = {'total': 0, 'success': 0, 'failed': 0, 'errors': []}
    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        results['total'] = sum(1 for _ in reader)
        reader = csv.DictReader(io.StringIO(csv_content))
        for row in reader:
            uid = row.get('uid', '').strip()
            cn = row.get('cn', '').strip()
            sn = row.get('sn', '').strip()
            givenName = row.get('givenName', '').strip()
            password = row.get('password', 'Default123!')
            phone2 = row.get('phone2', '').strip()
            
            if not uid or not cn or not sn or not givenName:
                results['failed'] += 1
                results['errors'].append(f"Missing required fields for: {uid}")
                continue
            
            success, message = add_user_to_ldap(
                uid=uid, cn=cn, sn=sn, givenName=givenName, password=password,
                phone2=phone2,
                employeeNumber=row.get('employeeNumber', '').strip(),
                telephoneNumber=row.get('telephoneNumber', '').strip(),
                mobile=row.get('mobile', '').strip(),
                mail=row.get('mail', '').strip(),
                title=row.get('title', '').strip(),
                departmentNumber=row.get('departmentNumber', '').strip()
            )
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(message)
        return results
    except Exception as e:
        return {'total': 0, 'success': 0, 'failed': 1, 'errors': [f"Error parsing CSV: {str(e)}"]}

# ============================================================================
# Forms
# ============================================================================
class AddUserForm(FlaskForm):
    uid = StringField('Username (UID)', validators=[DataRequired(), Length(min=3, max=50)])
    cn = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    sn = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    givenName = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    employeeNumber = StringField('Employee ID', validators=[Optional()])
    telephoneNumber = StringField('Phone Number', validators=[Optional()])
    mobile = StringField('Mobile Number', validators=[Optional()])
    mail = StringField('Email', validators=[Optional(), Email()])
    title = StringField('Job Title', validators=[Optional()])
    departmentNumber = StringField('Department', validators=[Optional()])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    submit = SubmitField('Add User')

class SearchForm(FlaskForm):
    search_term = StringField('Search', validators=[DataRequired()])
    search_type = SelectField('Search Type', choices=[
        ('name', 'Search by Name'), 
        ('number', 'Search by Phone Number'),
        ('email', 'Search by Email'), 
        ('uid', 'Search by Username')
    ])
    submit = SubmitField('Search')

class ResetPasswordForm(FlaskForm):
    uid = StringField('Username', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Reset Password')

# ============================================================================
# Routes
# ============================================================================
@app.route('/')
def index():
    total_count = get_user_count()
    metrics = get_system_metrics()
    
    return render_template(
        'index.html', 
        title='Dashboard', 
        metrics=metrics,
        icon='speedometer2', 
        now=datetime.now()
    )

@app.route('/users')
def users():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', DEFAULT_PER_PAGE, type=int)
        search_term = request.args.get('search', '', type=str)
        sort_by = request.args.get('sort', 'cn', type=str)
        
        if per_page > MAX_PER_PAGE:
            per_page = MAX_PER_PAGE
        if per_page < MIN_PER_PAGE:
            per_page = MIN_PER_PAGE
        
        users_list, total_count, total_pages = get_users_paginated(
            page=page,
            per_page=per_page,
            search_term=search_term,
            sort_by=sort_by
        )
        
        if search_term and users_list:
            flash(f'Found {len(users_list)} user(s) matching "{search_term}"', 'info')
        elif search_term and not users_list:
            flash(f'No users found matching "{search_term}"', 'warning')
        
        return render_template(
            'users.html',
            title='User Management',
            users=users_list,
            page=page,
            per_page=per_page,
            total_count=total_count,
            total_pages=total_pages,
            search_term=search_term,
            sort_by=sort_by,
            icon='people',
            now=datetime.now()
        )
        
    except Exception as e:
        print(f"Error in users route: {str(e)}")
        flash(f'Error loading users: {str(e)}', 'danger')
        return render_template(
            'users.html',
            title='User Management',
            users=[],
            page=1,
            per_page=DEFAULT_PER_PAGE,
            total_count=0,
            total_pages=0,
            search_term='',
            sort_by='cn',
            icon='people',
            now=datetime.now()
        )

@app.route('/add', methods=['GET', 'POST'])
def add_user():
    form = AddUserForm()
    if form.validate_on_submit():
        success, message = add_user_to_ldap(
            uid=form.uid.data, 
            cn=form.cn.data, 
            sn=form.sn.data,
            givenName=form.givenName.data, 
            password=form.password.data or 'Default123!',
            employeeNumber=form.employeeNumber.data,
            telephoneNumber=form.telephoneNumber.data,
            mobile=form.mobile.data,
            phone2=request.form.get("phone2", "").strip(),
            mail=form.mail.data,
            title=form.title.data,
            departmentNumber=form.departmentNumber.data
        )
        if success:
            flash(message, 'success')
            return redirect(url_for('users'))
        else:
            flash(message, 'danger')
    return render_template('add.html', title='Add User', form=form, icon='person-plus', now=datetime.now())

@app.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    results = []
    if form.validate_on_submit():
        search_term = form.search_term.data
        search_type = form.search_type.data
        all_users = get_all_users()
        for user in all_users:
            if search_type == 'name':
                if (search_term.lower() in user['cn'].lower() or 
                    search_term.lower() in user['sn'].lower() or 
                    search_term.lower() in user['givenName'].lower()):
                    results.append(user)
            elif search_type == 'number':
                if search_term in user['telephoneNumber'] or search_term in user['mobile']:
                    results.append(user)
            elif search_type == 'email':
                if search_term.lower() in user['mail'].lower():
                    results.append(user)
            elif search_type == 'uid':
                if search_term.lower() in user['uid'].lower():
                    results.append(user)
        flash(f'Found {len(results)} user(s)', 'info')
    return render_template('search.html', title='Search Users', form=form, results=results, icon='search', now=datetime.now())

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        if form.new_password.data != form.confirm_password.data:
            flash('Passwords do not match!', 'danger')
            return render_template('reset_password.html', title='Reset Password', form=form, icon='key', now=datetime.now())
        
        conn = get_ldap_connection()
        if not conn:
            flash('Cannot connect to LDAP server', 'danger')
            return render_template('reset_password.html', title='Reset Password', form=form, icon='key', now=datetime.now())
        
        try:
            dn = f"uid={form.uid.data},{PEOPLE_OU}"
            conn.modify(dn, {'userPassword': [(MODIFY_REPLACE, [form.new_password.data])]})
            conn.unbind()
            flash(f'Password for {form.uid.data} reset successfully!', 'success')
            return redirect(url_for('users'))
        except Exception as e:
            flash(f'Error resetting password: {e}', 'danger')
            if conn:
                conn.unbind()
    
    return render_template('reset_password.html', title='Reset Password', form=form, icon='key', now=datetime.now())

@app.route('/phone_config')
def phone_config():
    return render_template('phone_config.html', title='Phone Configuration', icon='phone', now=datetime.now())

@app.route('/import_export')
def import_export():
    return render_template('import_export.html', title='Import/Export', icon='file-earmark-arrow', now=datetime.now())

@app.route('/export/csv')
def export_csv():
    users = get_all_users()
    csv_data = export_users_to_csv(users)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=ldap_users_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )

@app.route('/export/sample-csv')
def export_sample_csv():
    sample_data = [{
        'uid': 'sample_user1',
        'cn': 'Sample User One',
        'sn': 'User',
        'givenName': 'Sample',
        'employeeNumber': 'EMP001',
        'telephoneNumber': '+91-555-0100',
        'phone2': '+91-555-0101',
        'mobile': '+91-555-0102',
        'mail': 'sample1@coreip.local',
        'title': 'Engineer',
        'departmentNumber': 'DEP001'
    }]
    csv_data = export_users_to_csv(sample_data)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=ldap_sample_template.csv'}
    )

@app.route('/import/csv', methods=['POST'])
def import_csv():
    if 'csv_file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('import_export'))
    
    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('import_export'))
    
    if not file.filename.endswith('.csv'):
        flash('Please upload a CSV file', 'danger')
        return redirect(url_for('import_export'))
    
    try:
        csv_content = file.read().decode('utf-8')
        results = import_users_from_csv(csv_content)
        flash(f'Import completed! Total: {results["total"]}, Success: {results["success"]}, Failed: {results["failed"]}', 
              'success' if results['failed'] == 0 else 'warning')
        if results['errors']:
            for error in results['errors'][:5]:
                flash(f'Error: {error}', 'danger')
        return redirect(url_for('users'))
    except Exception as e:
        flash(f'Error importing CSV: {str(e)}', 'danger')
        return redirect(url_for('import_export'))

@app.route('/delete_user', methods=['GET'])
def delete_user():
    uid = request.args.get('uid')
    if not uid:
        flash('No user specified', 'danger')
        return redirect(url_for('users'))
    
    conn = get_ldap_connection()
    if not conn:
        flash('Cannot connect to LDAP server', 'danger')
        return redirect(url_for('users'))
    
    try:
        dn = f"uid={uid},{PEOPLE_OU}"
        conn.delete(dn)
        conn.unbind()
        flash(f'User {uid} deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting user: {e}', 'danger')
        if conn:
            conn.unbind()
    
    return redirect(url_for('users'))

@app.route('/delete_multiple_users', methods=['POST'])
def delete_multiple_users():
    selected_users = request.form.getlist('selected_users')
    if not selected_users:
        flash('No users selected for deletion', 'warning')
        return redirect(url_for('users'))
    
    conn = get_ldap_connection()
    if not conn:
        flash('Cannot connect to LDAP server', 'danger')
        return redirect(url_for('users'))
    
    deleted = []
    failed = []
    for uid in selected_users:
        try:
            dn = f"uid={uid},{PEOPLE_OU}"
            conn.delete(dn)
            deleted.append(uid)
        except Exception as e:
            failed.append(f"{uid} ({str(e)})")
    
    conn.unbind()
    
    if deleted:
        flash(f'Successfully deleted {len(deleted)} user(s): {", ".join(deleted)}', 'success')
    if failed:
        flash(f'Failed to delete {len(failed)} user(s): {", ".join(failed)}', 'danger')
    
    return redirect(url_for('users'))

@app.route('/edit/<uid>', methods=['GET', 'POST'])
def edit_user(uid):
    conn = get_ldap_connection()
    if not conn:
        flash('Cannot connect to LDAP server', 'danger')
        return redirect(url_for('users'))
    
    try:
        conn.search(search_base=PEOPLE_OU, search_filter=f"(uid={uid})", search_scope=SUBTREE, attributes=['*'])
        
        if len(conn.entries) == 0:
            flash(f'User {uid} not found!', 'danger')
            conn.unbind()
            return redirect(url_for('users'))
        
        entry = conn.entries[0]
        current_data = {
            'uid': uid,
            'cn': str(entry.cn) if hasattr(entry, 'cn') and entry.cn else '',
            'sn': str(entry.sn) if hasattr(entry, 'sn') and entry.sn else '',
            'givenName': str(entry.givenName) if hasattr(entry, 'givenName') and entry.givenName else '',
            'telephoneNumber': str(entry.telephoneNumber) if hasattr(entry, 'telephoneNumber') and entry.telephoneNumber else '',
            'phone2': str(entry.phone2) if hasattr(entry, 'phone2') and entry.phone2 else '',
            'mobile': str(entry.mobile) if hasattr(entry, 'mobile') and entry.mobile else '',
            'mail': str(entry.mail) if hasattr(entry, 'mail') and entry.mail else '',
            'employeeNumber': str(entry.employeeNumber) if hasattr(entry, 'employeeNumber') and entry.employeeNumber else '',
            'title': str(entry.title) if hasattr(entry, 'title') and entry.title else '',
            'departmentNumber': str(entry.departmentNumber) if hasattr(entry, 'departmentNumber') and entry.departmentNumber else ''
        }
        conn.unbind()
        
        if request.method == 'POST':
            new_cn = request.form.get('cn', '').strip()
            new_sn = request.form.get('sn', '').strip()
            new_givenName = request.form.get('givenName', '').strip()
            new_telephoneNumber = request.form.get('telephoneNumber', '').strip()
            new_phone2 = request.form.get('phone2', '').strip()
            new_mobile = request.form.get('mobile', '').strip()
            new_mail = request.form.get('mail', '').strip()
            new_employeeNumber = request.form.get('employeeNumber', '').strip()
            new_title = request.form.get('title', '').strip()
            new_departmentNumber = request.form.get('departmentNumber', '').strip()
            new_password = request.form.get('password', '').strip()
            
            conn = get_ldap_connection()
            if not conn:
                flash('Cannot connect to LDAP server', 'danger')
                return redirect(url_for('users'))
            
            try:
                dn = f"uid={uid},{PEOPLE_OU}"
                changes = {}
                modified = False
                
                if new_cn and new_cn != current_data['cn']:
                    changes['cn'] = [(MODIFY_REPLACE, [new_cn])]
                    modified = True
                if new_sn and new_sn != current_data['sn']:
                    changes['sn'] = [(MODIFY_REPLACE, [new_sn])]
                    modified = True
                if new_givenName and new_givenName != current_data['givenName']:
                    changes['givenName'] = [(MODIFY_REPLACE, [new_givenName])]
                    modified = True
                if new_telephoneNumber != current_data['telephoneNumber']:
                    if new_telephoneNumber:
                        changes['telephoneNumber'] = [(MODIFY_REPLACE, [new_telephoneNumber])]
                    else:
                        changes['telephoneNumber'] = [(MODIFY_DELETE, [])]
                    modified = True
                if new_phone2 != current_data['phone2']:
                    if new_phone2:
                        changes['phone2'] = [(MODIFY_REPLACE, [new_phone2])]
                    else:
                        changes['phone2'] = [(MODIFY_DELETE, [])]
                    modified = True
                if new_mobile != current_data['mobile']:
                    if new_mobile:
                        changes['mobile'] = [(MODIFY_REPLACE, [new_mobile])]
                    else:
                        changes['mobile'] = [(MODIFY_DELETE, [])]
                    modified = True
                if new_mail != current_data['mail']:
                    if new_mail:
                        changes['mail'] = [(MODIFY_REPLACE, [new_mail])]
                    else:
                        changes['mail'] = [(MODIFY_DELETE, [])]
                    modified = True
                if new_employeeNumber != current_data['employeeNumber']:
                    if new_employeeNumber:
                        changes['employeeNumber'] = [(MODIFY_REPLACE, [new_employeeNumber])]
                    else:
                        changes['employeeNumber'] = [(MODIFY_DELETE, [])]
                    modified = True
                if new_title != current_data['title']:
                    if new_title:
                        changes['title'] = [(MODIFY_REPLACE, [new_title])]
                    else:
                        changes['title'] = [(MODIFY_DELETE, [])]
                    modified = True
                if new_departmentNumber != current_data['departmentNumber']:
                    if new_departmentNumber:
                        changes['departmentNumber'] = [(MODIFY_REPLACE, [new_departmentNumber])]
                    else:
                        changes['departmentNumber'] = [(MODIFY_DELETE, [])]
                    modified = True
                if new_password:
                    changes['userPassword'] = [(MODIFY_REPLACE, [new_password])]
                    modified = True
                
                if modified:
                    conn.modify(dn, changes)
                    flash(f'User {uid} updated successfully!', 'success')
                else:
                    flash('No changes made', 'info')
                
                conn.unbind()
                return redirect(url_for('users'))
                
            except Exception as e:
                flash(f'Error updating user: {str(e)}', 'danger')
                if conn:
                    conn.unbind()
                return redirect(url_for('edit_user', uid=uid))
        
        return render_template('edit.html', title='Edit User', user=current_data, icon='pencil-square', now=datetime.now())
    
    except Exception as e:
        flash(f'Error loading user: {str(e)}', 'danger')
        if conn:
            conn.unbind()
        return redirect(url_for('users'))

# ============================================================================
# API Endpoints for Real-time Updates
# ============================================================================
@app.route('/api/user-count')
def api_user_count():
    """API endpoint to get user count for real-time updates"""
    try:
        count = get_user_count()
        return jsonify({'count': count, 'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/metrics')
def api_metrics():
    """API endpoint for system metrics"""
    metrics = get_system_metrics()
    return jsonify(metrics)

@app.route('/api/weekly-activity')
def api_weekly_activity():
    """API endpoint for weekly activity data"""
    data = {
        'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'values': [random.randint(20, 80) for _ in range(7)]
    }
    return jsonify(data)

# ============================================================================
# Debug Route
# ============================================================================
@app.route('/debug')
def debug():
    users = get_all_users()
    output = "<h1>LDAP Debug</h1><p><b>Total Users: " + str(len(users)) + "</b></p><hr>"
    for user in users:
        output += f"<h3>{user['uid']} - {user['cn']}</h3><ul>"
        for key, value in user.items():
            if value:
                output += f"<li><b>{key}:</b> {value}</li>"
        output += "</ul><hr>"
    return output

# ============================================================================
# Main Entry Point
# ============================================================================
if __name__ == '__main__':
    print("=" * 60)
    print(f"{APP_NAME} v{APP_VERSION} - {COMPANY_NAME}")
    print("=" * 60)
    print(f"Web Server: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"LDAP Server: {LDAP_SERVER}:{LDAP_PORT}")
    print(f"Debug Mode: {DEBUG_MODE}")
    print(f"psutil: {'✅ Available - Showing REAL metrics' if PSUTIL_AVAILABLE else '❌ Not available - Showing SIMULATED metrics'}")
    print("=" * 60)
    
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG_MODE)