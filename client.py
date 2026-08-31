import os

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


load_dotenv()

CUSTOMER_URL = os.getenv("CUSTOMER_URL")

if not CUSTOMER_URL:
    raise RuntimeError("CUSTOMER_URL is missing in the .env file")


app = FastAPI(
    title="Food Ordering API",
    description="API for viewing the menu, ordering food, and making payments",
    version="1.0.0",
)


class OrderRequest(BaseModel):
    text: str


class PaymentRequest(BaseModel):
    order_id: str
    amount: float


def call_customer_service(method: str, endpoint: str, **kwargs):
    """Call the existing customer service and return its JSON response."""
    try:
        response = requests.request(
            method=method,
            url=f"{CUSTOMER_URL}{endpoint}",
            timeout=30,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Customer service request failed: {error}",
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail="Customer service returned an invalid JSON response",
        ) from error


@app.get("/")
def home():
    return {
        "message": "Food Ordering API is running",
        "docs": "/docs",
    }


@app.get("/menu")
def get_menu():
    return call_customer_service("GET", "/menu")


@app.post("/order")
def create_order(order: OrderRequest):
    result = call_customer_service(
        "POST",
        "/order",
        json={"text": order.text},
    )

    if result.get("status") != "ok":
        return result

    return {
        "status": result["status"],
        "order_id": result["order_id"],
        "breakdown": result["breakdown"],
        "total": result["total"],
    }


@app.post("/pay")
def make_payment(payment: PaymentRequest):
    result = call_customer_service(
        "POST",
        "/pay",
        json={
            "order_id": payment.order_id,
            "amount": payment.amount,
        },
    )

    if result.get("status") == "approved":
        return {
            "status": result["status"],
            "message": result["message"],
            "delivery_id": result["delivery_id"],
            "delivery_time_min": result["delivery_time_min"],
        }

    return result


if __name__ == "__main__":
    uvicorn.run(
        "client:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )