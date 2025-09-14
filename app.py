from fastapi import FastAPI, Depends, status, Request, Form, HTTPException, Cookie
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from jwt import PyJWTError, ExpiredSignatureError
import os
import secrets
import uvicorn
import models
from database import SessionLocal, engine
from sqlalchemy import create_engine, text
from typing import Optional
from datetime import datetime, timedelta
import bcrypt
import jwt
import json
from pydantic import BaseModel

# ===== Database setup =====
sephora_engine = create_engine('sqlite:///sephora_products.db')
skincare_engine = create_engine('sqlite:///skincare_sample.db')
models.Base.metadata.create_all(bind=engine)

# ===== Configuration =====
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="LUNOR")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ===== Cart  =====
class CartItem(BaseModel):
    product_id: int
    quantity: int


def get_cart_from_cookie(cart_cookie: Optional[str] = Cookie(None)) -> list:
    if not cart_cookie:
        return []
    try:
        return json.loads(cart_cookie)
    except:
        return []


def set_cart_cookie(response: RedirectResponse, cart: list):
    response.set_cookie(
        key="cart",
        value=json.dumps(cart),
        httponly=True,
        secure=False,
        samesite="lax"
    )


# ======== DB ========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======== JWT ========
def create_jwt(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def get_current_user_from_cookie(token: Optional[str] = Cookie(None)) -> Optional[str]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except ExpiredSignatureError:
        return None
    except PyJWTError:
        return None
    except Exception as e:
        print(f"Unexpected error in token validation: {e}")
        return None


# ======== ROUTES ========
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, username: Optional[str] = Depends(get_current_user_from_cookie)):
    try:
        with skincare_engine.connect() as connection:
            query = text("""
                SELECT product_id, product_name, brand_name, rating, reviews, 
                       price_usd, sale_price_usd, image_url 
                FROM products 
                WHERE brand_name LIKE '%Herbivore%' 
                AND rating IS NOT NULL 
                ORDER BY rating DESC, reviews DESC 
                LIMIT 3
            """)
            result = connection.execute(query)
            herbivore_products = [dict(row._mapping) for row in result]
    except Exception as e:
        print(f"Error fetching Herbivore products: {e}")
        herbivore_products = []

    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": username,
        "herbivore_products": herbivore_products
    })


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request, username: Optional[str] = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("about.html", {
        "request": request,
        "username": username
    })


# ======== Cart  ========
@app.get("/cart", response_class=HTMLResponse)
async def cart(request: Request,
               username: Optional[str] = Depends(get_current_user_from_cookie),
               cart_cookie: Optional[str] = Cookie(None)):
    cart_items = get_cart_from_cookie(cart_cookie)
    items = []

    if cart_items:
        try:
            with skincare_engine.connect() as connection:
                product_ids = [item['product_id'] for item in cart_items]
                placeholders = ', '.join([':id' + str(i) for i in range(len(product_ids))])
                query = text(f"""
                    SELECT product_id, product_name, brand_name, price_usd, sale_price_usd, image_url
                    FROM products 
                    WHERE product_id IN ({placeholders})
                """)
                params = {f'id{i}': pid for i, pid in enumerate(product_ids)}
                result = connection.execute(query, params)

                product_dict = {row.product_id: dict(row._mapping) for row in result}
                for item in cart_items:
                    if item['product_id'] in product_dict:
                        product_info = product_dict[item['product_id']]
                        product_info['quantity'] = item['quantity']
                        items.append(product_info)
        except Exception as e:
            print(f"Error fetching cart items: {e}")

    return templates.TemplateResponse("cart.html", {
        "request": request,
        "username": username,
        "items": items
    })


@app.get("/add_to_cart/{product_id}")
async def add_to_cart(product_id: int,
                      response: RedirectResponse = RedirectResponse(url="/cart")):

    cart_cookie = get_cart_from_cookie()
    cart_items = cart_cookie.copy()

    found = False
    for item in cart_items:
        if item['product_id'] == product_id:
            item['quantity'] += 1
            found = True
            break

    if not found:
        cart_items.append({'product_id': product_id, 'quantity': 1})

    set_cart_cookie(response, cart_items)
    return response


@app.post("/checkout")
async def checkout(response: RedirectResponse = RedirectResponse(url="/")):
    # Clear the cart
    set_cart_cookie(response, [])
    return response


# ======== AUTH ========
@app.get("/register", response_class=HTMLResponse)
def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
def register(
        username: str = Form(..., min_length=3, max_length=50),
        password: str = Form(..., min_length=6),
        country: str = Form(..., min_length=2, max_length=50),
        db: Session = Depends(get_db)
):
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = hash_password(password)
    new_user = models.User(
        username=username,
        hashed_password=hashed_password,
        country=country
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_jwt({"sub": new_user.username})
    response = RedirectResponse(url="/account", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="token", value=token, httponly=True, secure=False, samesite="lax")
    return response


@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if not db_user or not verify_password(password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_jwt({"sub": db_user.username})
    response = RedirectResponse(url="/account", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="token", value=token, httponly=True, secure=False, samesite="lax")
    return response


# ===== account ======
@app.get("/account", response_class=HTMLResponse)
def account(request: Request, username: Optional[str] = Depends(get_current_user_from_cookie)):
    if not username:
        return RedirectResponse("/login?error=not_logged_in")
    return templates.TemplateResponse("account.html", {"request": request, "username": username})


# ==================
@app.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("token")
    return response


# ===== Additional Pages =====
@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request, username: Optional[str] = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("privacy.html", {
        "request": request,
        "username": username
    })


@app.get("/accessibility", response_class=HTMLResponse)
def accessibility(request: Request, username: Optional[str] = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("accessibility.html", {
        "request": request,
        "username": username
    })


@app.get("/faqs", response_class=HTMLResponse)
def faqs(request: Request, username: Optional[str] = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("faqs.html", {
        "request": request,
        "username": username
    })


@app.get("/returns", response_class=HTMLResponse)
def returns(request: Request, username: Optional[str] = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("returns.html", {
        "request": request,
        "username": username
    })


# ===== product =====
@app.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(
        request: Request,
        product_id: str,
        username: Optional[str] = Depends(get_current_user_from_cookie)
):
    try:
        with skincare_engine.connect() as connection:
            query = text("""
                SELECT * FROM products 
                WHERE product_id = :product_id
            """)
            result = connection.execute(query, {"product_id": product_id})
            product_row = result.mappings().first()

            if not product_row:
                raise HTTPException(status_code=404, detail="Product not found")

            product = dict(product_row)

    except Exception as e:
        print(f"Error fetching product: {e}")
        raise HTTPException(status_code=404, detail="Product not found")

    return templates.TemplateResponse("product.html", {
        "request": request,
        "username": username,
        "product": product
    })


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
