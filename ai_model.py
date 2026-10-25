
import numpy as np
from sklearn.ensemble import RandomForestRegressor


def train_ai_model():
    """
    Demo-only model trained on synthetic readings.
    Not validated for real transformer forecasting.
    """
    rng = np.random.default_rng(42)
    samples = 1000

    # Synthetic R, Y and B phase current readings
    currents = rng.uniform(10, 150, (samples, 3))

    # Synthetic ambient temperature input
    ambient = rng.uniform(15, 45, (samples, 1))

    X = np.column_stack((currents, ambient))

    # Synthetic next-reading targets
    # Small random changes around the present current
    changes = rng.normal(0, 3, (samples, 3))
    y = np.maximum(0, currents + changes)

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X, y)
    return model


model = train_ai_model()


def predict_next_load(r_current, y_current, b_current, ambient_temp):
    """Return illustrative next-reading estimates for R, Y and B."""

    readings = np.array([[
        r_current,
        y_current,
        b_current,
        ambient_temp
    ]], dtype=float)

    if not np.all(np.isfinite(readings)):
        raise ValueError("All input readings must be finite numbers.")

    if np.any(readings[0, :3] < 0):
        raise ValueError("Phase currents cannot be negative.")

    prediction = model.predict(readings)[0]

    return {
        "R": round(float(prediction[0]), 2),
        "Y": round(float(prediction[1]), 2),
        "B": round(float(prediction[2]), 2)
    }
