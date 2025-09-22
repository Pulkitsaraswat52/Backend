from fastapi import HTTPException, Request, Depends, Response
from jose import jwt, JWTError
from sqlalchemy.orm import Session, contains_eager
from starlette.middleware.base import BaseHTTPMiddleware
import models
from database import SessionLocal
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Configuration
SECRET_KEY = "your_secret_key"  # Replace with your actual secret in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
COOKIE_NAME = "access_token"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Password hashing utilities
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# JWT utilities
def create_access_token(subject: str, expires_delta=None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Cookie management
def set_token_cookie(response: Response, token: str):
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=True,  # Use False if testing without HTTPS
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

def delete_token_cookie(response: Response):
    response.delete_cookie(COOKIE_NAME)

# Auth Middleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS middleware (adjust to your frontend URL)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public paths
        public_paths = ["/login", "/register", "/verify", "/logout", "/docs", "/openapi.json"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return Response("Unauthorized", status_code=401)
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                return Response("Unauthorized", status_code=401)
            
            db = SessionLocal()
            user = (
                db.query(models.User)
                .filter(models.User.username == username)
                .join(models.User.role)
                .options(contains_eager(models.User.role))
                .first()
            )
            db.close()
            
            if not user:
                return Response("Unauthorized", status_code=401)
            
            request.state.user = user
        except JWTError:
            return Response("Unauthorized", status_code=401)
        
        return await call_next(request)

app.add_middleware(AuthMiddleware)

# Dependency for fetching current user with loaded role (to use in routes)
def get_current_user_from_cookie(
    request: Request,
    db: Session = Depends(SessionLocal),
):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = (
        db.query(models.User)
        .filter(models.User.username == username)
        .join(models.User.role)
        .options(contains_eager(models.User.role))
        .first()
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user
