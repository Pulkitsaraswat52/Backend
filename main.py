import os
import shutil
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import face_recognition
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session, joinedload
from passlib.context import CryptContext
from jose import jwt, JWTError

import models
from database import SessionLocal, engine, get_db
from schemas import UserCreate
from seed_roles import seed_roles as _seed_roles

# ---------------- CONFIG ----------------
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"
COOKIE_NAME = "access_token"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # one day
UPLOAD_DIR = "saved_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- APP ----------------
app = FastAPI(title="Face Recognition Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/saved_images", StaticFiles(directory=UPLOAD_DIR), name="saved_images")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============== Anti-Spoof CNN ==============
class SimpleAntiSpoofCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.fc1 = nn.Linear(64 * 6 * 6, 128)
        self.fc2 = nn.Linear(128, 2)

    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = torch.max_pool2d(x, 2)
        x = torch.relu(self.conv2(x))
        x = torch.max_pool2d(x, 2)
        x = torch.flatten(x, 1)
        x = torch.relu(self.fc1(x))
        return self.fc2(x)


def load_model(path="models/Silent-Face-AntiSpoofing.pth"):
    if not os.path.exists(path):
        print(f"⚠️ Warning: '{path}' not found. Liveness check disabled.")
        return None
    model = SimpleAntiSpoofCNN()
    model.load_state_dict(torch.load(path, map_location="cpu"))
    model.eval()
    return model


cnn_model = load_model()


def liveness_check(image_path, model):
    if model is None:
        return True
    transform = transforms.Compose([
        transforms.Resize((32, 32)),
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,)),
    ])
    img = Image.open(image_path).convert("RGB")
    img_tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        output = model(img_tensor)
        pred = torch.argmax(output, dim=1).item()
    return pred == 1


# ------------- DB INIT -------------
models.Base.metadata.create_all(bind=engine)

# ------------- JWT TOKEN UTIL -------------
def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode({"sub": subject, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def set_token_cookie(response: Response, token: str):
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def delete_token_cookie(response: Response):
    response.delete_cookie(COOKIE_NAME)


# ------------- AUTH MIDDLEWARE -------------
PUBLIC_PATHS = ["/login", "/register", "/face-login", "/logout", "/docs", "/openapi.json", "/ws"]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return Response("Unauthorized: Missing token", status_code=401)

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                return Response("Unauthorized: Invalid token payload", status_code=401)

            db = SessionLocal()
            user = db.query(models.User).options(joinedload(models.User.role)).filter(models.User.username == username).first()
            db.close()

            if not user:
                return Response("Unauthorized: user not found", status_code=401)

            request.state.user = user
        except JWTError:
            return Response("Unauthorized: JWT decode error", status_code=401)
        except Exception:
            return Response("Unauthorized: error retrieving user", status_code=401)

        return await call_next(request)

app.add_middleware(AuthMiddleware)

# ------------- WEBSOCKET SUPPORT -------------
clients: list[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Accept connection from React frontend
    await websocket.accept()
    clients.append(websocket)
    print("✅ WebSocket client connected:", websocket.client)

    try:
        while True:
            msg = await websocket.receive_text()
            print(f"📩 Received: {msg}")
            await websocket.send_text(f"Server echo: {msg}")
    except WebSocketDisconnect:
        clients.remove(websocket)
        print("❌ WebSocket client disconnected")

async def broadcast_message(message: str):
    """Send a message to all connected WebSocket clients"""
    disconnected = []
    for client in clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        clients.remove(client)

# ------------- STARTUP SEED ROLES -------------
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        _seed_roles(db)
    finally:
        db.close()

# ============= ROUTES =============
# (your existing /register, /face-login, /login, /logout, /me, /faces, /entries routes remain unchanged)



# ------------- AUTH MIDDLEWARE -------------
PUBLIC_PATHS = ["/login", "/register", "/face-login", "/logout", "/docs", "/openapi.json", "/ws"]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return Response("Unauthorized: Missing token", status_code=401)

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                return Response("Unauthorized: Invalid token payload", status_code=401)

            db = SessionLocal()
            user = db.query(models.User).options(joinedload(models.User.role)).filter(models.User.username == username).first()
            db.close()

            if not user:
                return Response("Unauthorized: user not found", status_code=401)

            request.state.user = user
        except JWTError:
            return Response("Unauthorized: JWT decode error", status_code=401)
        except Exception:
            return Response("Unauthorized: error retrieving user", status_code=401)

        return await call_next(request)

app.add_middleware(AuthMiddleware)

# ------------- WEBSOCKET SUPPORT -------------
clients: list[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            # Echo message (optional)
            await websocket.send_text(f"Server received: {msg}")
    except WebSocketDisconnect:
        clients.remove(websocket)

async def broadcast_message(message: str):
    """Send a message to all connected WebSocket clients"""
    disconnected = []
    for client in clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        clients.remove(client)

# ------------- STARTUP SEED ROLES -------------
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        _seed_roles(db)
    finally:
        db.close()

# ============= ROUTES =============

@app.post("/register/")
async def register_user(
    username: str = Form(...),
    password: str = Form(...),
    file: UploadFile = File(...),
    role_name: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.lower().strip()
    role_name = role_name.lower().strip()

    if role_name not in ["admin", "employee"]:
        raise HTTPException(400, detail="Invalid role. Allowed roles: admin, employee")
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(400, detail="Username already exists")

    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        raise HTTPException(400, detail="Role not found in database")

    img_path = os.path.join(UPLOAD_DIR, f"{username}.jpg")
    with open(img_path, "wb") as f_out:
        shutil.copyfileobj(file.file, f_out)

    if not liveness_check(img_path, cnn_model):
        os.remove(img_path)
        raise HTTPException(400, detail="Liveness check failed (spoof detected)")

    img = face_recognition.load_image_file(img_path)
    encodings = face_recognition.face_encodings(img)
    if not encodings:
        os.remove(img_path)
        raise HTTPException(400, detail="No face found in image")

    encoding = encodings[0]
    existing = db.query(models.FaceData).all()
    for f in existing:
        stored_enc = np.array(f.encoding)
        if face_recognition.compare_faces([stored_enc], encoding, tolerance=0.4)[0]:
            os.remove(img_path)
            raise HTTPException(400, detail="Duplicate face detected")

    try:
        new_user = models.User(username=username, password_hash=pwd_context.hash(password), role_id=role.id)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        face_entry = models.FaceData(user_id=new_user.id, encoding=encoding.tolist(), image_link=f"saved_images/{username}.jpg")
        db.add(face_entry)
        db.commit()

        # 🔔 Notify via WebSocket
        await broadcast_message(f"New user registered: {username} ({role.name})")

    except Exception as e:
        db.rollback()
        if os.path.exists(img_path):
            os.remove(img_path)
        raise HTTPException(500, detail="Registration failed: " + str(e))

    return {"success": True, "message": f"User '{username}' registered as '{role.name}'"}


@app.post("/face-login/")
async def face_login(response: Response, file: UploadFile = File(...), db: Session = Depends(get_db)):
    tmp_path = os.path.join(UPLOAD_DIR, "tmp_login.jpg")
    with open(tmp_path, "wb") as f_out:
        shutil.copyfileobj(file.file, f_out)
    try:
        img = face_recognition.load_image_file(tmp_path)
        enc = face_recognition.face_encodings(img)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    if not enc:
        raise HTTPException(400, detail="No face detected in login image")

    for f in db.query(models.FaceData).all():
        if face_recognition.compare_faces([np.array(f.encoding)], enc[0], tolerance=0.6)[0]:
            user = db.query(models.User).options(joinedload(models.User.role)).filter(models.User.id == f.user_id).first()
            if not user:
                raise HTTPException(500, detail="Matched face points to missing user")
            role_name = user.role.name if user.role else "unassigned"
            token = create_access_token(user.username)
            set_token_cookie(response, token)

            # 🔔 Notify WebSocket
            await broadcast_message(f"User logged in: {user.username} ({role_name})")

            return {"success": True, "username": user.username, "role": role_name}
    raise HTTPException(401, detail="Face not recognized")


@app.post("/login/")
async def login(response: Response, creds: UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).options(joinedload(models.User.role)).filter(models.User.username == creds.username.lower().strip()).first()
    if not user or not pwd_context.verify(creds.password, user.password_hash):
        raise HTTPException(401, detail="Invalid credentials")
    role_name = user.role.name if user.role else "unassigned"
    token = create_access_token(user.username)
    set_token_cookie(response, token)

    # 🔔 Notify
    await broadcast_message(f"User logged in: {user.username} ({role_name})")

    return {"success": True, "username": user.username, "role": role_name}


@app.post("/logout/")
async def logout(response: Response, request: Request):
    delete_token_cookie(response)
    if hasattr(request.state, "user"):
        await broadcast_message(f"User logged out: {request.state.user.username}")
    return {"success": True, "message": "Logout successful"}


@app.get("/me/")
async def me(request: Request):
    u = request.state.user
    role_name = u.role.name if getattr(u, "role", None) else "unassigned"
    return {"id": u.id, "username": u.username, "role": role_name}


@app.get("/faces/")
async def get_faces(db: Session = Depends(get_db)):
    faces = db.query(models.FaceData).options(joinedload(models.FaceData.user)).all()
    result = []
    for f in faces:
        username = f.user.username if getattr(f, "user", None) else "unknown"
        result.append({"id": f.id, "username": username, "image_link": f.image_link})
    return result


@app.get("/entries/")
async def get_entries(db: Session = Depends(get_db)):
    users = db.query(models.User).options(joinedload(models.User.role)).all()
    result = []
    for u in users:
        role_name = u.role.name if getattr(u, "role", None) else "unassigned"
        result.append({"id": u.id, "username": u.username, "role": role_name})
    return result
