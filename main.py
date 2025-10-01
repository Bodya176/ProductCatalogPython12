from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict
import threading
import requests
from datetime import datetime, timedelta, date  # date добавлен

PRODUCT_SERVICE_URL = "http://localhost:8080/products"

app = FastAPI()

# --- Модели данных ---
class OrderItem(BaseModel):
    product_id: int
    quantity: int

class Order(BaseModel):
    id: int
    items: List[OrderItem]
    total_amount: float = 0.0
    delivery_date: date  # теперь только дата

# --- Хранилище ---
orders: Dict[int, Order] = {}
order_id_counter = 0

@app.get("/orders", response_model=List[Order])
def get_all_orders():
    return list(orders.values())

@app.get("/orders/{order_id}", response_model=Order)
def get_order_by_id(order_id: int):
    if order_id not in orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return orders[order_id]

@app.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(order_items: List[OrderItem]):
    total_amount = 0.0
    validated_items = []

    for item in order_items:
        try:
            response = requests.get(f"{PRODUCT_SERVICE_URL}/{item.product_id}")

            if response.status_code == 200:
                product_data = response.json()
                total_amount += product_data["price"] * item.quantity
                validated_items.append(item)
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product with id {item.product_id} not found."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Product service is unavailable."
                )
        except requests.exceptions.RequestException:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cannot connect to Product service."
            )

    global order_id_counter
    order_id_counter += 1
    new_id = order_id_counter

    # delivery_date только в формате YYYY-MM-DD
    delivery_date = (datetime.utcnow() + timedelta(days=5)).date()

    new_order = Order(
        id=new_id,
        items=validated_items,
        total_amount=total_amount,
        delivery_date=delivery_date
    )
    orders[new_id] = new_order
    return new_order
