"""Flask API and demo load-transfer recommendation engine.

All calculations are illustrative software simulation only. They are not
validated for operating real distribution equipment.
"""
from flask import Flask, request, jsonify
from thermal_model import calculate_thermal_state
import math

app = Flask(__name__)
PHASES = ("R", "Y", "B")
MAX_SIMULATED_CURRENT = 200.0

# Retained for the existing status endpoint / dashboard connection.
twin_database = {
    "thermal_states": {p: 30.0 for p in PHASES},
    "current_loads": {p: 50.0 for p in PHASES},
    "status": "NORMAL",
}


def _validate_phase_values(values, field_name):
    if not isinstance(values, dict):
        raise ValueError(f"{field_name} must be an object with R, Y and B values")
    result = {}
    for phase in PHASES:
        value = float(values.get(phase, 0.0))
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{field_name}.{phase} must be a finite non-negative number")
        result[phase] = value
    return result


def _risk(current, ambient_temp):
    return calculate_thermal_state(
        current=float(current), ambient_temp=float(ambient_temp)
    )["thermal_percent"]


def recommend_transfer(current_loads, predicted_loads, ambient_temp=30.0,
                        excluded_targets=None):
    """Find the best one-destination transfer by minimizing worst pair risk.

    The same transfer amount is applied to present and predicted snapshots.
    Search is performed in 0.5 A increments, bounded by source load and the
    destination's 200 A demo ceiling. A recommendation is returned only if
    it improves the worst present/predicted thermal-risk score.
    """
    current = _validate_phase_values(current_loads, "current_loads")
    predicted = _validate_phase_values(predicted_loads, "predicted_loads")
    ambient = float(ambient_temp)
    if not math.isfinite(ambient):
        raise ValueError("ambient_temp must be finite")

    excluded = set(excluded_targets or [])
    for phase in excluded:
        if phase not in PHASES:
            raise ValueError(f"Unknown excluded phase: {phase}")

    # Choose the phase with the greatest combined current/predicted thermal risk.
    source_scores = {
        p: max(_risk(current[p], ambient), _risk(predicted[p], ambient))
        for p in PHASES
    }
    source = max(PHASES, key=lambda p: source_scores[p])
    baseline_source_score = source_scores[source]

    # Only recommend intervention when a phase reaches the dashboard's
    # WARNING / TRANSFER band (75% thermal index) in current or prediction.
    if baseline_source_score < 75.0:
        return {
            "recommended": False,
            "status": "NO_TRANSFER_NEEDED",
            "source": source,
            "destination": None,
            "amount_a": 0.0,
            "reason_transfer": "No phase currently or predictively reaches the demo thermal warning band.",
            "reason_no_transfer": (
                f"The highest present/predicted thermal index is {baseline_source_score:.1f}%, "
                "below the 75% demo warning threshold. Keeping the phase allocation unchanged "
                "avoids an unnecessary simulated transfer."
            ),
            "before": {"current": current, "predicted": predicted},
            "after": None,
            "score_before": round(baseline_source_score, 2),
            "score_after": round(baseline_source_score, 2),
        }

    candidates = []
    for destination in PHASES:
        if destination == source or destination in excluded:
            continue
        max_amount = min(current[source], predicted[source],
                         MAX_SIMULATED_CURRENT - current[destination],
                         MAX_SIMULATED_CURRENT - predicted[destination])
        if max_amount < 0.5:
            continue

        # Find amount minimizing the worst thermal index across source and
        # destination for both the present and predicted snapshots.
        steps = int(max_amount / 0.5)
        best = None
        for step in range(1, steps + 1):
            amount = step * 0.5
            post_current = dict(current)
            post_predicted = dict(predicted)
            post_current[source] -= amount
            post_current[destination] += amount
            post_predicted[source] -= amount
            post_predicted[destination] += amount

            pair_scores = [
                _risk(post_current[source], ambient),
                _risk(post_current[destination], ambient),
                _risk(post_predicted[source], ambient),
                _risk(post_predicted[destination], ambient),
            ]
            score = max(pair_scores)
            # Tie-break toward the smaller transfer.
            candidate = (score, amount, post_current, post_predicted)
            if best is None or score < best[0] - 1e-9:
                best = candidate

        if best:
            candidates.append((best[0], best[1], destination, best[2], best[3]))

    if not candidates:
        return {
            "recommended": False,
            "status": "NO_SAFE_TRANSFER_AVAILABLE",
            "source": source,
            "destination": None,
            "amount_a": 0.0,
            "reason_transfer": "No eligible destination has sufficient simulated headroom for a transfer.",
            "reason_no_transfer": "The remaining phases are at their configured 200 A demo ceiling or have been excluded. Do not force a transfer in this simulation.",
            "before": {"current": current, "predicted": predicted},
            "after": None,
            "score_before": round(baseline_source_score, 2),
            "score_after": round(baseline_source_score, 2),
        }

    candidates.sort(key=lambda item: (item[0], item[1]))
    best_score, amount, destination, after_current, after_predicted = candidates[0]

    if best_score >= baseline_source_score - 0.05:
        return {
            "recommended": False,
            "status": "NO_BENEFICIAL_TRANSFER",
            "source": source,
            "destination": None,
            "amount_a": 0.0,
            "reason_transfer": "The evaluated transfers do not materially improve the worst present/predicted thermal index.",
            "reason_no_transfer": "A transfer would not provide a meaningful improvement under the current demo model, so retaining the existing allocation is preferable.",
            "before": {"current": current, "predicted": predicted},
            "after": None,
            "score_before": round(baseline_source_score, 2),
            "score_after": round(best_score, 2),
        }

    return {
        "recommended": True,
        "status": "TRANSFER_RECOMMENDED",
        "source": source,
        "destination": destination,
        "amount_a": round(amount, 1),
        "reason_transfer": (
            f"Phase {source} has the highest present/predicted thermal risk. "
            f"Moving {amount:.1f} A to Phase {destination} gives the lowest "
            "worst-case thermal index among the evaluated destinations and amounts."
        ),
        "reason_no_transfer": (
            f"If declined, currents remain unchanged: Phase {source} stays at "
            f"{current[source]:.1f} A now and {predicted[source]:.1f} A predicted. "
            "The elevated demo thermal-risk indication therefore remains; no physical action occurs."
        ),
        "before": {"current": current, "predicted": predicted},
        "after": {"current": after_current, "predicted": after_predicted},
        "score_before": round(baseline_source_score, 2),
        "score_after": round(best_score, 2),
    }


@app.route("/get_status", methods=["GET"])
def get_status():
    return jsonify(twin_database)


@app.route("/update_twin", methods=["POST"])
def update_twin():
    data = request.get_json(silent=True) or {}
    try:
        loads = _validate_phase_values(data, "currents")
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    twin_database["current_loads"] = loads
    ambient = float(data.get("ambient_temp", 30.0))
    thermal = {
        p: calculate_thermal_state(loads[p], ambient)["temperature"]
        for p in PHASES
    }
    twin_database["thermal_states"] = thermal
    twin_database["status"] = "WARNING" if any(
        calculate_thermal_state(loads[p], ambient)["status"] != "NORMAL"
        for p in PHASES
    ) else "NORMAL"
    return jsonify({**twin_database, "ambient_temp": ambient})


@app.route("/recommend_transfer", methods=["POST"])
def recommend_transfer_route():
    data = request.get_json(silent=True) or {}
    try:
        recommendation = recommend_transfer(
            current_loads=data.get("current_loads", {}),
            predicted_loads=data.get("predicted_loads", {}),
            ambient_temp=data.get("ambient_temp", 30.0),
            excluded_targets=data.get("excluded_targets", []),
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(recommendation)


if __name__ == "__main__":
    print("Starting Flask API on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
