import requests
import os
from dotenv import load_dotenv

load_dotenv()

CUSTOMER_URL = os.getenv("CUSTOMER_URL")

def main():
    print("=== MENU ===")
    menu = requests.get(f"{CUSTOMER_URL}/menu").json()
    for name, d in menu.items():
        print(f"{name.title():10} Rs.{d['price']:<5} (stock: {d['quantity']})")

    text = input("\nWhat would you like to order? (e.g. '2 pizza and 1 coke')\n> ")
    r = requests.post(f"{CUSTOMER_URL}/order", json={"text": text}).json()
    if r["status"] != "ok":
        print(r)
        return

    order_id, total = r["order_id"], r["total"]
    print(f"\nOrder ID: {order_id}")
    for name, d in r["breakdown"].items():
        print(f"  {name}: {d['qty']} x Rs.{d['price']} = Rs.{d['line_total']}")
    print(f"Total: Rs.{total}")

    while True:
        amount = float(input("\nEnter payment amount: "))
        pr = requests.post(f"{CUSTOMER_URL}/pay", json={"order_id": order_id, "amount": amount}).json()
        print(pr["message"])
        if pr["status"] == "approved":
            print(f"Delivery ID: {pr['delivery_id']} ")
            print(f"Food Delivered in : {pr['delivery_time_min']} min")
            break
        if pr["status"] == "error":
            break

if __name__ == "__main__":
    main()
