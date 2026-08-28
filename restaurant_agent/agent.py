import json, os
from fastapi import FastAPI
from pydantic import BaseModel

BASE = os.path.dirname(__file__)
MENU_FILE = os.path.join(BASE, "menu.json")

app = FastAPI(title="RestaurantAgent")  # A2A_Server

def load_menu():
    with open(MENU_FILE) as f:
        return json.load(f)

def save_menu(menu):
    with open(MENU_FILE, "w") as f:
        json.dump(menu, f, indent=2)

@app.get("/.well-known/agent.json")
def agent_card():
    with open(os.path.join(BASE, "agent_card.json")) as f:
        return json.load(f)

@app.get("/menu")  # Show_Menu, Menu_Data
def show_menu():
    return load_menu()

class ItemsReq(BaseModel):
    items: dict[str, int]

@app.post("/check")  # Check_Availability
def check_availability(req: ItemsReq):
    menu = load_menu()
    unavailable = {}
    unknown = []
    for name, qty in req.items.items():
        if name not in menu:
            unknown.append(name)
            continue
        if menu[name]["quantity"] < qty:
            unavailable[name] = menu[name]["quantity"]
    return {
        "available": not unavailable and not unknown,
        "unavailable": unavailable,
        "unknown": unknown,
        "menu": menu,
    }

@app.post("/reduce")
def reduce_stock(req: ItemsReq):
    menu = load_menu()
    unavailable = {}
    unknown = []

    # Validate the entire order before changing inventory.
    for name, qty in req.items.items():
        if name not in menu:
            unknown.append(name)
        elif qty <= 0 or menu[name]["quantity"] < qty:
            unavailable[name] = menu[name]["quantity"]

    if unavailable or unknown:
        return {
            "status": "error",
            "message": "Stock was not reduced.",
            "unavailable": unavailable,
            "unknown": unknown,
        }

    for name, qty in req.items.items():
        menu[name]["quantity"] -= qty
    save_menu(menu)
    return {"status": "reduced", "menu": menu}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
