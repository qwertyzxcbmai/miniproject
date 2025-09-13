from pydantic import BaseModel, constr
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), nullable=True)
    price = db.Column(db.Integer, nullable=False)  # цена в грн (целое для простоты)
    description = db.Column(db.String(500), nullable=False)
    
class UserRegister(BaseModel):
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=6)
    country: str
