import json, os
from fastapi import FastAPI
from pydantic import BaseModel

BASE = os.path.dirname(__file__)
app = FastAPI(title="PaymentAgent")

@app.get("/.well-known/agent.json")
def agent_card():
    with open(os.path.join(BASE, "agent_card.json")) as f:
        return json.load(f)

class CalcReq(BaseModel):
    items: dict

@app.post("/calculate")
def calculate_total(req: CalcReq):
    breakdown = {}
    total = 0
    for name, d in req.items.items():
        line = d["price"] * d["qty"]
        breakdown[name] = {"price": d["price"], "qty": d["qty"], "line_total": line}
        total += line
    return {"breakdown": breakdown, "total": total}

class ValidateReq(BaseModel):
    total: float
    amount: float

@app.post("/validate")
def validate_payment(req: ValidateReq):
    if req.amount == req.total:
        return {"status": "approved", "message": "Payment approved."}
    elif req.amount > req.total:
        return {"status": "higher", "message": f"Amount too high. Expected {req.total}. Re-enter amount."}
    else:
        return {"status": "lower", "message": f"Amount too low. Expected {req.total}. Check the price and re-enter."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
