import os
from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- MSP per crop (Rs./quintal) ---
MSP_DATA = {
    "Bajra": 2775, "Barley": 1980, "Jowar": 3699, "Maize": 2400,
    "Paddy (Common)": 2369, "Ragi": 4886, "Wheat": 2585,
    "Cotton": 7710, "Copra": 12027, "Groundnut": 7263, "Mustard": 6200,
    "Sesamum": 9846, "Soyabean": 5328, "Arhar": 8000, "Gram": 5875,
    "Urad": 7800, "Moong": 8768, "Masur": 7000, "Safflower": 6540,
    "Onion": 1499.98, "Potato": 783.36, "Tomato": 3139.63
}

# --- Load state-wise prices ---
state_json_path = os.path.join(BASE_DIR, "dataset", "state_prices.json")
with open(state_json_path) as f:
    STATE_PRICES = json.load(f)

# --- Crop images mapping ---
CROP_IMAGE_MAP = {crop: crop.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")+".jpg"
                  for crop in MSP_DATA.keys()}

# --- All states from JSON ---
ALL_STATES = sorted({state for prices in STATE_PRICES.values()
                    for state in prices.keys()})

# --- Routes ---


@app.route("/")
def home():
    crops = sorted(MSP_DATA.keys())
    return render_template("index.html", crops=crops, images=CROP_IMAGE_MAP, states=ALL_STATES)


@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        req = request.json
        crop = req["crop"]
        total_cost = float(req["cost"])
        total_kg = float(req["quantity"])
        profit_percent = float(req["profit"])
        selected_state = req.get("state", "")

        # Cost per kg and required price
        cost_per_kg = total_cost / total_kg
        required_price = cost_per_kg * (1 + profit_percent / 100)
        total_revenue = required_price * total_kg

        # MSP per kg
        msp_kg = MSP_DATA.get(crop, 0)/100

        # Market price per kg in selected state
        states = STATE_PRICES.get(crop, {})
        selected_state_price = None
        selected_state_revenue = None
        if selected_state:
            if selected_state in states:
                selected_state_price = states[selected_state]/100
                selected_state_revenue = round(
                    selected_state_price * total_kg, 2)
            else:
                selected_state_price = None
                selected_state_revenue = "Revenue not available for this state."

        # Revenue per state (only valid)
        state_revenues = {st: round(price/100 * total_kg, 2)
                          for st, price in states.items() if price is not None}

        # Advice
        if state_revenues:
            best_state = max(state_revenues.items(), key=lambda x: x[1])[0]
            if selected_state:
                if selected_state in state_revenues:
                    if selected_state == best_state:
                        advice = f"Good choice! {selected_state} gives maximum revenue."
                    else:
                        advice = f"Selected state {selected_state} revenue is lower. Consider selling in {best_state} for max revenue."
                else:
                    advice = f"Revenue not available for {selected_state}. Best state to sell: {best_state}"
            else:
                advice = f"Best state to sell: {best_state}"
        else:
            advice = "No state price data available."

        # Top 3 states
        top_states = sorted(state_revenues.items(),
                            key=lambda x: x[1], reverse=True)[:3]

        return jsonify({
            "cost_per_kg": round(cost_per_kg, 2),
            "required_price": round(required_price, 2),
            "total_revenue": round(total_revenue, 2),
            "msp": round(msp_kg, 2),
            "market": round(selected_state_price, 2) if selected_state_price else None,
            "selected_state_revenue": selected_state_revenue,
            "states": states,
            "state_revenues": state_revenues,
            "advice": advice,
            "top_states": top_states
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)
