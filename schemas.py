from pydantic import BaseModel
from pydantic import BaseModel, Field, validator
from typing import Optional

from pydantic import BaseModel


class UserRegister(BaseModel):
    username: str
    password: str
    country: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
