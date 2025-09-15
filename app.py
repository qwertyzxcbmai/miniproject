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
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import re
from datetime import datetime, timedelta, timezone
from fastapi.responses import JSONResponse

# ===== Database setup =====

sephora_engine = create_engine('sqlite:///sephora_products.db')
skincare_engine = create_engine('sqlite:///skincare_sample.db')
models.Base.metadata.create_all(bind=engine)

# ===== JWT Configuration =====
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="LUNOR")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ===== Cart functionality =====
class CartItem(BaseModel):
    product_id: int
    quantity: int


def get_cart_from_cookie(request: Request, cart_cookie: Optional[str] = None) -> list:
    if cart_cookie is None:
        cart_cookie = request.cookies.get("cart")
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


def extract_name_from_email(email: str) -> str:
    name_part = email.split("@")[0]
    name_part = re.sub(r'[^A-Za-z_]', '', name_part)
    name_part = name_part.replace("_", " ")
    return name_part


# ======== DB session ========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======== JWT ========
def create_jwt(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
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


# ======== INDEX ========
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, username: Optional[str] = Depends(get_current_user_from_cookie)):
    try:
        with skincare_engine.connect() as connection:
            query1 = text("""
                SELECT product_id, product_name, brand_name, rating, reviews, 
                       price_usd, sale_price_usd, image_url 
                FROM products
                WHERE image_url IS NOT NULL
                ORDER BY RANDOM()
                LIMIT 12
            """)
            query2 = text("""
                SELECT product_id, product_name, brand_name, rating, reviews, 
                       price_usd, sale_price_usd, image_url 
                FROM products
                WHERE image_url IS NOT NULL
                ORDER BY RANDOM()
                LIMIT 8
            """)

            result1 = connection.execute(query1)
            result2 = connection.execute(query2)

            random_products1 = [dict(row._mapping) for row in result1]
            random_products2 = [dict(row._mapping) for row in result2]
    except Exception as e:
        print(f"Error fetching products: {e}")
        random_products1, random_products2 = [], []

    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": username,
        "random_products1": random_products1,
        "random_products2": random_products2
    })


# ======== Cart Routes ========
@app.get("/cart", response_class=HTMLResponse)
async def cart(request: Request,
               username: Optional[str] = Depends(get_current_user_from_cookie)):
    cart_items = get_cart_from_cookie(request)
    items = []

    if cart_items:
        try:
            with skincare_engine.connect() as connection:
                for item in cart_items:
                    query = text("""
                        SELECT product_id, product_name, brand_name, price_usd, sale_price_usd, image_url
                        FROM products 
                        WHERE product_id = :pid
                    """)
                    result = connection.execute(query, {"pid": item['product_id']})
                    product_row = result.mappings().first()
                    if product_row:
                        product_info = dict(product_row)
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
async def add_to_cart(
        request: Request,
        product_id: str
):
    cart_cookie = request.cookies.get("cart")
    cart_items = get_cart_from_cookie(request)

    found = False
    for item in cart_items:
        if item["product_id"] == product_id:
            item["quantity"] += 1
            found = True
            break

    if not found:
        cart_items.append({"product_id": product_id, "quantity": 1})

    response = RedirectResponse(url="/cart", status_code=302)
    set_cart_cookie(response, cart_items)
    return response


@app.post("/checkout")
async def checkout(response: RedirectResponse = RedirectResponse(url="/")):
    set_cart_cookie(response, [])
    return JSONResponse(content={"message": "Checkout successful"}, status_code=200)

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
def account(request: Request, db: Session = Depends(get_db),
            username: Optional[str] = Depends(get_current_user_from_cookie)):
    if not username:
        return RedirectResponse("/login?error=not_logged_in")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return RedirectResponse("/login?error=not_found")

    display_name = re.sub(r'[\d_]+', ' ', user.username.split("@")[0]).title()

    return templates.TemplateResponse("account.html", {
        "request": request,
        "username": display_name,
        "email": user.username,
        "country": user.country,
        "addresses": user.addresses
    })


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("token")
    return response


# =====  Pages =====
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


@app.get("/termsofservice", response_class=HTMLResponse)
def privacy(request: Request, username: Optional[str] = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("termsofservice.html", {
        "request": request,
        "username": username
    })


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request, username: Optional[str] = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("about.html", {
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


# =================================
@app.get("/shop", response_class=HTMLResponse)
async def shop(
        request: Request,
        page: int = 1,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        in_stock: bool = False,
        sort: str = "rating_desc",
        username: Optional[str] = Depends(get_current_user_from_cookie)
):
    try:
        with skincare_engine.connect() as connection:
            query = text("""
                SELECT product_id, product_name, brand_name, rating, reviews, 
                       price_usd, sale_price_usd, image_url, primary_category,
                       out_of_stock, new
                FROM products 
                WHERE 1=1
            """)

            conditions = []
            params = {}

            if category:
                conditions.append("primary_category = :category")
                params["category"] = category

            if brand:
                conditions.append("brand_name = :brand")
                params["brand"] = brand

            if max_price:
                conditions.append("COALESCE(NULLIF(sale_price_usd, 0), price_usd) <= :max_price")
                params["max_price"] = max_price

            if min_rating:
                conditions.append("rating >= :min_rating")
                params["min_rating"] = min_rating

            if in_stock:
                conditions.append("out_of_stock = 0")

            if conditions:
                query = text(str(query) + " AND " + " AND ".join(conditions))

            sort_mapping = {
                "rating_desc": "rating DESC, reviews DESC",
                "price_asc": "COALESCE(NULLIF(sale_price_usd, 0), price_usd) ASC",
                "price_desc": "COALESCE(NULLIF(sale_price_usd, 0), price_usd) DESC",
                "name_asc": "product_name ASC",
                "name_desc": "product_name DESC",
                "new": "new DESC, rating DESC"
            }
            order_by = sort_mapping.get(sort, "rating DESC, reviews DESC")

            per_page = 12
            offset = (page - 1) * per_page

            paginated_query = text(f"""
                WITH filtered_products AS (
                    {str(query)}
                )
                SELECT * FROM filtered_products
                ORDER BY {order_by}
                LIMIT :limit OFFSET :offset
            """)

            params["limit"] = per_page
            params["offset"] = offset

            result = connection.execute(paginated_query, params)
            products = [dict(row._mapping) for row in result]

            count_query = text(f"""
                SELECT COUNT(*) as total_count
                FROM products
                WHERE 1=1 {'AND ' + ' AND '.join(conditions) if conditions else ''}
            """)
            count_result = connection.execute(count_query,
                                              {k: v for k, v in params.items() if k not in ['limit', 'offset']})
            total_products = count_result.scalar() or 0
            total_pages = (total_products + per_page - 1) // per_page

            categories_result = connection.execute(text("""
                SELECT DISTINCT primary_category FROM products 
                WHERE primary_category IS NOT NULL 
                ORDER BY primary_category
            """))
            categories = [row[0] for row in categories_result if row[0]]

            brands_result = connection.execute(text("""
                SELECT DISTINCT brand_name FROM products 
                WHERE brand_name IS NOT NULL 
                ORDER BY brand_name
            """))
            brands = [row[0] for row in brands_result if row[0]]

            max_price_result = connection.execute(text("""
                SELECT MAX(COALESCE(NULLIF(sale_price_usd, 0), price_usd)) 
                FROM products 
                WHERE price_usd IS NOT NULL
            """))
            max_price_value = max_price_result.scalar() or 100

            random_query = text("""
                SELECT product_id, product_name, brand_name, price_usd, sale_price_usd, image_url
                FROM products
                ORDER BY RANDOM()
                LIMIT 20
            """)
            random_result = connection.execute(random_query)
            random_products = [dict(row._mapping) for row in random_result]

    except Exception as e:
        print(f"Error fetching products: {e}")
        products = []
        random_products = []
        categories = []
        brands = []
        total_products = 0
        total_pages = 1
        max_price_value = 100

    return templates.TemplateResponse("shop.html", {
        "request": request,
        "username": username,
        "products": products,
        "random_products": random_products,
        "categories": categories,
        "brands": brands,
        "total_products": total_products,
        "total_pages": total_pages,
        "page": page,
        "max_price": max_price_value,
        "current_filters": {
            "category": category,
            "brand": brand,
            "max_price": max_price,
            "min_rating": min_rating,
            "in_stock": in_stock,
            "sort": sort
        }
    })


# ======================================
@app.get("/search_products")
async def search_products(request: Request, q: str = ""):
    if not q or len(q) < 2:
        return []

    try:
        with skincare_engine.connect() as connection:
            query = text("""
                SELECT product_id, product_name, brand_name, image_url
                FROM products 
                WHERE product_name LIKE :query OR brand_name LIKE :query
                ORDER BY rating DESC, reviews DESC
                LIMIT 5
            """)
            result = connection.execute(query, {"query": f"%{q}%"})
            products = [dict(row._mapping) for row in result]
            return products
    except Exception as e:
        print(f"Error searching products: {e}")
        return []


# ===========Error================
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "status_code": exc.status_code, "detail": exc.detail},
        status_code=exc.status_code
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "status_code": 422, "detail": "Validation Error"},
        status_code=422
    )


@app.get("/error")
async def error():
    raise RuntimeError("Test server error")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
