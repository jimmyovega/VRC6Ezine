#!/usr/bin/env python3
"""
Database Management Script
Allows you to list, drop tables, or remove the entire database
MOVE THIS FILE TO THE PROJECT ROOT DIRECTORY
This script provides an interactive command-line interface to manage your SQLite database.
It can list all tables, drop specific tables, drop all tables, or remove the entire database file.
Make sure to run this script only when you are sure about the operations, as dropping tables or removing the database cannot be undone.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Import your existing config
try:
    from config import Config
    DATABASE_PATH = Config.DATABASE_PATH
except ImportError:
    # Fallback if config is not available
    DATABASE_PATH = "app.db"
    print("Warning: Could not import Config. Using default database path: app.db")

def get_db_connection():
    """Get a database connection"""
    if not os.path.exists(DATABASE_PATH):
        print(f"Database file '{DATABASE_PATH}' does not exist!")
        return None
    return sqlite3.connect(DATABASE_PATH)

def list_tables():
    """List all tables in the database"""
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

def get_table_info(table_name):
    """Get information about a specific table"""
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]
    
    # Get column info
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    conn.close()
    return {
        'row_count': row_count,
        'columns': columns
    }

def drop_table(table_name):
    """Drop a specific table"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
        conn.close()
        print(f"✅ Table '{table_name}' dropped successfully!")
        return True
    except sqlite3.Error as e:
        print(f"❌ Error dropping table '{table_name}': {e}")
        conn.close()
        return False

def drop_all_tables():
    """Drop all tables in the database"""
    tables = list_tables()
    if not tables:
        print("No tables found to drop.")
        return
    
    print(f"Dropping {len(tables)} tables...")
    success_count = 0
    
    for table in tables:
        if drop_table(table):
            success_count += 1
    
    print(f"✅ Successfully dropped {success_count}/{len(tables)} tables")

def remove_database():
    """Remove the entire database file"""
    if not os.path.exists(DATABASE_PATH):
        print(f"Database file '{DATABASE_PATH}' does not exist!")
        return False
    
    try:
        os.remove(DATABASE_PATH)
        print(f"✅ Database file '{DATABASE_PATH}' removed successfully!")
        return True
    except OSError as e:
        print(f"❌ Error removing database file: {e}")
        return False

def display_tables():
    """Display all tables with their information"""
    tables = list_tables()
    
    if not tables:
        print("No tables found in the database.")
        return
    
    print(f"\n📋 Tables in database '{DATABASE_PATH}':")
    print("=" * 60)
    
    for i, table in enumerate(tables, 1):
        info = get_table_info(table)
        if info:
            print(f"{i:2d}. {table:<20} ({info['row_count']:,} rows)")
        else:
            print(f"{i:2d}. {table:<20} (error reading info)")

def main():
    """Main interactive menu"""
    print("🗄️  Database Management Tool")
    print(f"Database: {DATABASE_PATH}")
    
    if not os.path.exists(DATABASE_PATH):
        print(f"\n❌ Database file '{DATABASE_PATH}' does not exist!")
        return
    
    while True:
        print("\n" + "="*50)
        print("Choose an option:")
        print("1. List all tables")
        print("2. Drop a specific table")
        print("3. Drop ALL tables")
        print("4. Remove entire database file")
        print("5. Exit")
        print("="*50)
        
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == '1':
            display_tables()
            
        elif choice == '2':
            display_tables()
            tables = list_tables()
            if not tables:
                continue
                
            try:
                table_num = int(input(f"\nEnter table number (1-{len(tables)}): ")) - 1
                if 0 <= table_num < len(tables):
                    table_name = tables[table_num]
                    info = get_table_info(table_name)
                    
                    print(f"\n⚠️  About to drop table: {table_name}")
                    if info:
                        print(f"   Rows: {info['row_count']:,}")
                        print(f"   Columns: {len(info['columns'])}")
                    
                    confirm = input("Are you sure? (yes/no): ").lower()
                    if confirm in ['yes', 'y']:
                        drop_table(table_name)
                    else:
                        print("Operation cancelled.")
                else:
                    print("Invalid table number!")
            except ValueError:
                print("Invalid input! Please enter a number.")
                
        elif choice == '3':
            display_tables()
            tables = list_tables()
            if not tables:
                continue
                
            print(f"\n⚠️  About to drop ALL {len(tables)} tables!")
            print("This action cannot be undone!")
            confirm = input("Type 'DROP ALL TABLES' to confirm: ")
            
            if confirm == 'DROP ALL TABLES':
                drop_all_tables()
            else:
                print("Operation cancelled.")
                
        elif choice == '4':
            print(f"\n⚠️  About to remove the entire database file: {DATABASE_PATH}")
            print("This action cannot be undone!")
            confirm = input("Type 'REMOVE DATABASE' to confirm: ")
            
            if confirm == 'REMOVE DATABASE':
                if remove_database():
                    print("Database removed. Exiting...")
                    break
            else:
                print("Operation cancelled.")
                
        elif choice == '5':
            print("Goodbye! 👋")
            break
            
        else:
            print("Invalid choice! Please enter 1-5.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user. Goodbye! 👋")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)