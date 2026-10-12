import unittest
from app.core.security import hash_password, verify_password, create_access_token, verify_access_token
from app.database.session import SessionLocal
from app.models.user import User

class TestAuthAndSecurity(unittest.TestCase):
    def test_password_hashing(self):
        pw = "TestPassword99!"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        
        # Salt must be random, so hashes must be distinct
        self.assertNotEqual(h1, h2)
        
        # Both must verify successfully
        self.assertTrue(verify_password(pw, h1))
        self.assertTrue(verify_password(pw, h2))
        
        # Invalid password must fail
        self.assertFalse(verify_password("WrongPassword!", h1))

    def test_jwt_tokens(self):
        payload = {"sub": "user_12345", "email": "test@example.com"}
        token = create_access_token(payload, expires_delta_seconds=3600)
        
        decoded = verify_access_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], "user_12345")
        self.assertEqual(decoded["email"], "test@example.com")
        
        # Tampered token must fail
        tampered_token = token[:-4] + "abcd"
        self.assertIsNone(verify_access_token(tampered_token))
        
        # Expired token must fail
        expired_token = create_access_token(payload, expires_delta_seconds=-10)
        self.assertIsNone(verify_access_token(expired_token))

if __name__ == "__main__":
    unittest.main()
