from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid

from config import Config
from database import get_db_connection
from utils import allowed_file, send_welcome_email, generate_random_password, is_strong_password
from auth import login_required, admin_required

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    conn = get_db_connection()
    articles = conn.execute('''
        SELECT a.*, u.username 
        FROM articles a 
        JOIN users u ON a.author_id = u.id 
        WHERE a.published = TRUE 
        ORDER BY a.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('index.html', articles=articles)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? AND active = TRUE', (username,)
        ).fetchone()
        conn.close()
        
        if user and user['password_hash'] == password:  # Simple password check for now
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password, or account is disabled', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    if session.get('is_admin'):
        articles = conn.execute('''
            SELECT a.*, u.username 
            FROM articles a 
            JOIN users u ON a.author_id = u.id 
            ORDER BY a.created_at DESC
        ''').fetchall()
    else:
        articles = conn.execute('''
            SELECT a.*, u.username 
            FROM articles a 
            JOIN users u ON a.author_id = u.id 
            WHERE a.author_id = ? 
            ORDER BY a.created_at DESC
        ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('dashboard.html', articles=articles)

@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db_connection()
    users = conn.execute('''
        SELECT id, username, email, is_admin, active, created_at,
               (SELECT COUNT(*) FROM articles WHERE author_id = users.id) as article_count
        FROM users 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/add_user', methods=['GET', 'POST'])
@admin_required
def admin_add_user():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        is_admin = 'is_admin' in request.form
        
        if not username or not email:
            flash('Username and email are required', 'error')
            return render_template('admin_add_user.html')
        
        # Generate random password
        password = generate_random_password()
        
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO users (username, email, password_hash, is_admin, active) VALUES (?, ?, ?, ?, ?)',
                (username, email, password, is_admin, True)
            )
            conn.commit()
            
            # Send welcome email
            try:
                send_welcome_email(email, username, password)
                flash(f'User {username} created successfully! Welcome email sent to {email}', 'success')
            except Exception as e:
                flash(f'User created but email failed to send: {str(e)}', 'warning')
            
            return redirect(url_for('admin_users'))
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'error')
        finally:
            conn.close()
    
    return render_template('admin_add_user.html')

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin_users'))
    
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        is_admin = 'is_admin' in request.form
        active = 'active' in request.form
        reset_password = 'reset_password' in request.form
        
        try:
            if reset_password:
                new_password = generate_random_password()
                conn.execute('''
                    UPDATE users 
                    SET username = ?, email = ?, is_admin = ?, active = ?, password_hash = ?
                    WHERE id = ?
                ''', (username, email, is_admin, active, new_password, user_id))
                
                # Send new password email
                try:
                    send_welcome_email(email, username, new_password, is_reset=True)
                    flash(f'User updated and new password sent to {email}', 'success')
                except Exception as e:
                    flash(f'User updated but email failed to send: {str(e)}', 'warning')
            else:
                conn.execute('''
                    UPDATE users 
                    SET username = ?, email = ?, is_admin = ?, active = ?
                    WHERE id = ?
                ''', (username, email, is_admin, active, user_id))
                flash('User updated successfully', 'success')
            
            conn.commit()
            return redirect(url_for('admin_users'))
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'error')
        finally:
            conn.close()
    
    conn.close()
    return render_template('admin_edit_user.html', user=user)

@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def admin_delete_user(user_id):
    if user_id == session['user_id']:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin_users'))
    
    conn = get_db_connection()
    try:
        # Check if user has articles
        article_count = conn.execute(
            'SELECT COUNT(*) as count FROM articles WHERE author_id = ?', (user_id,)
        ).fetchone()['count']
        
        if article_count > 0:
            flash('Cannot delete user with existing articles. Please reassign or delete articles first.', 'error')
        else:
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            flash('User deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_users'))

@app.route('/create_article', methods=['GET', 'POST'])
@login_required
def create_article():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        published = 'published' in request.form
        
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = str(uuid.uuid4()) + '.' + secure_filename(file.filename).rsplit('.', 1)[1].lower()
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = filename
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO articles (title, content, image_path, author_id, published)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, content, image_path, session['user_id'], published))
        conn.commit()
        conn.close()
        
        flash('Article created successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('create_article.html')

@app.route('/edit_article/<int:article_id>', methods=['GET', 'POST'])
@login_required
def edit_article(article_id):
    conn = get_db_connection()
    article = conn.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    
    if not article:
        flash('Article not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if user can edit this article
    if not session.get('is_admin') and article['author_id'] != session['user_id']:
        flash('You can only edit your own articles', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        published = 'published' in request.form
        
        image_path = article['image_path']  # Keep existing image by default
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Delete old image if it exists
                if image_path:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                filename = str(uuid.uuid4()) + '.' + secure_filename(file.filename).rsplit('.', 1)[1].lower()
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = filename
        
        conn.execute('''
            UPDATE articles 
            SET title = ?, content = ?, image_path = ?, published = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (title, content, image_path, published, article_id))
        conn.commit()
        conn.close()
        
        flash('Article updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    conn.close()
    return render_template('edit_article.html', article=article)

@app.route('/delete_article/<int:article_id>')
@login_required
def delete_article(article_id):
    conn = get_db_connection()
    article = conn.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    
    if not article:
        flash('Article not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if user can delete this article
    if not session.get('is_admin') and article['author_id'] != session['user_id']:
        flash('You can only delete your own articles', 'error')
        return redirect(url_for('dashboard'))
    
    # Delete associated image
    if article['image_path']:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], article['image_path'])
        if os.path.exists(image_path):
            os.remove(image_path)
    
    conn.execute('DELETE FROM articles WHERE id = ?', (article_id,))
    conn.commit()
    conn.close()
    
    flash('Article deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/article/<int:article_id>')
def view_article(article_id):
    conn = get_db_connection()
    article = conn.execute('''
        SELECT a.*, u.username 
        FROM articles a 
        JOIN users u ON a.author_id = u.id 
        WHERE a.id = ? AND a.published = TRUE
    ''', (article_id,)).fetchone()
    conn.close()
    
    if not article:
        flash('Article not found or not published', 'error')
        return redirect(url_for('index'))
    
    return render_template('article.html', article=article)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('change_password.html')
        
        if not is_strong_password(new_password):
            flash('Password must be 8-20 characters, include upper and lower case letters, a digit, and a special character.', 'error')
            return render_template('change_password.html')
        
        conn = get_db_connection()
        user = conn.execute('SELECT password_hash FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        
        if user['password_hash'] != current_password:
            flash('Current password is incorrect', 'error')
            conn.close()
            return render_template('change_password.html')
        
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_password, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('change_password.html')

if __name__ == '__main__':
    
    # For production on Raspberry Pi, use host='0.0.0.0' to accept external connections
    app.run(debug=True, host='0.0.0.0', port=5000)