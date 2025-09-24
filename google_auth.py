import os
import time
import logging
from typing import Optional
from datetime import timedelta

import requests
from fastapi import Request, Response, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

import models
from database import SessionLocal

logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class GoogleAuth:
    def __init__(self, oauth_instance: OAuth, create_access_token_func, set_token_cookie_func):
        self.oauth = oauth_instance
        self.create_access_token = create_access_token_func
        self.set_token_cookie = set_token_cookie_func
        
        # Register Google OAuth
        self.oauth.register(
            name='google',
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )
    
    async def google_login(self, request: Request):
        """Initiate Google OAuth login"""
        redirect_uri = "http://localhost:8000/auth/google/callback"
        return await self.oauth.google.authorize_redirect(request, redirect_uri)
    
    async def google_callback(self, request: Request, response: Response, db: Session = Depends(get_db)):
        """Handle Google OAuth callback"""
        logger.info(f"Google callback request headers: {request.headers}")
        logger.info(f"Google callback query params: {request.query_params}")
        
        try:
            token = await self.oauth.google.authorize_access_token(request)
            user_info = token.get('userinfo')
            if not user_info:
                raise HTTPException(status_code=400, detail="Failed to fetch user info")
            
            email = user_info.get('email')
            name = user_info.get('name')
            
            # Check if user exists
            user = db.query(models.User).filter(models.User.username == email).first()
            if not user:
                # Create new user
                user = models.User(username=email, password_hash="")  # No password for OAuth users
                db.add(user)
                db.commit()
                db.refresh(user)
            
            # Create access token
            access_token = self.create_access_token(subject=user.username)
            self.set_token_cookie(response, access_token)
            
            # Redirect to frontend after successful login
            return Response(
                content=f"""
                <html>
                    <body>
                        <script>
                            window.opener.postMessage({{
                                type: 'GOOGLE_LOGIN_SUCCESS',
                                user: {{ email: '{email}', name: '{name}' }}
                            }}, 'http://localhost:3000');
                            window.close();
                        </script>
                    </body>
                </html>
                """,
                media_type="text/html"
            )
        except Exception as e:
            logger.error(f"Google callback error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
    
    async def verify_google_token(self, response: Response, token_data: dict = Body(...), db: Session = Depends(get_db)):
        """Verify Google JWT token sent from frontend"""
        logger.info(f"Received token data: {token_data}")
        
        try:
            token = token_data.get('token')
            if not token:
                logger.error("Token not provided in request")
                raise HTTPException(status_code=400, detail="Token not provided")
            
            # Check server time synchronization
            try:
                server_time = int(time.time())
                time_response = requests.get("http://worldtimeapi.org/api/timezone/Etc/UTC", timeout=5)
                world_time = time_response.json().get("unixtime")
                time_diff = abs(server_time - world_time)
                if time_diff > 5:
                    logger.warning(f"Server clock is off by {time_diff} seconds. Please synchronize system time.")
            except Exception as e:
                logger.warning(f"Failed to check server time: {str(e)}")

            logger.info(f"Verifying token with Google Client ID: {os.getenv('GOOGLE_CLIENT_ID')}")
            
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                os.getenv("GOOGLE_CLIENT_ID")
            )
            
            logger.info(f"Token verification successful. ID info: {idinfo}")
            email = idinfo.get('email')
            name = idinfo.get('name')
            
            if not email:
                logger.error("Email not found in token")
                raise HTTPException(status_code=400, detail="Email not found in token")
            
            # Check if user exists, create if not
            user = db.query(models.User).filter(models.User.username == email).first()
            if not user:
                logger.info(f"Creating new user with email: {email}")
                user = models.User(username=email, password_hash="")
                db.add(user)
                db.commit()
                db.refresh(user)
            else:
                logger.info(f"User found: {email}")
            
            # Create access token
            access_token = self.create_access_token(subject=user.username)
            self.set_token_cookie(response, access_token)
            
            logger.info(f"Login successful for user: {email}")
            return {
                "access_token": access_token, 
                "token_type": "bearer", 
                "user": {"username": email, "name": name}
            }
            
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Token verification failed: {str(e)}")
