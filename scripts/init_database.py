#!/usr/bin/env python3
"""
Database initialization script for vrc6 Ezine
Run this script to set up the database for the first time
MOVE THIS FILE TO THE PROJECT ROOT DIRECTORY
This script will create the necessary tables and insert default values
Make sure to run this script only once, or it will fail if the tables already exist.
You can re-run it to reset the database, but it will not delete existing data.
"""

from database import init_db
import os

def main():
    print("Initializing vrc6 Ezine database...")
    
    # Check if database already exists
    if os.path.exists('vrc6.db'):
        response = input("Database already exists. Reinitialize? This will NOT delete existing data (y/N): ")
        if response.lower() != 'y':
            print("Initialization cancelled.")
            return
    
    try:
        init_db()
        print("\n✅ Database initialization completed successfully!")
        print("\nDefault admin account:")
        print("  Username: chief")
        print("  Password: VRC6in2025!")
        print("  ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")
        print("\nYou can now run: python app.py")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())