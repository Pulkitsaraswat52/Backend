from pydantic import BaseModel, constr

class UserCreate(BaseModel):
    username: constr(strip_whitespace=True, min_length=3, max_length=30)
    password: constr(strip_whitespace=True, min_length=6)
