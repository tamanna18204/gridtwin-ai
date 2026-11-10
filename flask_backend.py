
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

twin_data = {}

LIMIT = 75.0


# Calculate phase balance score
def calculate_score(loads):
    values = list(loads.values())

    if not values or max(values) == 0:
        return 100.0

    average = sum(values) / len(values)
    deviation = max(abs(value - average) for value in values)

    score = 100 - (deviation / max(average, 1)) * 100

    return round(max(0, score), 1)


# Common response for unsuccessful recommendations
def no_recommendation(message, before, score_before):
    return jsonify({
        "recommended": False,
        "message": message,
        "before": before,
        "after": before,
        "score_before": score_before,
        "score_after": score_before
    }), 200


# =====================================
# 1. UPDATE DIGITAL TWIN
# =====================================

@app.route("/update_twin", methods=["POST"])
def update_twin():

    global twin_data

    try:
        data = request.get_json(silent=True) or {}

        twin_data = {
            "R": float(data.get("R", 0)),
            "Y": float(data.get("Y", 0)),
            "B": float(data.get("B", 0)),
            "ambient_temp": float(data.get("ambient_temp", 30))
        }

        return jsonify({
            "status": "success",
            "message": "Digital Twin Updated Successfully",
            "transformer": twin_data
        }), 200

    except (TypeError, ValueError) as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400


# =====================================
# 2. RECOMMEND LOAD TRANSFER
# =====================================

@app.route("/recommend_transfer", methods=["POST"])
def recommend_transfer():

    try:
        data = request.get_json(silent=True) or {}

        current = data.get("current_loads", {})
        predicted = data.get("predicted_loads", {})
        excluded = data.get("excluded_targets", [])

        phases = ["R", "Y", "B"]

        current_loads = {
            p: float(current.get(p, 0))
            for p in phases
        }

        predicted_loads = {
            p: float(predicted.get(p, current_loads[p]))
            for p in phases
        }

        # Before transfer
        before = {
            "current": current_loads.copy(),
            "predicted": predicted_loads.copy()
        }

        score_before = calculate_score(predicted_loads)

        # Find overloaded phases
        overloaded = [
            p for p in phases
            if predicted_loads[p] > LIMIT
        ]

        if not overloaded:
            return no_recommendation(
                "All phases are within safe demo limit.",
                before,
                score_before
            )

        # Highest overloaded phase
        source = max(
            overloaded,
            key=lambda p: predicted_loads[p]
        )

        # Find safe destination phases
        candidates = []

        for p in phases:

            if p == source:
                continue

            if predicted_loads[p] >= LIMIT:
                continue

            is_excluded = any(
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and item[0] == source
                and item[1] == p
                for item in excluded
            )

            if not is_excluded:
                candidates.append(p)

        if not candidates:
            return no_recommendation(
                "No safe destination phase available.",
                before,
                score_before
            )

        # Lowest loaded destination
        destination = min(
            candidates,
            key=lambda p: predicted_loads[p]
        )

        # Calculate transfer amount
        amount = min(
            predicted_loads[source] - LIMIT,
            LIMIT - predicted_loads[destination]
        )

        if amount <= 0:
            return no_recommendation(
                "No safe transfer amount available.",
                before,
                score_before
            )

        # After transfer
        after = {
            "current": current_loads.copy(),
            "predicted": predicted_loads.copy()
        }

        after["predicted"][source] = round(
            predicted_loads[source] - amount, 2
        )

        after["predicted"][destination] = round(
            predicted_loads[destination] + amount, 2
        )

        score_after = calculate_score(after["predicted"])

        # Final successful response
        return jsonify({
            "recommended": True,
            "source": source,
            "destination": destination,
            "amount_a": round(amount, 2),
            "before": before,
            "after": after,
            "score_before": score_before,
            "score_after": score_after,
            "message": "Safe demo transfer recommendation generated."
        }), 200

    except (TypeError, ValueError, AttributeError) as error:

        return jsonify({
            "recommended": False,
            "error": str(error),
            "message": "Invalid load data."
        }), 400

    except Exception as error:

        app.logger.exception("Transfer recommendation failed")

        return jsonify({
            "recommended": False,
            "error": str(error),
            "message": "Internal backend error."
        }), 500


# =====================================
# 3. HEALTH CHECK
# =====================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "status": "online",
        "service": "GridTwin AI Flask Backend"
    })


# =====================================
# 4. START SERVER
# =====================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
