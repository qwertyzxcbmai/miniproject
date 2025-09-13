from flask import Flask, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from models import db, Product
from datetime import datetime, timedelta
import bcrypt
import jwt
from fastapi import FastAPI, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from jwt import PyJWTError, ExpiredSignatureError
from fastapi import Cookie
import os
import secrets
import uvicorn
import models
from database import SessionLocal, engine
from fastapi import Form
from sqlalchemy import create_engine, text
from fastapi import HTTPException
from typing import Optional
#========================================================
app = FastAPI(title="LUNOR")
app = Flask(__name__)
app.config["SECRET_KEY"] = "supesecret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db.init_app(app)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

#================================================================
@app.route("/")
def index():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("index.html", products=products)

@app.route("/product/<int:product_id>")
def product_detail(product_id: int):
    product = Product.query.get_or_404(product_id)
    return render_template("product.html", product=product)

@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id: int):
    cart = session.get("cart", [])
    cart.append(product_id)
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/cart")
def cart():
    cart_ids = session.get("cart", [])
    items = Product.query.filter(Product.id.in_(cart_ids)).all() if cart_ids else []
    return render_template("cart.html", items=items)

@app.route("/checkout", methods=["POST"])
def checkout():
    session["cart"] = []
    return render_template("order_success.html")

def seed_data():
    if Product.query.first():
        return
    products = [
        Product(name="Увлажняющий крем", category="Крем", price=350,
                description="Питает и интенсивно увлажняет кожу лица."),
        Product(name="Очищающая пенка", category="Очищение", price=280,
                description="Мягко удаляет загрязнения и не сушит кожу."),
        Product(name="Тоник с ромашкой", category="Тоник", price=220,
                description="Успокаивает, снимает покраснения и освежает."),
        Product(name="Сыворотка с витамином C", category="Сыворотка", price=450,
                description="Выравнивает тон и придаёт сияние."),
    ]
    db.session.add_all(products)
    db.session.commit()
#============mine=============
@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})
    
@app.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("token")
    return response

@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request}, status_code=200)


@app.get("/accessibility", response_class=HTMLResponse)
def accessibility(request: Request):
    return templates.TemplateResponse("accessibility.html", {"request": request})


@app.get("/faqs", response_class=HTMLResponse)
def accessibility(request: Request):
    return templates.TemplateResponse("faqs.html", {"request": request})


@app.get("/returns", response_class=HTMLResponse)
def accessibility(request: Request):
    return templates.TemplateResponse("returns.html", {"request": request})

@app.get("/account", response_class=HTMLResponse)
def account(request: Request, username: Optional[str] = Depends(get_current_user_from_cookie)):
    if not username:
        return RedirectResponse("/login?error=not_logged_in")
    return templates.TemplateResponse("account.html", {"request": request, "username": username})





if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True)
