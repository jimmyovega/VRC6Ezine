from unittest.mock import patch, MagicMock

with patch.dict('sys.modules', {'config': MagicMock()}):
    from vrc6 import utils

def test_generate_random_password(length=12):
    password = utils.generate_random_password(length)   
    print (f"Generated password: {password}")
    assert len(password) == length
    assert any(c.islower() for c in password)
    assert any(c.isupper() for c in password)
    assert any(c.isdigit() for c in password)
