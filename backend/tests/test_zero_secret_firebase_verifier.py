import unittest
from unittest.mock import patch
import google.auth.exceptions as g_exc
from app.core.security import (
    verify_firebase_id_token,
    verify_token,
    verify_access_token,
    create_access_token,
    get_token_algorithm,
)

class TestZeroSecretFirebaseVerifier(unittest.TestCase):
    """
    Comprehensive unit tests for the official zero-secret Firebase ID token verifier.
    Tests valid claims, claim constraints (audience, issuer, sub), malformed/expired tokens,
    network failures, and backward compatibility with HS256.
    """

    def test_valid_token_decoding(self):
        """Valid token claims are parsed, mapped (sub->uid), and returned."""
        mock_claims = {
            "iss": "https://securetoken.google.com/plutochatbot",
            "aud": "plutochatbot",
            "sub": "user_firebase_12345",
            "email": "user@example.com",
            "name": "Jane Doe",
            "picture": "https://photo.example.com/jane.jpg",
            "auth_time": 1700000000,
            "exp": 1700003600,
        }

        with patch("app.core.security.id_token.verify_firebase_token", return_value=mock_claims.copy()):
            result = verify_firebase_id_token("fake.valid.jwt")
            self.assertIsNotNone(result)
            self.assertEqual(result["uid"], "user_firebase_12345")
            self.assertEqual(result["sub"], "user_firebase_12345")
            self.assertEqual(result["email"], "user@example.com")
            self.assertEqual(result["name"], "Jane Doe")
            self.assertEqual(result["picture"], "https://photo.example.com/jane.jpg")

    def test_wrong_issuer_rejection(self):
        """Tokens with an unexpected issuer must be rejected."""
        mock_claims = {
            "iss": "https://securetoken.google.com/wrong-project",
            "aud": "plutochatbot",
            "sub": "user_firebase_12345",
            "email": "user@example.com",
        }

        with patch("app.core.security.id_token.verify_firebase_token", return_value=mock_claims):
            result = verify_firebase_id_token("fake.wrong_issuer.jwt")
            self.assertIsNone(result)

    def test_missing_or_invalid_sub_rejection(self):
        """Tokens missing sub, or having an empty/non-string sub, must be rejected."""
        # 1. Missing sub
        with patch("app.core.security.id_token.verify_firebase_token", return_value={
            "iss": "https://securetoken.google.com/plutochatbot",
            "aud": "plutochatbot",
            "email": "user@example.com",
        }):
            self.assertIsNone(verify_firebase_id_token("fake.missing_sub.jwt"))

        # 2. Empty string sub
        with patch("app.core.security.id_token.verify_firebase_token", return_value={
            "iss": "https://securetoken.google.com/plutochatbot",
            "aud": "plutochatbot",
            "sub": "",
            "email": "user@example.com",
        }):
            self.assertIsNone(verify_firebase_id_token("fake.empty_sub.jwt"))

        # 3. Non-string sub
        with patch("app.core.security.id_token.verify_firebase_token", return_value={
            "iss": "https://securetoken.google.com/plutochatbot",
            "aud": "plutochatbot",
            "sub": 123456,
            "email": "user@example.com",
        }):
            self.assertIsNone(verify_firebase_id_token("fake.non_string_sub.jwt"))

    def test_wrong_audience_rejection(self):
        """Underlying verify_firebase_token raises InvalidValue on audience mismatch."""
        with patch("app.core.security.id_token.verify_firebase_token", side_effect=g_exc.InvalidValue("Wrong audience")):
            result = verify_firebase_id_token("fake.wrong_aud.jwt")
            self.assertIsNone(result)

    def test_expired_token_rejection(self):
        """Underlying verify_firebase_token raises InvalidValue on expired tokens."""
        with patch("app.core.security.id_token.verify_firebase_token", side_effect=g_exc.InvalidValue("Token expired")):
            result = verify_firebase_id_token("fake.expired.jwt")
            self.assertIsNone(result)

    def test_malformed_token_rejection(self):
        """Malformed JWT syntax raises MalformedError, returning None."""
        with patch("app.core.security.id_token.verify_firebase_token", side_effect=g_exc.MalformedError("Malformed JWT")):
            result = verify_firebase_id_token("not-a-token")
            self.assertIsNone(result)

    def test_network_and_transport_error_handling(self):
        """Network/transport failure fetching public certs must not crash or leak info."""
        with patch("app.core.security.id_token.verify_firebase_token", side_effect=g_exc.TransportError("DNS failure")):
            result = verify_firebase_id_token("fake.jwt")
            self.assertIsNone(result)

    def test_hs256_backward_compatibility(self):
        """Local HS256 tokens are unaffected and maintain full backward compatibility."""
        payload = {"sub": "local_dev_user", "email": "dev@pluto.local", "name": "Local Dev"}
        token = create_access_token(payload)

        # verify_access_token works
        verified_local = verify_access_token(token)
        self.assertIsNotNone(verified_local)
        self.assertEqual(verified_local["sub"], "local_dev_user")

        # verify_token recognizes HS256 and marks is_firebase=False
        resolved = verify_token(token)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["sub"], "local_dev_user")
        self.assertEqual(resolved["is_firebase"], False)

    def test_unified_verify_token_routes_correctly(self):
        """verify_token correctly routes RS256 to Firebase verifier and marks is_firebase=True."""
        mock_claims = {
            "iss": "https://securetoken.google.com/plutochatbot",
            "aud": "plutochatbot",
            "sub": "firebase_uid_999",
            "email": "user999@test.com",
            "name": "User 999",
        }

        # RS256 token header
        rs256_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyOTk5In0.sig"
        with patch("app.core.security.id_token.verify_firebase_token", return_value=mock_claims.copy()):
            resolved = verify_token(rs256_token)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved["uid"], "firebase_uid_999")
            self.assertEqual(resolved["is_firebase"], True)
            self.assertEqual(resolved["email"], "user999@test.com")

if __name__ == "__main__":
    unittest.main()
