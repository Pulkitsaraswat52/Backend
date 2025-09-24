# from fastapi import FastAPI, HTTPException, Depends, Request
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from fastapi.responses import HTMLResponse
# from fastapi.staticfiles import StaticFiles
# from pydantic import BaseModel
# import jwt
# import bcrypt
# import psycopg2
# from psycopg2 import sql
# import datetime
# import os
# from dotenv import load_dotenv

# load_dotenv()

# app = FastAPI()

# # Environment variables
# SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key")
# DB_CONFIG = {
#     "dbname": os.getenv("DB_NAME", "auth_db"),
#     "user": os.getenv("DB_USER", "postgres"),
#     "password": os.getenv("DB_PASSWORD", "12345"),
#     "host": os.getenv("DB_HOST", "localhost"),
#     "port": os.getenv("DB_PORT", "5432")
# }

# # Security scheme
# security = HTTPBearer()

# # Pydantic models for request validation
# class UserSignup(BaseModel):
#     email: str
#     password: str
#     role: str = "user"

# class UserLogin(BaseModel):
#     email: str
#     password: str

# # Database connection
# def get_db_connection():
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         return conn
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# # Initialize database
# def init_db():
#     conn = get_db_connection()
#     cur = conn.cursor()
#     try:
#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS users (
#                 id SERIAL PRIMARY KEY,
#                 email VARCHAR(255) UNIQUE NOT NULL,
#                 password_hash VARCHAR(255) NOT NULL,
#                 role VARCHAR(50) NOT NULL
#             );
#             CREATE TABLE IF NOT EXISTS tokens (
#                 id SERIAL PRIMARY KEY,
#                 user_id INTEGER REFERENCES users(id),
#                 token TEXT NOT NULL,
#                 created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
#                 expires_at TIMESTAMP WITH TIME ZONE NOT NULL
#             );
#         """)
#         conn.commit()
#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")
#     finally:
#         cur.close()
#         conn.close()

# # Initialize database on startup
# init_db()

# # Mount static files directory AFTER defining the routes
# # This ensures that the root route "/" takes precedence over static files
# @app.get("/", response_class=HTMLResponse)
# async def get_login_page():
#     try:
#         # Check if the static directory exists
#         if not os.path.exists("static"):
#             raise HTTPException(status_code=500, detail="Static directory not found. Please create a 'static' folder in your project root.")
        
#         # Check if index.html exists
#         if not os.path.exists("static/index.html"):
#             raise HTTPException(status_code=500, detail="Frontend file (static/index.html) not found. Please create index.html in the static directory.")
        
#         with open("static/index.html", "r", encoding="utf-8") as f:
#             content = f.read()
#             return HTMLResponse(content=content)
#     except FileNotFoundError:
#         raise HTTPException(status_code=500, detail="Frontend file (static/index.html) not found. Ensure it exists in the static directory.")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error loading frontend: {str(e)}")

# @app.post("/signup")
# async def signup(user: UserSignup):
#     conn = get_db_connection()
#     cur = conn.cursor()
#     try:
#         # Check if email already exists
#         cur.execute(sql.SQL("SELECT id FROM users WHERE email = %s"), (user.email,))
#         if cur.fetchone():
#             raise HTTPException(status_code=400, detail="Email already exists")
        
#         # Hash password
#         hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
#         # Insert user into database
#         cur.execute(
#             sql.SQL("INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s) RETURNING id"),
#             (user.email, hashed_password, user.role)
#         )
#         user_id = cur.fetchone()[0]
#         conn.commit()
        
#         # Generate JWT
#         expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
#         payload = {
#             "email": user.email,
#             "role": user.role,
#             "exp": expires_at
#         }
#         token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
#         # Store token in database
#         cur.execute(
#             sql.SQL("INSERT INTO tokens (user_id, token, expires_at) VALUES (%s, %s, %s)"),
#             (user_id, token, expires_at)
#         )
#         conn.commit()
        
#         return {"message": "User created successfully", "token": token}
#     except HTTPException:
#         raise
#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")
#     finally:
#         cur.close()
#         conn.close()

# @app.post("/login")
# async def login(user: UserLogin):
#     conn = get_db_connection()
#     cur = conn.cursor()
#     try:
#         cur.execute(
#             sql.SQL("SELECT id, password_hash, role FROM users WHERE email = %s"),
#             (user.email,)
#         )
#         result = cur.fetchone()
#         if not result or not bcrypt.checkpw(user.password.encode('utf-8'), result[1].encode('utf-8')):
#             raise HTTPException(status_code=401, detail="Invalid email or password")
        
#         user_id, _, role = result
        
#         # Generate JWT
#         expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
#         payload = {
#             "email": user.email,
#             "role": role,
#             "exp": expires_at
#         }
#         token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
#         # Store token in database
#         cur.execute(
#             sql.SQL("INSERT INTO tokens (user_id, token, expires_at) VALUES (%s, %s, %s)"),
#             (user_id, token, expires_at)
#         )
#         conn.commit()
        
#         return {"token": token}
#     except HTTPException:
#         raise
#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
#     finally:
#         cur.close()
#         conn.close()

# @app.get("/verify")
# async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
#     token = credentials.credentials
#     conn = get_db_connection()
#     cur = conn.cursor()
#     try:
#         # Check if token exists in database and is not expired
#         cur.execute(
#             sql.SQL("SELECT expires_at FROM tokens WHERE token = %s"),
#             (token,)
#         )
#         result = cur.fetchone()
#         if not result:
#             raise HTTPException(status_code=401, detail="Token not found in database")
#         expires_at = result[0]
#         if expires_at < datetime.datetime.now(datetime.timezone.utc):
#             raise HTTPException(status_code=401, detail="Token has expired")
        
#         # Decode JWT
#         payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
#         return {"status": "200", "payload": payload}
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token has expired")
#     except jwt.InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid token")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")
#     finally:
#         cur.close()
#         conn.close()

# # Mount static files directory AFTER defining all routes
# app.mount("/static", StaticFiles(directory="static"), name="static")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)




from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import jwt
import bcrypt
import psycopg2
from psycopg2 import sql
import datetime
import os
from dotenv import load_dotenv
from enum import Enum

load_dotenv()

app = FastAPI()

# Environment variables
SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key")
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "auth_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "12345"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

# Security scheme
security = HTTPBearer()

# Models
class UserSignup(BaseModel):
    email: str
    password: str
    role: str = "user"

class UserLogin(BaseModel):
    email: str
    password: str

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# Initialize database
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            );
            CREATE TABLE IF NOT EXISTS tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                token TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL
            );
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")
    finally:
        cur.close()
        conn.close()

init_db()

# IMPROVED JWT TOKEN AUTHENTICATION
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Extract JWT token and return user info WITHOUT database calls for better performance.
    Token contains all necessary user information.
    """
    token = credentials.credentials
    
    try:
        # Decode JWT token - this contains all user info
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        # Extract user info from JWT payload (no database call needed)
        user_info = {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "exp": payload.get("exp")
        }
        
        # Check if token is expired (JWT also checks this, but we can add custom logic)
        if datetime.datetime.fromtimestamp(user_info["exp"], datetime.timezone.utc) < datetime.datetime.now(datetime.timezone.utc):
            raise HTTPException(status_code=401, detail="Token has expired")
            
        return user_info
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token validation failed: {str(e)}")

def get_current_user_with_db_validation(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Alternative: Validate token against database (more secure but slower)
    Use this for high-security routes where you need to ensure token wasn't revoked
    """
    token = credentials.credentials
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # First check if token exists in database and is not expired
        cur.execute(
            sql.SQL("SELECT user_id, expires_at FROM tokens WHERE token = %s"),
            (token,)
        )
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=401, detail="Token not found or has been revoked")
        
        user_id, expires_at = result
        if expires_at < datetime.datetime.now(datetime.timezone.utc):
            raise HTTPException(status_code=401, detail="Token has expired")
        
        # Decode JWT to get user info
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        return {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "exp": payload.get("exp")
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")
    finally:
        cur.close()
        conn.close()

# Role-based authorization
def require_role(required_role: str):
    def role_checker(current_user = Depends(get_current_user)):
        if current_user["role"] != required_role:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user
    return role_checker

def require_any_role(required_roles: List[str]):
    def role_checker(current_user = Depends(get_current_user)):
        if current_user["role"] not in required_roles:
            roles_str = ", ".join(required_roles)
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied. Required roles: {roles_str}"
            )
        return current_user
    return role_checker

# PUBLIC ROUTES
@app.get("/")
async def root():
    return {"message": "JWT Auth API is running"}

@app.post("/signup")
async def signup(user: UserSignup):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Check if email exists
        cur.execute(sql.SQL("SELECT id FROM users WHERE email = %s"), (user.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Hash password
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insert user
        cur.execute(
            sql.SQL("INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s) RETURNING id"),
            (user.email, hashed_password, user.role)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        
        # Generate JWT with comprehensive user info
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        payload = {
            "user_id": user_id,          # Include user ID in token
            "email": user.email,
            "role": user.role,
            "iat": datetime.datetime.now(datetime.timezone.utc),  # Issued at
            "exp": expires_at            # Expiration
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
        # Store token in database
        cur.execute(
            sql.SQL("INSERT INTO tokens (user_id, token, expires_at) VALUES (%s, %s, %s)"),
            (user_id, token, expires_at)
        )
        conn.commit()
        
        return {
            "message": "User created successfully", 
            "token": token,
            "user": {
                "id": user_id,
                "email": user.email,
                "role": user.role
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")
    finally:
        cur.close()
        conn.close()

@app.post("/login")
async def login(user: UserLogin):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            sql.SQL("SELECT id, password_hash, role, is_active FROM users WHERE email = %s"),
            (user.email,)
        )
        result = cur.fetchone()
        if not result or not result[3]:
            raise HTTPException(status_code=401, detail="Invalid credentials or inactive account")
            
        if not bcrypt.checkpw(user.password.encode('utf-8'), result[1].encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user_id, _, role, _ = result
        
        # Generate JWT with comprehensive user info
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        payload = {
            "user_id": user_id,          # Include user ID in token
            "email": user.email,
            "role": role,
            "iat": datetime.datetime.now(datetime.timezone.utc),  # Issued at
            "exp": expires_at            # Expiration
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
        # Store token in database
        cur.execute(
            sql.SQL("INSERT INTO tokens (user_id, token, expires_at) VALUES (%s, %s, %s)"),
            (user_id, token, expires_at)
        )
        conn.commit()
        
        return {
            "token": token,
            "user": {
                "id": user_id,
                "email": user.email,
                "role": role
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
    finally:
        cur.close()
        conn.close()

# PROTECTED ROUTES - Using JWT token data directly (FAST & SECURE)

@app.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    """
    Fast protected route - uses JWT token data directly
    No database calls needed for basic user info
    """
    return {
        "message": "Access granted to protected resource",
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "token_expires": datetime.datetime.fromtimestamp(current_user["exp"], datetime.timezone.utc).isoformat()
    }

@app.get("/profile")
async def get_profile(current_user = Depends(get_current_user)):
    """
    User profile - all info comes from JWT token
    """
    return {
        "profile": {
            "id": current_user["user_id"],
            "email": current_user["email"],
            "role": current_user["role"],
            "authenticated": True
        },
        "token_info": {
            "expires_at": datetime.datetime.fromtimestamp(current_user["exp"], datetime.timezone.utc).isoformat()
        }
    }

@app.get("/dashboard")
async def user_dashboard(current_user = Depends(get_current_user)):
    """
    User dashboard - customized based on role from JWT
    """
    role = current_user["role"]
    
    dashboard_data = {
        "welcome_message": f"Welcome to your dashboard, {current_user['email']}!",
        "user_id": current_user["user_id"],
        "role": role,
        "features": []
    }
    
    # Customize dashboard based on role (from JWT token)
    if role == "admin":
        dashboard_data["features"] = ["user_management", "analytics", "system_config"]
    elif role == "manager":
        dashboard_data["features"] = ["team_management", "reports"]
    else:
        dashboard_data["features"] = ["basic_access", "profile"]
    
    return dashboard_data

@app.get("/user-data")
async def get_user_data(current_user = Depends(get_current_user)):
    """
    Get user-specific data using user_id from JWT
    """
    user_id = current_user["user_id"]
    
    # Use user_id for database queries instead of email/username
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Example: Get user's specific data using ID from token
        cur.execute(
            sql.SQL("SELECT created_at, is_active FROM users WHERE id = %s"),
            (user_id,)
        )
        user_details = cur.fetchone()
        
        if not user_details:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user_info": {
                "id": user_id,
                "email": current_user["email"],
                "role": current_user["role"],
                "created_at": user_details[0].isoformat() if user_details[0] else None,
                "is_active": user_details[1]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user data: {str(e)}")
    finally:
        cur.close()
        conn.close()

# HIGH-SECURITY ROUTES - Use database validation for critical operations
@app.get("/sensitive-data")
async def get_sensitive_data(current_user = Depends(get_current_user_with_db_validation)):
    """
    For sensitive operations, validate token against database
    This ensures token hasn't been revoked
    """
    return {
        "message": "Access to sensitive data granted",
        "user_id": current_user["user_id"],
        "security_level": "high",
        "note": "This route validates token against database"
    }

@app.delete("/account")
async def delete_account(current_user = Depends(get_current_user_with_db_validation)):
    """
    Critical operation - always validate against database
    """
    user_id = current_user["user_id"]
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Deactivate user account
        cur.execute(
            sql.SQL("UPDATE users SET is_active = FALSE WHERE id = %s"),
            (user_id,)
        )
        
        # Revoke all tokens for this user
        cur.execute(sql.SQL("DELETE FROM tokens WHERE user_id = %s"), (user_id,))
        conn.commit()
        
        return {"message": "Account deleted successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Account deletion failed: {str(e)}")
    finally:
        cur.close()
        conn.close()

# ROLE-BASED PROTECTED ROUTES
@app.get("/admin")
async def admin_only(current_user = Depends(require_role("admin"))):
    """
    Admin-only route - role checked from JWT token
    """
    return {
        "message": "Admin area access granted",
        "admin_email": current_user["email"],
        "admin_id": current_user["user_id"]
    }

@app.get("/manager-or-admin")
async def manager_or_admin(current_user = Depends(require_any_role(["admin", "manager"]))):
    """
    Multiple role access - checked from JWT token
    """
    return {
        "message": f"Management area access granted for {current_user['role']}",
        "user_id": current_user["user_id"],
        "email": current_user["email"]
    }

@app.get("/user-stats/{target_user_id}")
async def get_user_stats(target_user_id: int, current_user = Depends(get_current_user)):
    """
    Get stats for a specific user - authorize based on role from JWT
    """
    # Check if user can access other user's stats
    if current_user["role"] not in ["admin", "manager"] and current_user["user_id"] != target_user_id:
        raise HTTPException(status_code=403, detail="Can only access your own stats")
    
    return {
        "stats_for_user": target_user_id,
        "requested_by": current_user["email"],
        "requester_id": current_user["user_id"],
        "access_level": current_user["role"]
    }

# TOKEN UTILITIES
@app.get("/verify")
async def verify_token(current_user = Depends(get_current_user)):
    """
    Verify token validity - all info from JWT
    """
    return {
        "valid": True,
        "user": {
            "id": current_user["user_id"],
            "email": current_user["email"],
            "role": current_user["role"]
        },
        "expires_at": datetime.datetime.fromtimestamp(current_user["exp"], datetime.timezone.utc).isoformat()
    }

@app.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout - remove token from database
    """
    token = credentials.credentials
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql.SQL("DELETE FROM tokens WHERE token = %s"), (token,))
        conn.commit()
        return {"message": "Logged out successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")
    finally:
        cur.close()
        conn.close()

@app.post("/refresh-token")
async def refresh_token(current_user = Depends(get_current_user)):
    """
    Generate new token with extended expiry
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Generate new token
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
        payload = {
            "user_id": current_user["user_id"],
            "email": current_user["email"],
            "role": current_user["role"],
            "iat": datetime.datetime.now(datetime.timezone.utc),
            "exp": expires_at
        }
        new_token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
        # Store new token
        cur.execute(
            sql.SQL("INSERT INTO tokens (user_id, token, expires_at) VALUES (%s, %s, %s)"),
            (current_user["user_id"], new_token, expires_at)
        )
        conn.commit()
        
        return {
            "message": "Token refreshed successfully",
            "token": new_token,
            "expires_at": expires_at.isoformat()
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
