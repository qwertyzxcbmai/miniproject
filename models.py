from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from pydantic import BaseModel, constr
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)  
    street = Column(String, nullable=False)
    city = Column(String, nullable=False)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=False)

    user = relationship("User", back_populates="addresses")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    country = Column(String)

    addresses = relationship("Address", back_populates="user")


class UserRegister(BaseModel):
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=6)
    country: str


class Product(Base):
    __tablename__ = "products"

    product_id = Column(String, primary_key=True)
    product_name = Column(String)
    brand_id = Column(Integer)
    brand_name = Column(String)
    loves_count = Column(Integer)
    rating = Column(Float)
    reviews = Column(Float)
    size = Column(String)
    variation_type = Column(String)
    variation_value = Column(String)
    variation_desc = Column(Text)
    ingredients = Column(Text)
    price_usd = Column(Float)
    value_price_usd = Column(Float)
    sale_price_usd = Column(String)
    limited_edition = Column(Integer)
    new = Column(Integer)
    online_only = Column(Integer)
    out_of_stock = Column(Integer)
    sephora_exclusive = Column(Integer)
    highlights = Column(Text)
    primary_category = Column(String)
    secondary_category = Column(String)
    tertiary_category = Column(String)
    child_count = Column(Integer)
    child_max_price = Column(Float)
    child_min_price = Column(Float)
    image_filename = Column(String)
    image_path = Column(String)
    image_url = Column(String)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), nullable=True)
    price = db.Column(db.Integer, nullable=False)  # цена в грн (целое для простоты)
    description = db.Column(db.String(500), nullable=False)
