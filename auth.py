from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        if not session.get('is_admin'):
            flash('Admin privileges required to access this page.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def check_user_active(user_id):
    """Check if user account is active"""
    from database import get_db_connection
    
    conn = get_db_connection()
    user = conn.execute('SELECT active FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    return user and user['active']

def update_last_login(user_id):
    """Update user's last login timestamp"""
    from database import get_db_connection
    
    conn = get_db_connection()
    conn.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_current_user():
    """Get current user information from session"""
    if 'user_id' not in session:
        return None
    
    from database import get_db_connection
    
    conn = get_db_connection()
    user = conn.execute('''
        SELECT id, username, email, is_admin, active, created_at, last_login 
        FROM users WHERE id = ?
    ''', (session['user_id'],)).fetchone()
    conn.close()
    
    return user

def logout_user():
    """Clear user session"""
    session.clear()

def is_authenticated():
    """Check if user is authenticated"""
    return 'user_id' in session

def is_admin():
    """Check if current user is admin"""
    return session.get('is_admin', False)