import sqlite3
from config import Config

def get_db_connection():
    """Get a database connection with Row factory for dict-like access"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the SQLite database with all required tables"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Users table with additional fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Articles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image_path TEXT,
            author_id INTEGER,
            published BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES users (id)
        )
    ''')
    
    # User sessions table (optional, for tracking active sessions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_token TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # System settings table (for storing app configuration)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create default admin user
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, is_admin, active) VALUES (?, ?, ?, ?, ?)",
            (Config.DEFAULT_ADMIN_USERNAME, Config.DEFAULT_ADMIN_EMAIL, 
             Config.DEFAULT_ADMIN_PASSWORD, True, True)
        )
        conn.commit()
        print(f"Default admin user created:")
        print(f"  Username: {Config.DEFAULT_ADMIN_USERNAME}")
        print(f"  Password: {Config.DEFAULT_ADMIN_PASSWORD}")
        print(f"  Email: {Config.DEFAULT_ADMIN_EMAIL}")
        print("⚠️  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!")
    except sqlite3.IntegrityError:
        # Admin user already exists
        pass
    
    # Insert default settings
    default_settings = [
        ('site_initialized', 'true'),
        ('registration_open', 'false'),
        ('max_articles_per_user', '50'),
        ('max_image_size_mb', '16')
    ]
    
    for key, value in default_settings:
        cursor.execute(
            'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
            (key, value)
        )
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def get_setting(key, default=None):
    """Get a setting value from the database"""
    conn = get_db_connection()
    result = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return result['value'] if result else default

def set_setting(key, value):
    """Set a setting value in the database"""
    conn = get_db_connection()
    conn.execute(
        'INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
        (key, value)
    )
    conn.commit()
    conn.close()

def get_user_stats():
    """Get user statistics for admin dashboard"""
    conn = get_db_connection()
    stats = {}
    
    # Total users
    stats['total_users'] = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    
    # Active users
    stats['active_users'] = conn.execute('SELECT COUNT(*) as count FROM users WHERE active = TRUE').fetchone()['count']
    
    # Admin users
    stats['admin_users'] = conn.execute('SELECT COUNT(*) as count FROM users WHERE is_admin = TRUE').fetchone()['count']
    
    # Total articles
    stats['total_articles'] = conn.execute('SELECT COUNT(*) as count FROM articles').fetchone()['count']
    
    # Published articles
    stats['published_articles'] = conn.execute('SELECT COUNT(*) as count FROM articles WHERE published = TRUE').fetchone()['count']
    
    # Draft articles
    stats['draft_articles'] = conn.execute('SELECT COUNT(*) as count FROM articles WHERE published = FALSE').fetchone()['count']
    
    conn.close()
    return stats

def cleanup_old_sessions():
    """Remove expired sessions from the database"""
    conn = get_db_connection()
    conn.execute('DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP')
    conn.commit()
    conn.close()

def backup_database(backup_path):
    """Create a backup of the database"""
    import shutil
    try:
        shutil.copy2(Config.DATABASE_PATH, backup_path)
        return True
    except Exception as e:
        print(f"Backup failed: {e}")
        return False