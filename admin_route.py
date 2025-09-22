from fastapi import APIRouter, Depends, HTTPException
import models
from auth import get_current_user_from_cookie

router = APIRouter()

@router.get("/admin-area")
def admin_area(user: models.User = Depends(get_current_user_from_cookie)):
    if user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"msg": f"Welcome admin {user.username}"}
