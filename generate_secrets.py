import secrets

# Generate secure random strings
session_secret = secrets.token_urlsafe(32)
jwt_secret = secrets.token_urlsafe(32)

print(f"SESSION_SECRET={session_secret}")
print(f"JWT_SECRET={jwt_secret}")
