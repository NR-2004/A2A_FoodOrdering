import json, os, random
from datetime import datetime
from fastapi import FastAPI

BASE = os.path.dirname(__file__)
COUNT_FILE = os.path.join(BASE, "count_delivery.json")
app = FastAPI(title="DeliveryAgent")

def load_counter():
    with open(COUNT_FILE) as f:
        return json.load(f)

def save_counter(c):
    with open(COUNT_FILE, "w") as f:
        json.dump(c, f, indent=2)

@app.get("/.well-known/agent.json")
def agent_card():
    with open(os.path.join(BASE, "agent_card.json")) as f:
        return json.load(f)

def gen_delivery_id():
    today = datetime.now().strftime("%Y%d%m")
    c = load_counter()
    if c["date"] != today:
        c["date"] = today
        c["count"] = 0
    c["count"] += 1
    save_counter(c)
    return f"MNR{today}{str(c['count']).zfill(3)}"

def generate_time():
    return random.randint(15, 45)

@app.post("/create")
def create_delivery():
    return {
        "delivery_id": gen_delivery_id(),
        "delivery_time_min": generate_time(),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
