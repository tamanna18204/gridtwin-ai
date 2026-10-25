def calculate_thermal_state(
    current,
    ambient_temp,
    rated_current=100.0,
    max_reference_temp=90.0
):
    if rated_current <= 0 or max_reference_temp <= 0:
        raise ValueError("Reference values must be positive.")

    load_ratio = max(0.0, current) / rated_current
    temperature_rise = 60.0 * (load_ratio ** 2)
    conductor_temp = ambient_temp + temperature_rise
    thermal_percent = (conductor_temp / max_reference_temp) * 100.0

    if thermal_percent < 75:
        status = "NORMAL"
    elif thermal_percent <= 90:
        status = "WARNING / TRANSFER"
    else:
        status = "EMERGENCY / TRIP"

    return {
        "temperature": round(conductor_temp, 2),
        "thermal_percent": round(thermal_percent, 2),
        "status": status
    }
