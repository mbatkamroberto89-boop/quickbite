from fastapi import FastAPI
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base, engine
from fastapi import Request
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from fastapi.encoders import jsonable_encoder
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
templates = Jinja2Templates(directory="templates")
app = FastAPI()
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")

from fastapi.responses import RedirectResponse

@app.get("/")
def read_root():
    return RedirectResponse(url="/restaurants-page")


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    address = Column(String)
    email = Column(String)
    phone = Column(String)
    menu = relationship("MenuItem", back_populates="restaurant")

class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    restaurant = relationship("Restaurant", back_populates="menu")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    quantity = Column(Integer)

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)


Base.metadata.create_all(bind=engine)
from database import SessionLocal
db = SessionLocal()

if db.query(Restaurant).count() == 0:
    burger_place = Restaurant(
        name="Burger Palace",
        address="12 Bakerstraße, Kaiserslautern",
        email="contact@burgerpalace.de",
        phone="+49 631 1234567"
    )
    burger_place.menu = [
        MenuItem(name="Cheeseburger", price=8.99),
        MenuItem(name="Fries", price=3.49),
    ]

    shake_place = Restaurant(
        name="Milkshake Corner",
        address="45 Hauptstraße, Kaiserslautern",
        email="hello@milkshakecorner.de",
        phone="+49 631 7654321"
    )
    shake_place.menu = [
        MenuItem(name="Milkshake", price=4.99),
        MenuItem(name="Sundae", price=5.49),
    ]

    db.add(burger_place)
    db.add(shake_place)
    db.commit()

db.close()
from fastapi.encoders import jsonable_encoder

@app.get("/restaurants")
def get_restaurants():
    db = SessionLocal()
    restaurants = db.query(Restaurant).all()
    result = []
    for r in restaurants:
        result.append({
            "id": r.id,
            "name": r.name,
            "menu": [{"name": item.name, "price": item.price} for item in r.menu]
        })
    db.close()
    return result

from pydantic import BaseModel
from typing import List


class OrderItemInput(BaseModel):
    menu_item_id: int
    quantity: int


class OrderInput(BaseModel):
    user_id: int
    restaurant_id: int
    items: List[OrderItemInput]

class UserInput(BaseModel):
    username: str
    password: str

@app.post("/register")
def register(user_input: UserInput):
    db = SessionLocal()

    existing_user = db.query(User).filter(User.username == user_input.username).first()
    if existing_user:
        db.close()
        return {"error": "Username already taken"}

    hashed_password = pwd_context.hash(user_input.password)
    new_user = User(username=user_input.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.close()

    return {"message": "User registered successfully"}


@app.post("/orders")
def create_order(order_input: OrderInput):
    db = SessionLocal()

    new_order = Order( user_id=order_input.user_id,
        restaurant_id=order_input.restaurant_id
                     )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    for item in order_input.items:
        order_item = OrderItem(
            order_id=new_order.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity
        )
        db.add(order_item)

    db.commit()
    order_id = new_order.id 
    db.close()

    return {"message": "Order placed!", "order_id": order_id }
@app.get("/orders")
def get_orders():
    db = SessionLocal()
    orders = db.query(Order).all()
    result = []
    for o in orders:
        result.append({
            "id": o.id,
            "customer_name": o.customer_name,
            "restaurant_id": o.restaurant_id,
            "items": [{"menu_item_id": i.menu_item_id, "quantity": i.quantity} for i in o.items]
        })
    db.close()
    return result
@app.get("/restaurants-page")
def restaurants_page(request: Request):
    db = SessionLocal()
    restaurants = db.query(Restaurant).all()

    restaurant_data = []
    for r in restaurants:
        restaurant_data.append({
            "id": r.id,
            "name": r.name,
            "address": r.address,
            "email": r.email,
            "phone": r.phone,
            "menu": [{"id": item.id, "name": item.name, "price": item.price} for item in r.menu]
        })
    db.close()
    return templates.TemplateResponse(request, "restaurants.html", {"restaurants": restaurant_data})
@app.get("/users")
def get_users():
    db = SessionLocal()
    users = db.query(User).all()
    result = [{"id": u.id, "username": u.username, "hashed_password": u.hashed_password} for u in users]
    db.close()
    return result

@app.post("/login")
def login(user_input: UserInput):
    db = SessionLocal()

    user = db.query(User).filter(User.username == user_input.username).first()

    if not user:
        db.close()
        return {"error": "Invalid username or password"}

    if not pwd_context.verify(user_input.password, user.hashed_password):
        db.close()
        return {"error": "Invalid username or password"}

    db.close()
    return {"message": f"Welcome back, {user.username}!", "user_id": user.id}

@app.get("/login-page")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@app.get("/register-page")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {})
@app.get("/my-orders-page")
def my_orders_page(request: Request, user_id: int):
    db = SessionLocal()

    orders = db.query(Order).filter(Order.user_id == user_id).all()

    order_data = []
    for o in orders:
        restaurant = db.query(Restaurant).filter(Restaurant.id == o.restaurant_id).first()
        item_details = []
        for oi in o.items:
            menu_item = db.query(MenuItem).filter(MenuItem.id == oi.menu_item_id).first()
            item_details.append({"name": menu_item.name, "quantity": oi.quantity})

        order_data.append({
            "id": o.id,
            "restaurant_name": restaurant.name,
            "items": item_details
        })

    db.close()
    return templates.TemplateResponse(request, "my_orders.html", {"orders": order_data})