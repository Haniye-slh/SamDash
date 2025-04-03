from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, Float, String, ForeignKey, DateTime, Text, DateTime
from datetime import datetime

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")

class Product(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    image: Mapped[str] = mapped_column(String(500), nullable=True)
    
class Order(db.Model):
    id: Mapped[int] =mapped_column(Integer, primary_key=True)
    username: Mapped[str] =mapped_column(String(150), nullable=False)
    product_id: Mapped[int] =mapped_column(Integer, ForeignKey('product.id', ondelete="CASCADE"), nullable=False)
    address: Mapped[str] =mapped_column(String(500), nullable=False)
    quantity: Mapped[int] =mapped_column(Integer, nullable=False)
    timestamp: Mapped[str] =mapped_column(DateTime, default=datetime.utcnow)
    product= db.relationship("Product", backref="orders")
    status = db.Column(db.String(20), default="Pending")
    
class Comment(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("product.id"), nullable=False)