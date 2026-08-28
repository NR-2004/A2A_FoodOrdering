import json, os, re, requests, uuid
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

BASE = os.path.dirname(__file__)
RESTAURANT_URL = os.getenv("RESTAURANT_URL")
PAYMENT_URL    = os.getenv("PAYMENT_URL")
DELIVERY_URL   = os.getenv("DELIVERY_URL")

try:
    from ai_core_client import openai_client
    DEPLOYMENT_ID = os.environ["DEPLOYMENT_ID"]
except Exception as e:
    print("LLM unavailable, falling back to regex parser:", e)
    openai_client = None
    DEPLOYMENT_ID = None

app = FastAPI(title="CustomerAgent")
ORDERS = {}

class A2AClient:
    @staticmethod
    def get(base, path):
        return requests.get(f"{base}{path}").json()

    @staticmethod
    def post(base, path, payload):
        return requests.post(f"{base}{path}", json=payload).json()

a2a = A2AClient()

@app.get("/.well-known/agent.json")
def agent_card():
    with open(os.path.join(BASE, "agent_card.json")) as f:
        return json.load(f)

@app.get("/menu")
def get_menu():
    return a2a.get(RESTAURANT_URL, "/menu")

def order_parser_regex(text, menu):
    """Extract every menu item and its quantity from free-form order text."""
    text = text.lower()
    items = {}
    menu_names = sorted(menu, key=len, reverse=True)
    if not menu_names:
        return items

    name_pattern = "|".join(re.escape(name) for name in menu_names)
    pattern = re.compile(
        rf"(?<![a-z])(?:(\d+)\s*(?:x\s*)?)?({name_pattern})(?:es|s)?(?![a-z])",
        re.IGNORECASE,
    )

    for match in pattern.finditer(text):
        qty = int(match.group(1) or 1)
        name = match.group(2).lower()
        if qty > 0:
            items[name] = items.get(name, 0) + qty
    return items


def order_parser_llm(text, menu):
    prompt = (
        "Extract the food order as strict JSON only (no prose, no markdown fences). "
        f"Valid menu items: {list(menu.keys())}. "
        'Output format: {"item_name": quantity, ...}. '
        f'User order: "{text}"'
    )
    response = openai_client.chat.completions.create(
        model=DEPLOYMENT_ID,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
    parsed = json.loads(raw)
    return {k: int(v) for k, v in parsed.items() if k in menu and int(v) > 0}


def order_parser(text, menu):  # Order_Parser — regex first (deterministic), LLM only as fallback
    items = order_parser_regex(text, menu)
    if items:
        return items
    if openai_client is not None and DEPLOYMENT_ID:
        try:
            return order_parser_llm(text, menu)
        except Exception as e:
            print("LLM parse failed:", e)
    return items

class OrderReq(BaseModel):
    text: str

@app.post("/order")
def place_order(req: OrderReq):
    menu = a2a.get(RESTAURANT_URL, "/menu")
    items = order_parser(req.text, menu)
    if not items:
        return {"status": "error", "message": "Could not understand order. Use e.g. '2 pizza and 1 coke'."}

    check = a2a.post(RESTAURANT_URL, "/check", {"items": items})
    if not check["available"]:
        return {"status": "error", "message": "Items unavailable/unknown.",
                "unavailable": check["unavailable"], "unknown": check["unknown"]}

    calc_items = {name: {"price": menu[name]["price"], "qty": qty} for name, qty in items.items()}
    calc = a2a.post(PAYMENT_URL, "/calculate", {"items": calc_items})

    order_id = str(uuid.uuid4())[:8]
    ORDERS[order_id] = {"items": items, "total": calc["total"], "status": "pending"}
    return {"status": "ok", "order_id": order_id, "breakdown": calc["breakdown"], "total": calc["total"]}

class PayReq(BaseModel):
    order_id: str
    amount: float

@app.post("/pay")
def pay(req: PayReq):
    order = ORDERS.get(req.order_id)
    if not order:
        return {"status": "error", "message": "Invalid order_id."}
    if order["status"] == "approved":
        return {"status": "error", "message": "Order already paid."}

    result = a2a.post(PAYMENT_URL, "/validate", {"total": order["total"], "amount": req.amount})
    if result["status"] != "approved":
        return result

    stock_result = a2a.post(RESTAURANT_URL, "/reduce", {"items": order["items"]})
    if stock_result.get("status") != "reduced":
        return {
            "status": "error",
            "message": "Payment was approved, but inventory could not be updated. Please contact support.",
            "inventory": stock_result,
        }
    delivery = a2a.post(DELIVERY_URL, "/create", {})
    order["status"] = "approved"
    return {"status": "approved", "message": "Payment approved.", **delivery}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
