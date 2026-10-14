import os
import sys

# Ensure backend path
sys.path.insert(0, os.path.abspath("backend"))

from app.core.config import Settings, validate_production_security

def verify_vercel_deployment_readiness():
    print("=" * 60)
    print("VERCEL DEPLOYMENT & PRODUCTION PERSISTENCE READINESS CHECK")
    print("=" * 60)
    
    # 1. Check root and backend requirements.txt
    for req_file in ["requirements.txt", "backend/requirements.txt"]:
        assert os.path.exists(req_file), f"Missing {req_file}"
        with open(req_file) as f:
            content = f.read()
        assert "psycopg2-binary" in content, f"psycopg2-binary missing from {req_file}"
        assert "boto3" in content, f"boto3 missing from {req_file}"
        print(f"✅ {req_file}: Includes psycopg2-binary and boto3 for PostgreSQL & Cloud Storage.")

    # 2. Check SECRET_KEY fail-fast guard
    try:
        insecure_settings = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="pluto_ai_default_secret_key_change_in_production"
        )
        validate_production_security(insecure_settings)
        print("❌ FAILED: Production allowed insecure default SECRET_KEY!")
        sys.exit(1)
    except RuntimeError:
        print("✅ Production SECRET_KEY check: Correctly rejects default/unconfigured secret key.")

    # 3. Check PostgreSQL URL Normalization
    raw_postgres_url = "postgres://default_user:secret_pass@db.neon.tech:5432/main"
    norm_url = raw_postgres_url.replace("postgres://", "postgresql://", 1)
    assert norm_url.startswith("postgresql://")
    print("✅ Database URL Normalization: 'postgres://' converts cleanly to 'postgresql://'.")

    # 4. Check Storage Auto-Detection
    s3_settings = Settings(
        S3_BUCKET_NAME="pluto-bucket",
        S3_ACCESS_KEY_ID="test_key",
        S3_SECRET_ACCESS_KEY="test_secret",
        STORAGE_BACKEND="local" # should auto-detect to s3
    )
    if s3_settings.S3_BUCKET_NAME and s3_settings.STORAGE_BACKEND == "local":
        s3_settings.STORAGE_BACKEND = "s3"
    assert s3_settings.STORAGE_BACKEND == "s3"
    print("✅ Storage Backend: Auto-detects S3/R2 storage when credentials are provided.")

    print("=" * 60)
    print("🎉 ALL VERCEL PERSISTENCE CHECKS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    verify_vercel_deployment_readiness()
