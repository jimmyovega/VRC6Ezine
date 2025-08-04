import os
import smtplib
import secrets
import string
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config
from PIL import Image
from werkzeug.security import generate_password_hash, check_password_hash

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def generate_random_password(length=12):
    """Generate a secure random password"""
    # Use a mix of letters, digits, and safe symbols
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def send_welcome_email(email, username, password, is_reset=False):
    """Send welcome email to new users with login credentials"""
    
    # Check if email configuration is available
    if not Config.MAIL_USERNAME or not Config.MAIL_PASSWORD:
        raise Exception("Email configuration not set. Please configure MAIL_USERNAME and MAIL_PASSWORD.")
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = Config.MAIL_DEFAULT_SENDER
    msg['To'] = email
    
    if is_reset:
        msg['Subject'] = f"Password Reset - {Config.SITE_NAME}"
        email_type = "password has been reset"
        action_text = "Your password has been reset by an administrator."
    else:
        msg['Subject'] = f"Welcome to {Config.SITE_NAME}"
        email_type = "account has been created"
        action_text = "Your account has been created by an administrator."
    
    # Email body
    body = f"""
    Hello {username},

    {action_text}

    Here are your login credentials:
    
    Website: {Config.SITE_URL}
    Username: {username}
    Password: {password}
    
    For security reasons, please log in and change your password as soon as possible.
    
    To change your password:
    1. Log in to your account
    2. Go to your dashboard
    3. Click on "Change Password"
    
    If you have any questions or need help, please contact the administrator.
    
    Best regards,
    {Config.SITE_NAME} Team
    
    ---
    This is an automated message. Please do not reply to this email.
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Send email
    try:
        server = smtplib.SMTP_SSL(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(Config.MAIL_DEFAULT_SENDER, email, text)
        server.quit()
        return True
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")

def send_notification_email(to_email, subject, message):
    """Send a general notification email"""
    
    if not Config.MAIL_USERNAME or not Config.MAIL_PASSWORD:
        raise Exception("Email configuration not set.")
    
    msg = MIMEMultipart()
    msg['From'] = Config.MAIL_DEFAULT_SENDER
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(message, 'plain'))
    
    try:
        server = smtplib.SMTP_SSL(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(Config.MAIL_DEFAULT_SENDER, to_email, text)
        server.quit()
        return True
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def get_file_info(filepath):
    """Get file information including size and modification date"""
    try:
        stat = os.stat(filepath)
        return {
            'size': stat.st_size,
            'size_formatted': format_file_size(stat.st_size),
            'modified': stat.st_mtime
        }
    except OSError:
        return None

def validate_email(email):
    """Simple email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """Validate username format"""
    import re
    # Username should be 3-20 characters, alphanumeric and underscores only
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(pattern, username) is not None

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    import re
    # Remove any path components
    filename = os.path.basename(filename)
    # Replace spaces and special characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    return filename

def create_thumbnail(image_path, thumbnail_path, size=(300, 300)):
    """Create a thumbnail of an image (requires Pillow)"""
    try:
        #from PIL import Image
        with Image.open(image_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, optimize=True, quality=85)
        return True
    except ImportError:
        # Pillow not installed
        return False
    except Exception as e:
        print(f"Thumbnail creation failed: {e}")
        return False

def log_activity(user_id, action, description=None):
    """Log user activity (requires activity_log table)"""
    from database import get_db_connection
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO activity_log (user_id, action, description, created_at) 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, action, description))
        conn.commit()
    except Exception as e:
        print(f"Activity logging failed: {e}")
    finally:
        conn.close()

def cleanup_orphaned_images():
    """Remove image files that are no longer referenced in the database"""
    from database import get_db_connection
    import glob
    
    conn = get_db_connection()
    
    # Get all image references from database
    referenced_images = set()
    articles = conn.execute('SELECT image_path FROM articles WHERE image_path IS NOT NULL').fetchall()
    for article in articles:
        if article['image_path']:
            referenced_images.add(article['image_path'])
    
    conn.close()
    
    # Get all files in upload directory
    upload_dir = Config.UPLOAD_FOLDER
    upload_files = set()
    
    for ext in Config.ALLOWED_EXTENSIONS:
        pattern = os.path.join(upload_dir, f"*.{ext}")
        files = glob.glob(pattern)
        for file_path in files:
            filename = os.path.basename(file_path)
            upload_files.add(filename)
    
    # Find orphaned files
    orphaned_files = upload_files - referenced_images
    
    # Remove orphaned files
    removed_count = 0
    for filename in orphaned_files:
        file_path = os.path.join(upload_dir, filename)
        try:
            os.remove(file_path)
            removed_count += 1
            print(f"Removed orphaned file: {filename}")
        except OSError as e:
            print(f"Failed to remove {filename}: {e}")
    
    return removed_count

def get_storage_usage():
    """Get storage usage statistics"""
    upload_dir = Config.UPLOAD_FOLDER
    total_size = 0
    file_count = 0
    
    if os.path.exists(upload_dir):
        for root, dirs, files in os.walk(upload_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    file_count += 1
                except OSError:
                    continue
    
    return {
        'total_size': total_size,
        'total_size_formatted': format_file_size(total_size),
        'file_count': file_count
    }

def is_strong_password(password):
    if len(password) < 8 or len(password) > 20:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

def hash_password(password):
    """Hash a password with salt using werkzeug (PBKDF2)."""
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def verify_password(stored_hash, password):
    """Verify a password against the stored hash."""
    return check_password_hash(stored_hash, password)