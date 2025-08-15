import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Mock modules BEFORE importing anything that depends on them
sys.modules['database'] = MagicMock()
sys.modules['config'] = MagicMock()

# Mock the Config class specifically
mock_config = MagicMock()
mock_config.UPLOAD_FOLDER = 'test_uploads'
mock_config.ALLOWED_EXTENSIONS = {'jpg', 'png', 'gif'}
sys.modules['config'].Config = mock_config

# Now we can safely import
from vrc6 import utils

@pytest.fixture
def sample_password():
    return "Test@1234"

def test_generate_random_password(length=12):
    password = utils.generate_random_password(length)   
    #print (f"Generated password: {password}")
    assert len(password) == length
    assert any(c.islower() for c in password)
    assert any(c.isupper() for c in password)
    assert any(c.isdigit() for c in password)

def test_hash_password(sample_password):
    hashed = utils.hash_password(sample_password)
    #print (f"Hashed password: {hashed}")
    assert hashed != sample_password
    assert len(hashed) > 0
    assert utils.check_password_hash(hashed, sample_password)

def test_verify_password(sample_password):
    hashed = utils.hash_password(sample_password)
    assert utils.verify_password(hashed, sample_password)

def test_is_strong_password(sample_password):
    assert utils.is_strong_password(sample_password)
    assert not utils.is_strong_password("weakpass")
    assert not utils.is_strong_password("Short1!")
    assert not utils.is_strong_password("nouppercase1!")
    assert not utils.is_strong_password("NOLOWERCASE1!")
    assert not utils.is_strong_password("NoSpecialChar1")
    assert not utils.is_strong_password("NoNumber!")
    assert not utils.is_strong_password("ThisPasswordIsWayTooLong123!")

def test_get_storage_usage():
    usage = utils.get_storage_usage()
    assert isinstance(usage, dict)
    assert 'total_size' in usage
    assert 'total_size_formatted' in usage
    assert 'file_count' in usage
    assert isinstance(usage['total_size'], int)
    assert isinstance(usage['file_count'], int)

def test_cleanup_orphaned_images():
    """Test cleanup_orphaned_images by mocking its helper functions"""
    
    # Mock the helper functions that cleanup_orphaned_images calls
    with patch('vrc6.utils.get_referenced_images') as mock_get_referenced:
        with patch('vrc6.utils.get_upload_files') as mock_get_upload:
            with patch('vrc6.utils.remove_orphaned_files') as mock_remove_orphaned:
                
                # Set up mock return values
                mock_get_referenced.return_value = {'file1.jpg', 'file3.jpg'}
                mock_get_upload.return_value = {'file1.jpg', 'file2.jpg', 'file3.jpg', 'file4.jpg'}
                mock_remove_orphaned.return_value = 2  # Return count of removed files
                
                # Call the function under test
                result = utils.cleanup_orphaned_images()
                
                # Verify the function calls
                mock_get_referenced.assert_called_once()
                mock_get_upload.assert_called_once()
                
                # Verify remove_orphaned_files was called with correct orphaned files
                expected_orphaned = {'file2.jpg', 'file4.jpg'}  # upload_files - referenced_images
                mock_remove_orphaned.assert_called_once_with(expected_orphaned)
                
                # Verify return value
                assert result == 2

def test_get_referenced_images():
    """Test get_referenced_images function separately"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    mock_cursor.fetchall.return_value = [
        {'image_path': 'file1.jpg'},
        {'image_path': 'file3.jpg'},
        {'image_path': None}  # Test null handling
    ]
    mock_conn.execute.return_value = mock_cursor
    
    with patch('vrc6.utils.get_db_connection', return_value=mock_conn):
        result = utils.get_referenced_images()
        
        expected = {'file1.jpg', 'file3.jpg'}
        assert result == expected
        mock_conn.close.assert_called_once()

def test_get_upload_files():
    """Test get_upload_files function separately"""
    with patch('glob.glob') as mock_glob:
        with patch('os.path.basename', side_effect=lambda x: x.split('/')[-1]):
            
            # Mock glob.glob to return different file patterns
            def glob_side_effect(pattern):
                if pattern.endswith('*.jpg'):
                    return ['/upload/file1.jpg', '/upload/file2.jpg']
                elif pattern.endswith('*.png'):
                    return ['/upload/file3.png']
                return []
            
            mock_glob.side_effect = glob_side_effect
            
            # Mock Config.ALLOWED_EXTENSIONS
            with patch('vrc6.utils.Config') as mock_config:
                mock_config.ALLOWED_EXTENSIONS = ['jpg', 'png']
                mock_config.UPLOAD_FOLDER = '/upload'
                
                result = utils.get_upload_files()
                
                expected = {'file1.jpg', 'file2.jpg', 'file3.png'}
                assert result == expected

def test_remove_orphaned_files():
    """Test remove_orphaned_files function separately"""
    orphaned_files = {'file1.jpg', 'file2.jpg', 'file3.jpg'}
    
    with patch('os.remove') as mock_remove:
        with patch('os.path.join', side_effect=lambda *args: '/'.join(args)):
            with patch('builtins.print'):  # Suppress print output
                with patch('vrc6.utils.Config') as mock_config:
                    mock_config.UPLOAD_FOLDER = '/upload'
                    
                    # Mock successful removal of 2 files, failure on 1
                    def remove_side_effect(path):
                        if 'file2.jpg' in path:
                            raise OSError("Permission denied")
                        return None
                    
                    mock_remove.side_effect = remove_side_effect
                    
                    result = utils.remove_orphaned_files(orphaned_files)
                    
                    # Should return 2 (successfully removed files)
                    assert result == 2
                    
                    # Verify os.remove was called for all files
                    assert mock_remove.call_count == 3

def test_log_activity_success():
    """Test successful activity logging"""
    mock_conn = MagicMock()
    
    with patch('vrc6.utils.get_db_connection', return_value=mock_conn):
        # Call the function
        utils.log_activity(user_id=1, action='login', description='User logged in')
        
        # Verify database operations
        mock_conn.execute.assert_called_once_with(
            '''
            INSERT INTO activity_log (user_id, action, description, created_at) 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (1, 'login', 'User logged in')
        )
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

def test_log_activity_without_description():
    """Test activity logging without description (None value)"""
    mock_conn = MagicMock()
    
    with patch('vrc6.utils.get_db_connection', return_value=mock_conn):
        # Call the function without description
        utils.log_activity(user_id=5, action='logout')
        
        # Verify database operations
        mock_conn.execute.assert_called_once_with(
            '''
            INSERT INTO activity_log (user_id, action, description, created_at) 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (5, 'logout', None)
        )
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

def test_log_activity_database_error():
    """Test activity logging when database operation fails"""
    mock_conn = MagicMock()
    # Make execute raise an exception
    mock_conn.execute.side_effect = Exception("Database connection failed")
    
    with patch('vrc6.utils.get_db_connection', return_value=mock_conn):
        with patch('builtins.print') as mock_print:
            # Call the function - should handle exception gracefully
            utils.log_activity(user_id=3, action='create_post', description='New post created')
            
            # Verify the error was printed
            mock_print.assert_called_once_with("Activity logging failed: Database connection failed")
            
            # Verify execute was attempted
            mock_conn.execute.assert_called_once()
            
            # Verify commit was NOT called due to exception
            mock_conn.commit.assert_not_called()
            
            # Verify connection was still closed in finally block
            mock_conn.close.assert_called_once()

def test_log_activity_commit_error():
    """Test activity logging when commit fails but execute succeeds"""
    mock_conn = MagicMock()
    # Make commit raise an exception
    mock_conn.commit.side_effect = Exception("Commit failed")
    
    with patch('vrc6.utils.get_db_connection', return_value=mock_conn):
        with patch('builtins.print') as mock_print:
            # Call the function
            utils.log_activity(user_id=2, action='update_profile', description='Profile updated')
            
            # Verify the error was printed
            mock_print.assert_called_once_with("Activity logging failed: Commit failed")
            
            # Verify execute was called successfully
            mock_conn.execute.assert_called_once_with(
                '''
            INSERT INTO activity_log (user_id, action, description, created_at) 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (2, 'update_profile', 'Profile updated')
            )
            
            # Verify commit was attempted
            mock_conn.commit.assert_called_once()
            
            # Verify connection was still closed
            mock_conn.close.assert_called_once()

def test_log_activity_connection_close_error():
    """Test activity logging when connection.close() fails"""
    mock_conn = MagicMock()
    # Make close raise an exception - this shouldn't affect the logging
    mock_conn.close.side_effect = Exception("Close failed")
    
    with patch('vrc6.utils.get_db_connection', return_value=mock_conn):
        # The close error should not be caught/handled by the function
        with pytest.raises(Exception, match="Close failed"):
            utils.log_activity(user_id=4, action='delete_post', description='Post deleted')
        
        # Verify the main operations completed successfully
        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

def test_log_activity_with_various_data_types():
    """Test activity logging with different parameter types"""
    mock_conn = MagicMock()
    
    test_cases = [
        # (user_id, action, description)
        (1, 'login', 'User logged in successfully'),
        (999, 'admin_action', 'Admin performed system maintenance'),
        (0, 'guest_access', None),  # Edge case: user_id = 0
        (42, '', 'Empty action string'),  # Edge case: empty action
        (123, 'test', ''),  # Edge case: empty description
    ]
    
    with patch('vrc6.utils.get_db_connection', return_value=mock_conn):
        for user_id, action, description in test_cases:
            mock_conn.reset_mock()  # Reset mock between calls
            
            utils.log_activity(user_id=user_id, action=action, description=description)
            
            # Verify correct parameters were passed
            mock_conn.execute.assert_called_once_with(
                '''
            INSERT INTO activity_log (user_id, action, description, created_at) 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, action, description)
            )
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()

def test_log_activity_sql_injection_safety():
    """Test that the function uses parameterized queries (safe from SQL injection)"""
    mock_conn = MagicMock()
    
    # Malicious input that would cause SQL injection if not properly parameterized
    malicious_user_id = "1; DROP TABLE activity_log; --"
    malicious_action = "'; DELETE FROM users; --"
    malicious_description = "'; UPDATE users SET is_admin = 1; --"
    
    with patch('vrc6.utils.get_db_connection', return_value=mock_conn):
        utils.log_activity(
            user_id=malicious_user_id, 
            action=malicious_action, 
            description=malicious_description
        )
        
        # Verify the malicious strings are passed as parameters (safe)
        mock_conn.execute.assert_called_once_with(
            '''
            INSERT INTO activity_log (user_id, action, description, created_at) 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (malicious_user_id, malicious_action, malicious_description)
        )
        
        # The SQL query itself should remain unchanged (not modified by the input)
        call_args = mock_conn.execute.call_args
        sql_query = call_args[0][0]
        assert "DROP TABLE" not in sql_query
        assert "DELETE FROM" not in sql_query
        assert "UPDATE users" not in sql_query