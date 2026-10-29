import streamlit as st
import plotly.graph_objects as go
import math
from thermal_model import calculate_thermal_state
from ai_model import predict_next_load


st.set_page_config(
    page_title="SIH | Distribution Network Digital Twin",
    page_icon="⚡",
    layout="wide",
)

# ---------- Theme / header ----------
st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
div[data-testid="stMetric"] {
    background: rgba(120, 145, 170, 0.10);
    border: 1px solid rgba(120, 145, 170, 0.28);
    padding: 12px 14px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

st.title("⚡ Distribution Network — Digital Twin")
st.caption("SIH 2026 • Interactive 3D Substation • Transformer & Feeder Monitoring")
st.info(
    "Prototype visualization using simulated inputs. It is not connected to physical equipment "
    "and is not an electrically validated network model."
)

# ---------- Sidebar controls ----------
st.sidebar.header("Simulated Sensor Inputs")
st.sidebar.caption("Change the values to update the monitoring view.")

# Store phase currents in session state so a transfer persists across reruns.
for key, default in (("current_r", 85), ("current_y", 60), ("current_b", 40)):
    if key not in st.session_state:
        st.session_state[key] = default

current_r = st.sidebar.slider("Phase R current (A)", 0, 200, key="current_r")
current_y = st.sidebar.slider("Phase Y current (A)", 0, 200, key="current_y")
current_b = st.sidebar.slider("Phase B current (A)", 0, 200, key="current_b")
ambient_temp = st.sidebar.slider("Ambient temperature (°C)", -10, 60, 30)
show_labels = st.sidebar.checkbox("Show equipment labels", value=True)
show_grid = st.sidebar.checkbox("Show ground grid", value=False)

phase_data = [
    ("R", "#E84A4A", current_r),
    ("Y", "#F2C744", current_y),
    ("B", "#3485E8", current_b),
]
avg = (current_r + current_y + current_b) / 3
# ---------- AI LOAD PREDICTION ----------
st.header("AI-Based Next Load Prediction")
st.caption("Prediction horizon: next model step")
predictions = predict_next_load(
    current_r,
    current_y,
    current_b,
    ambient_temp
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "R Phase Predicted (A)",
        f"{predictions['R']:.2f}"
    )

with col2:
    st.metric(
        "Y Phase Predicted (A)",
        f"{predictions['Y']:.2f}"
    )

with col3:
    st.metric(
        "B Phase Predicted (A)",
        f"{predictions['B']:.2f}"
    )

st.caption(
    "Demo prediction using synthetic training data. "
    "Not a validated real-world forecast."
)

# ---------- PRESENT VS PREDICTED LOAD GRAPH ----------
st.subheader("📊 Present Load vs Predicted Load")

phases = ["R", "Y", "B"]

present_load = [
    float(current_r),
    float(current_y),
    float(current_b)
]

predicted_load = [
    predictions["R"],
    predictions["Y"],
    predictions["B"]
]

fig_load_comparison = go.Figure()

fig_load_comparison.add_trace(
    go.Bar(
        name="Present Load",
        x=phases,
        y=present_load,
        text=[f"{value:.2f} A" for value in present_load],
        textposition="outside"
    )
)

fig_load_comparison.add_trace(
    go.Bar(
        name="Predicted Load",
        x=phases,
        y=predicted_load,
        text=[f"{value:.2f} A" for value in predicted_load],
        textposition="outside"
    )
)

fig_load_comparison.update_layout(
    title="Phase-wise Current Comparison",
    xaxis_title="Phase",
    yaxis_title="Current (A)",
    barmode="group",
    template="plotly_white",
    legend_title="Reading Type",
    margin=dict(t=60, b=40, l=40, r=30)
)

fig_load_comparison.update_yaxes(rangemode="tozero")

st.plotly_chart(
    fig_load_comparison,
    width="stretch",
    config={"displaylogo": False}
)

st.caption(
    "Present readings are compared with synthetic-model predictions. "
    "This is a single-step demo comparison, not a validated forecast."
)

# ---------- PREDICTED OVERLOAD WARNING ----------
st.subheader("⚠️ Predicted Overload Warning")

# Illustrative demo threshold only.
# Replace with validated equipment-specific ratings when available.
DEMO_CURRENT_THRESHOLD = 100.0  # Amperes

st.caption(
    f"Illustrative demo threshold: {DEMO_CURRENT_THRESHOLD:.1f} A per phase. "
    "This is not a validated transformer or ACSR conductor rating."
)

predicted_peak = max(predicted_load)

overloaded_phases = [
    phase
    for phase in phases
    if predictions[phase] > DEMO_CURRENT_THRESHOLD
]

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Highest Predicted Phase Current",
        f"{predicted_peak:.2f} A"
    )

with col2:
    st.metric(
        "Illustrative Threshold",
        f"{DEMO_CURRENT_THRESHOLD:.2f} A"
    )

if overloaded_phases:
    st.error(
        "DEMO WARNING: Predicted current exceeds the illustrative "
        "threshold in phase(s): "
        + ", ".join(overloaded_phases)
    )
else:
    st.success(
        "No predicted phase current exceeds the illustrative "
        "demo threshold."
    )

st.caption(
    "Software demonstration only. This warning is not a protection "
    "trip command and does not establish actual electrical safety."
)

# ---------- LOAD ANALYSIS ----------
st.header("⚡ Load Analysis")

phase_currents = {
    "R": float(current_r),
    "Y": float(current_y),
    "B": float(current_b)
}

avg = sum(phase_currents.values()) / 3
max_current = max(phase_currents.values())
min_current = min(phase_currents.values())

peak = max_current

spread = (
    (max_current - min_current) / avg * 100
    if avg > 0 else 0.0
)

max_deviation = max(
    abs(current - avg)
    for current in phase_currents.values()
)

imbalance_percent = (
    max_deviation / avg * 100
    if avg > 0 else 0.0
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Average Current", f"{avg:.2f} A")

with col2:
    st.metric("Maximum Current", f"{max_current:.2f} A")

with col3:
    st.metric("Minimum Current", f"{min_current:.2f} A")

st.metric(
    "Maximum-Deviation Imbalance",
    f"{imbalance_percent:.2f}%"
)

# ---------- PHASE IMBALANCE DETECTION ----------
st.subheader("🔍 Phase Imbalance Detection")

# Demo thresholds only; not a protection standard.
if avg == 0:
    status = "No Load"
    st.info("All three phases have zero current.")
elif imbalance_percent <= 10:
    status = "Balanced"
    st.success("Phase loading is balanced.")
elif imbalance_percent <= 20:
    status = "Moderate Imbalance"
    st.warning("Phase imbalance detected. Further analysis is needed.")
else:
    status = "High Imbalance"
    st.error("High phase imbalance detected.")

st.write(f"**System Status:** {status}")

for phase, current in phase_currents.items():
    deviation = current - avg
    st.write(
        f"**{phase} Phase:** {current:.2f} A "
        f"| Deviation from average: {deviation:+.2f} A"
    )

st.caption(
    "Simulation only. The 10% and 20% thresholds are illustrative "
    "demo settings, not validated protection limits."
)

# ---------- ACSR THERMAL OVERLOAD PROTECTION ----------
st.header("🌡️ ACSR Thermal Overload Protection")

# Demo assumes R, Y and B currents represent monitored conductor currents.
# Select the highest current for a conservative simulated assessment.
monitored_current = max(current_r, current_y, current_b)

thermal = calculate_thermal_state(
    current=monitored_current,
    ambient_temp=ambient_temp
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Monitored Current",
        f"{monitored_current:.2f} A"
    )

with col2:
    st.metric(
        "Estimated Conductor Temperature",
        f"{thermal['temperature']:.2f} °C"
    )

with col3:
    st.metric(
        "Thermal State",
        f"{thermal['thermal_percent']:.2f}%"
    )

st.subheader("Protection Decision")

if thermal["status"] == "NORMAL":
    st.success("NORMAL — Continue monitoring.")

elif thermal["status"] == "WARNING / TRANSFER":
    st.warning(
        "OVERLOAD WARNING — Simulated load-transfer "
        "recommendation generated."
    )

    st.info(
        "Recommendation: Evaluate transferring eligible load "
        "to the standby feeder after checking its available capacity."
    )

else:
    st.error(
        "EMERGENCY / TRIP — Critical simulated thermal state detected."
    )

    st.warning(
        "Simulated emergency alert only. No physical trip or "
        "switch operation is performed."
    )

st.caption(
    "Software simulation only. Thermal parameters and thresholds "
    "require engineering validation."
)

# ---------- INTERACTIVE LOAD TRANSFER SIMULATION ----------
st.header("🔀 Interactive Load Transfer")
st.caption(
    "Choose a source and destination phase, then transfer a selected amount. "
    "This is a software simulation only; it does not operate physical switchgear."
)

phase_keys = {"R": "current_r", "Y": "current_y", "B": "current_b"}
current_snapshot = {
    "R": float(st.session_state.current_r),
    "Y": float(st.session_state.current_y),
    "B": float(st.session_state.current_b),
}
source_phase = st.selectbox("Transfer load FROM phase", ["R", "Y", "B"], index=0, key="transfer_source")
destination_options = [p for p in ["R", "Y", "B"] if p != source_phase]
destination_phase = st.selectbox(
    "Transfer load TO phase", destination_options, key="transfer_destination"
)
available_source = current_snapshot[source_phase]
transfer_amount = st.number_input(
    "Load to transfer (A)",
    min_value=0.0,
    max_value=float(max(available_source, 0.0)),
    value=float(min(10.0, available_source)),
    step=1.0,
    key="transfer_amount",
)
st.caption(
    f"Available source current: {available_source:.1f} A · "
    f"Destination current before transfer: {current_snapshot[destination_phase]:.1f} A"
)
    if transfer_amount > source_now:
        st.session_state.transfer_error = (
            f"Phase {source_phase} only has {source_now:.1f} A available."
        )
        return
    
def transfer_load():
    source_phase = st.session_state.transfer_source
    destination_phase = st.session_state.transfer_destination
    transfer_amount = float(st.session_state.transfer_amount)

    phase_keys = {
        "R": "current_r",
        "Y": "current_y",
        "B": "current_b",
    }

    source_now = float(st.session_state[phase_keys[source_phase]])
    destination_now = float(st.session_state[phase_keys[destination_phase]])

    if transfer_amount <= 0:
        st.session_state.transfer_error = "Enter an amount greater than zero."
        return

    if transfer_amount > source_now:
        st.session_state.transfer_error = (
            f"Phase {source_phase} only has {source_now:.1f} A available."
        )
        return

    if destination_now + transfer_amount > 200:
        st.session_state.transfer_error = "Destination would exceed 200 A."
        return

    transfer_amount = float(round(transfer_amount))

    st.session_state[phase_keys[source_phase]] = int(round(source_now - transfer_amount))
    st.session_state[phase_keys[destination_phase]] = int(round(destination_now + transfer_amount))

    st.session_state.last_transfer = {
        "source": source_phase,
        "destination": destination_phase,
        "amount": transfer_amount,
        "source_before": source_now,
        "destination_before": destination_now,
        "source_after": source_now - transfer_amount,
        "destination_after": destination_now + transfer_amount,
    }

    st.session_state.transfer_error = ""


st.button(
    "⚡ TRANSFER LOAD",
    type="primary",
    width="stretch",
    on_click=transfer_load,
)

if st.session_state.get("transfer_error"):
    st.error(st.session_state.transfer_error)

    if destination_now + transfer_amount > 200:
        st.session_state.transfer_error = (
            "Destination would exceed the 200 A limit."
        )
        return

    transfer_amount = float(round(transfer_amount))

    st.session_state[phase_keys[source_phase]] = int(
        round(source_now - transfer_amount)
    )
    st.session_state[phase_keys[destination_phase]] = int(
        round(destination_now + transfer_amount)
    )

    st.session_state.last_transfer = {
        "source": source_phase,
        "destination": destination_phase,
        "amount": transfer_amount,
        "source_before": source_now,
        "destination_before": destination_now,
        "source_after": source_now - transfer_amount,
        "destination_after": destination_now + transfer_amount,
    }

    st.session_state.transfer_error = ""


if "last_transfer" in st.session_state:
    event = st.session_state.last_transfer
    st.success(
        f"Last transfer: {event['amount']:.1f} A moved from Phase {event['source']} "
        f"to Phase {event['destination']}."
    )
    before_col, after_col = st.columns(2)
    with before_col:
        st.markdown("**Before transfer**")
        st.write(f"Phase {event['source']}: {event['source_before']:.1f} A")
        st.write(f"Phase {event['destination']}: {event['destination_before']:.1f} A")
    with after_col:
        st.markdown("**After transfer**")
        st.write(f"Phase {event['source']}: {event['source_after']:.1f} A")
        st.write(f"Phase {event['destination']}: {event['destination_after']:.1f} A")
    st.metric("Total current across the three simulated phases", f"{sum(current_snapshot.values()):.1f} A",
              help="The transfer shifts the same amount between phases; the sum remains unchanged.")

    # A clear animated schematic of the transfer action for the judges' demo.
    st.subheader("Transfer movement")
    phase_x = {"R": 0, "Y": 1, "B": 2}
    sx, dx = phase_x[event["source"]], phase_x[event["destination"]]
    transfer_fig = go.Figure()
    transfer_fig.add_trace(go.Scatter(
        x=[0, 1, 2], y=[0, 0, 0], mode="lines",
        line=dict(color="#94A3B8", width=8), hoverinfo="skip", showlegend=False
    ))
    transfer_fig.add_trace(go.Scatter(
        x=[0, 1, 2], y=[0, 0, 0], mode="markers+text",
        marker=dict(size=34, color=["#E84A4A", "#F2C744", "#3485E8"],
                    line=dict(color="white", width=2)),
        text=["R", "Y", "B"], textposition="middle center",
        textfont=dict(color="white", size=14), showlegend=False,
        hovertemplate="Phase %{text}<extra></extra>"
    ))
    transfer_fig.add_trace(go.Scatter(
        x=[sx], y=[0.18], mode="markers",
        marker=dict(size=17, color="#10B981", line=dict(color="white", width=2)),
        name="Transferred load", showlegend=False
    ))
    transfer_frames = []
    for frame_idx in range(31):
        fraction = frame_idx / 30
        transfer_frames.append(go.Frame(
            name=str(frame_idx),
            data=[go.Scatter(x=[sx + (dx - sx) * fraction], y=[0.18 + 0.32 * math.sin(math.pi * fraction)])],
            traces=[2]
        ))
    transfer_fig.frames = transfer_frames
    transfer_fig.update_layout(
        height=300, margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(range=[-0.5, 2.5], tickvals=[0, 1, 2], ticktext=["Phase R", "Phase Y", "Phase B"],
                   showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(range=[-0.25, 0.75], visible=False, fixedrange=True),
        title=f"Moving {event['amount']:.1f} A: Phase {event['source']} → Phase {event['destination']}",
        updatemenus=[dict(type="buttons", showactive=False, x=0.5, y=-0.18, xanchor="center",
                          buttons=[dict(label="▶ Play transfer animation", method="animate", args=[None,
                              {"frame": {"duration": 45, "redraw": True},
                               "transition": {"duration": 0}, "fromcurrent": True}])])]
    )
    st.plotly_chart(transfer_fig, width="stretch", config={"displaylogo": False})
    st.caption("The animation illustrates the selected simulated transfer. The 3D feeder flow remains a separate continuous visualization.")

# Compatibility values for the existing primary/standby schematic below.
primary_before = float(monitored_current)
proposed_transfer = float(st.session_state.last_transfer["amount"]) if "last_transfer" in st.session_state else 0.0
standby_capacity = 50.0
primary_after = max(0.0, primary_before - proposed_transfer)

# ---------- VISUAL FEEDER AND SWITCH SIMULATION ----------
st.header("⚡ Primary & Standby Feeder Visualization")

# Determine the simulated switch state from existing inputs.
transfer_active = "last_transfer" in st.session_state

if transfer_active:
    last = st.session_state.last_transfer
    switch_label = f"TRANSFER COMPLETE: {last['amount']:.1f} A"
    switch_color = "#16a34a"
    primary_label = f"Phase {last['source']}: {last['source_after']:.1f} A"
    standby_label = f"Phase {last['destination']}: {last['destination_after']:.1f} A"
elif thermal["status"] == "EMERGENCY / TRIP":
    switch_label = "EMERGENCY - NO SWITCH ACTION"
    switch_color = "#dc2626"
    primary_label = f"Primary: {primary_before:.1f} A"
    standby_label = "Standby: unchanged"
elif thermal["status"] == "WARNING / TRANSFER":
    switch_label = "TRANSFER BLOCKED"
    switch_color = "#d97706"
    primary_label = f"Primary: {primary_before:.1f} A"
    standby_label = "Standby: unchanged"
else:
    switch_label = "NORMAL - MONITORING"
    switch_color = "#64748b"
    primary_label = f"Primary: {primary_before:.1f} A"
    standby_label = "Standby: on standby"

diagram = f"""
<div style="border:1px solid #64748b;border-radius:14px;
padding:14px;background:#ffffff;color:#172033;">
<svg viewBox="0 0 700 260" width="100%"
     xmlns="http://www.w3.org/2000/svg">
  <rect x="15" y="20" width="200" height="75" rx="12"
        fill="#dbeafe" stroke="#2563eb" stroke-width="2"/>
  <text x="115" y="47" text-anchor="middle"
        font-size="16" font-weight="bold" fill="#172033">
    PRIMARY FEEDER
  </text>
  <text x="115" y="72" text-anchor="middle"
        font-size="14" fill="#172033">{primary_label}</text>

  <rect x="485" y="20" width="200" height="75" rx="12"
        fill="#dcfce7" stroke="#16a34a" stroke-width="2"/>
  <text x="585" y="47" text-anchor="middle"
        font-size="16" font-weight="bold" fill="#172033">
    STANDBY FEEDER
  </text>
  <text x="585" y="72" text-anchor="middle"
        font-size="13" fill="#172033">{standby_label}</text>

  <path d="M215 58 H300" stroke="#64748b"
        stroke-width="5" fill="none"/>
  <path d="M400 58 H485" stroke="#64748b"
        stroke-width="5" fill="none"/>

  <rect x="300" y="28" width="100" height="60" rx="8"
        fill="{switch_color}" stroke="#334155" stroke-width="2"/>
  <circle cx="318" cy="58" r="5" fill="#ffffff"/>
  <circle cx="382" cy="58" r="5" fill="#ffffff"/>
  <line x1="318" y1="58" x2="378" y2="42"
        stroke="#ffffff" stroke-width="4"
        stroke-linecap="round"/>
  <text x="350" y="112" text-anchor="middle"
        font-size="13" fill="#172033">TRANSFER SWITCH</text>

  <rect x="35" y="145" width="630" height="68" rx="12"
        fill="#f1f5f9" stroke="{switch_color}" stroke-width="2"/>
  <text x="350" y="174" text-anchor="middle"
        font-size="16" font-weight="bold" fill="#172033">
    {switch_label}
  </text>
  <text x="350" y="196" text-anchor="middle"
        font-size="12" fill="#334155">
    Software simulation only - no physical switching
  </text>
</svg>
</div>
"""

st.markdown(diagram, unsafe_allow_html=True)

# Illustrative indicator only; not a validated thermal model.
estimated_temp = thermal["temperature"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Average phase current", f"{avg:.1f} A")
m2.metric("Phase current spread", f"{spread:.1f}%")
m3.metric("Highest phase current", f"{peak} A")
m4.metric("Illustrative temperature", f"{estimated_temp:.1f} °C")

if spread >= 30:
    st.warning("Phase current spread is high in this illustrative view. The threshold is a demo indicator, not a protection setting.")
elif spread >= 15:
    st.info("Phase currents differ noticeably in this illustrative view.")
else:
    st.success("Phase currents are relatively close in this illustrative view.")

# ---------- 3D helpers ----------
fig = go.Figure()

def add_box(x0, x1, y0, y1, z0, z1, color, name, opacity=1.0, line_color=None):
    vertices = [
        (x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
        (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)
    ]
    faces = [
        (0,1,2),(0,2,3),(4,5,6),(4,6,7),
        (0,1,5),(0,5,4),(1,2,6),(1,6,5),
        (2,3,7),(2,7,6),(3,0,4),(3,4,7)
    ]
    fig.add_trace(go.Mesh3d(
        x=[v[0] for v in vertices], y=[v[1] for v in vertices], z=[v[2] for v in vertices],
        i=[f[0] for f in faces], j=[f[1] for f in faces], k=[f[2] for f in faces],
        color=color, opacity=opacity, flatshading=False, name=name,
        showscale=False, lighting=dict(ambient=0.62, diffuse=0.75, specular=0.25, roughness=0.7),
        lightposition=dict(x=100, y=150, z=200),
        hovertemplate=f"<b>{name}</b><extra></extra>",
        **({"contour": {"show": False}} if False else {})
    ))

def add_line(points, color, name, width=6, dash="solid", opacity=1.0):
    fig.add_trace(go.Scatter3d(
        x=[p[0] for p in points], y=[p[1] for p in points], z=[p[2] for p in points],
        mode="lines", line=dict(color=color, width=width, dash=dash),
        opacity=opacity, name=name, showlegend=False,
        hovertemplate=f"<b>{name}</b><extra></extra>"
    ))

def add_marker(x, y, z, color, name, size=7, symbol="circle"):
    fig.add_trace(go.Scatter3d(
        x=[x], y=[y], z=[z], mode="markers",
        marker=dict(size=size, color=color, symbol=symbol, line=dict(color="#F8FAFC", width=1)),
        name=name, showlegend=False, hovertemplate=f"<b>{name}</b><extra></extra>"
    ))

def add_label(x, y, z, text, color="#243247", size=10):
    # Keep only high-level labels on the 3D scene to avoid overlapping text.
    if show_labels and (
        text in {"INCOMING SUPPLY", "MAIN BUSBAR", "MAIN BREAKER",
                 "TR-A", "TR-B", "TR-C", "LOAD BANK A", "LOAD BANK B",
                 "LOAD BANK C", "STANDBY FEEDER", "MONITOR"}
    ):
        fig.add_trace(go.Scatter3d(
            x=[x], y=[y], z=[z], mode="text", text=[text],
            textfont=dict(size=size, color=color, family="Arial"),
            showlegend=False, hoverinfo="skip"
        ))

# ---------- Ground / site platform ----------
add_box(-6.8, 8.0, -4.7, 4.7, -0.30, -0.05, "#D8DEE5", "Raised substation platform")
add_box(-6.55, 7.75, -4.45, 4.45, -0.05, 0.0, "#EEF1F4", "Substation floor")

# Floor grid as subtle guide lines
if show_grid:
    for x in range(-6, 8, 1):
        add_line([(x,-4.4,0.015),(x,4.4,0.015)], "#D1D8E0", "Ground guide", 1, opacity=0.6)
    for y in range(-4, 5, 1):
        add_line([(-6.5,y,0.015),(7.7,y,0.015)], "#D1D8E0", "Ground guide", 1, opacity=0.6)

# ---------- Incoming utility / substation ----------
# Entry gantry poles and crossbar
for x in [-5.8, -4.9]:
    add_box(x, x+0.12, -0.25, -0.13, 0.0, 3.0, "#7A8795", "Incoming line gantry")
add_box(-5.95, -4.75, -0.28, -0.10, 2.85, 3.0, "#64748B", "Gantry crossbar")
for y, c, p in [(-0.18,"#E84A4A","R"),(0.0,"#F2C744","Y"),(0.18,"#3485E8","B")]:
    add_line([(-6.5,y,3.2),(-5.35,y,3.2),(-4.5,y,2.9)], c, f"Incoming {p} conductor", 5)
    add_marker(-5.35,y,3.2,c,f"{p} incoming terminal",5)
add_label(-5.8, -1.0, 3.55, "INCOMING SUPPLY", size=10)

# Main incoming breaker / switchgear
add_box(-4.8,-4.15,-0.65,0.65,0.05,1.15,"#D7A84B","Incoming circuit breaker")
add_box(-4.72,-4.23,-0.50,0.50,1.15,1.32,"#F4D58D","Breaker cap")
add_label(-4.7,-1.0,1.55,"MAIN BREAKER",size=9)

# Main busbar runs across the site
add_box(-3.8, -3.55, -3.5, 3.5, 1.85, 2.05, "#B87333", "Main copper busbar")
add_label(-3.65, -4.15, 2.55, "MAIN BUSBAR", size=9)
add_line([(-4.15,0,2.0),(-3.8,0,2.0)], "#B87333", "Breaker to busbar", 10)

# ---------- Three transformer bays ----------
transformers = [
    {"name":"TR-A", "x":-2.2, "y":-2.45, "load":"LOAD BANK A", "loadx":5.1, "loady":-2.5},
    {"name":"TR-B", "x":-2.2, "y":0.0, "load":"LOAD BANK B", "loadx":5.1, "loady":0.0},
    {"name":"TR-C", "x":-2.2, "y":2.45, "load":"LOAD BANK C", "loadx":5.1, "loady":2.5},
]
for tr in transformers:
    x, y, name = tr["x"], tr["y"], tr["name"]
    # Bay foundation
    add_box(x-0.85,x+1.35,y-0.9,y+0.9,0.0,0.13,"#BFC8D2",f"{name} foundation")
    # Transformer tank and lid
    add_box(x-0.55,x+0.75,y-0.62,y+0.62,0.15,1.75,"#7C8C9C",f"{name} transformer tank")
    add_box(x-0.48,x+0.68,y-0.56,y+0.56,1.75,1.92,"#A9B5C1",f"{name} transformer lid")
    # Cooling fins on both sides
    for i in range(5):
        xx = x - 0.42 + i*0.22
        add_box(xx,xx+0.07,y-0.78,y-0.64,0.35,1.55,"#526779",f"{name} cooling fin")
        add_box(xx,xx+0.07,y+0.64,y+0.78,0.35,1.55,"#526779",f"{name} cooling fin")
    # Three bushings/terminals
    for j, (phase, color, current) in enumerate(phase_data):
        yy = y - 0.34 + j*0.34
        add_box(x+0.12,x+0.28,yy-0.09,yy+0.09,1.92,2.35,color,f"{name} {phase} bushing")
        add_marker(x+0.20,yy,2.4,color,f"{name} {phase} terminal",5)
    # label above the unit
    add_label(x+0.05,y,3.05,name,size=10)
    # connection from busbar to transformer
    add_line([(-3.55,y,2.0),(x-0.75,y,2.0),(x-0.45,y,2.0)], "#B87333", f"{name} bus connection", 5)
    # small breaker block between transformer and feeders
    add_box(x+1.05,x+1.42,y-0.35,y+0.35,0.18,0.85,"#64748B",f"{name} feeder breaker")
    add_box(x+1.12,x+1.35,y-0.20,y+0.20,0.85,0.98,"#82D4B5",f"{name} breaker handle")
    # Feeder phase wires extend to load bank, with a small raised routing point
    for j,(phase,color,current) in enumerate(phase_data):
        yy = y - 0.38 + j*0.38
        z = 1.55 - j*0.08
        add_line([(x+1.42,yy,z),(x+2.0,yy,z),(x+2.55,yy,z+0.15),(x+3.25,yy,z+0.15),(x+4.0,yy,z)], color, f"{name} phase {phase} feeder", 5)
        add_marker(x+2.55,yy,z+0.15,color,f"{name} {phase} feeder joint",4)
        # Inline switch
        add_box(x+2.72,x+2.95,yy-0.10,yy+0.10,z+0.02,z+0.24,"#7DD3B0",f"{name} phase {phase} switch")
        # load bank blocks at the right
        lx = tr["loadx"]
        ly = tr["loady"] + (j-1)*0.34
        add_line([(x+4.0,yy,z),(lx-0.35,ly,0.75)], color, f"{name} {phase} load lead", 4)
        add_box(lx-0.35,lx+0.55,ly-0.20,ly+0.20,0.25,0.85,color,f"{name} {phase} load module")
    add_label(tr["loadx"]+0.1,tr["loady"]-0.85,1.45,tr["load"],size=9)

# Standby / tie feeder along front edge
add_line([(-1.1,-3.65,0.45),(1.0,-3.65,0.45),(3.3,-3.65,0.45),(5.4,-3.65,0.45)], "#8795A5", "Standby tie feeder", 4, "dash")
add_box(1.0,1.38,-3.83,-3.47,0.35,0.72,"#A7B3C0","Standby isolator")
add_label(2.6,-4.2,0.75,"STANDBY FEEDER",size=9)

# Small warning/monitoring panel at the front
add_box(-5.7,-4.0,-3.9,-2.2,0.05,1.05,"#344256","Monitoring panel")
add_box(-5.55,-4.15,-3.72,-2.38,1.05,1.12,"#DDE9F5","Monitoring panel screen")
add_label(-4.85,-3.05,1.42,"MONITOR",size=9)



# ---------- Animated current-flow particles ----------
# Visual particles illustrate simulated current direction from each transformer
# feeder toward its load bank. This is an illustrative software animation.
flow_paths = []
for tr in transformers:
    x, y = tr["x"], tr["y"]
    for j, (phase, color, current) in enumerate(phase_data):
        yy = y - 0.38 + j * 0.38
        z = 1.55 - j * 0.08
        path = [
            (x + 1.42, yy, z),
            (x + 2.00, yy, z),
            (x + 2.55, yy, z + 0.15),
            (x + 3.25, yy, z + 0.15),
            (x + 4.00, yy, z),
            (tr["loadx"] - 0.35, tr["loady"] + (j - 1) * 0.34, 0.75),
        ]
        flow_paths.append((phase, color, float(current), path, tr["name"]))

def point_along_path(path, fraction):
    lengths = []
    total = 0.0
    for a, b in zip(path[:-1], path[1:]):
        length = math.sqrt(sum((b[k] - a[k]) ** 2 for k in range(3)))
        lengths.append(length)
        total += length
    if total <= 0:
        return path[0]
    target = (fraction % 1.0) * total
    walked = 0.0
    for idx, length in enumerate(lengths):
        if walked + length >= target:
            ratio = (target - walked) / length if length else 0.0
            a, b = path[idx], path[idx + 1]
            return tuple(a[k] + (b[k] - a[k]) * ratio for k in range(3))
        walked += length
    return path[-1]

# Two marker layers per phase: a soft halo and a bright core make the motion
# easier to see against the feeder wires.
particle_trace_indices = []
particle_count = 5
frame_count = 120
for phase, color, current, path, transformer_name in flow_paths:
    initial_points = [point_along_path(path, pidx / particle_count) for pidx in range(particle_count)]
    halo_idx = len(fig.data)
    particle_trace_indices.extend([halo_idx, halo_idx + 1])
    halo_size = max(8, min(12, 7 + current / 45))
    core_size = max(3, min(4.5, 2.5 + current / 100))
    fig.add_trace(go.Scatter3d(
        x=[pt[0] for pt in initial_points],
        y=[pt[1] for pt in initial_points],
        z=[pt[2] + 0.025 for pt in initial_points],
        mode="markers",
        marker=dict(size=halo_size, color=color, opacity=0.22, line=dict(width=0)),
        name=f"{transformer_name} {phase} flow glow",
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter3d(
        x=[pt[0] for pt in initial_points],
        y=[pt[1] for pt in initial_points],
        z=[pt[2] + 0.035 for pt in initial_points],
        mode="markers",
        marker=dict(size=core_size, color=color, opacity=1.0,
                    line=dict(color="#FFFFFF", width=0.7)),
        name=f"{transformer_name} {phase} current flow",
        showlegend=False,
        hovertemplate=f"<b>{transformer_name} · Phase {phase}</b><br>Simulated current: {current:.1f} A<br>Direction: transformer → load bank<extra></extra>",
    ))

# If a transfer has been performed, add a visible green marker to the 3D
# standby/tie feeder. This is a visual simulation of the selected transfer path.
transfer_3d_trace_index = None
transfer_3d_start_x = None
transfer_3d_end_x = None
if "last_transfer" in st.session_state:
    transfer_event = st.session_state.last_transfer
    transfer_x_positions = {"R": -0.2, "Y": 1.6, "B": 3.4}
    transfer_3d_start_x = transfer_x_positions[transfer_event["source"]]
    transfer_3d_end_x = transfer_x_positions[transfer_event["destination"]]
    transfer_3d_trace_index = len(fig.data)
    transfer_start = (transfer_3d_start_x, -3.65, 0.62)
    fig.add_trace(go.Scatter3d(
        x=[transfer_start[0]], y=[transfer_start[1]], z=[transfer_start[2]],
        mode="markers",
        marker=dict(size=9, color="#10B981", opacity=1.0,
                    line=dict(color="#FFFFFF", width=1.5)),
        name="Simulated transferred load",
        showlegend=False,
        hovertemplate=(
            f"<b>Simulated transfer: {transfer_event['amount']:.1f} A</b><br>"
            f"Phase {transfer_event['source']} → Phase {transfer_event['destination']}"
            "<extra></extra>"
        )
    ))
    particle_trace_indices.append(transfer_3d_trace_index)

animation_frames = []
for frame_idx in range(frame_count):
    frame_data = []
    for phase, color, current, path, transformer_name in flow_paths:
        # Faster current gives a slightly faster particle flow in this demo.
        speed = 0.55 + (max(0.0, current) / 200.0) * 0.9
        points = [
            point_along_path(path, pidx / particle_count + frame_idx * speed / frame_count)
            for pidx in range(particle_count)
        ]
        # Both layers receive identical coordinates to preserve the glow effect.
        frame_data.append(go.Scatter3d(
            x=[pt[0] for pt in points], y=[pt[1] for pt in points],
            z=[pt[2] + 0.025 for pt in points],
        ))
        frame_data.append(go.Scatter3d(
            x=[pt[0] for pt in points], y=[pt[1] for pt in points],
            z=[pt[2] + 0.035 for pt in points],
        ))

    # Move the green transfer marker along the tie feeder between the selected
    # phases. The existing current-flow particles continue animating as before.
    if transfer_3d_trace_index is not None:
        fraction = frame_idx / max(frame_count - 1, 1)
        transfer_x = transfer_3d_start_x + (transfer_3d_end_x - transfer_3d_start_x) * fraction
        frame_data.append(go.Scatter3d(
            x=[transfer_x], y=[-3.65], z=[0.62]
        ))

    animation_frames.append(go.Frame(name=str(frame_idx), data=frame_data, traces=particle_trace_indices))

fig.frames = animation_frames

# ---------- Plot styling ----------
fig.update_layout(
    height=820,
    margin=dict(l=0, r=0, t=20, b=20),
    paper_bgcolor="#F8FAFC",
    plot_bgcolor="#F8FAFC",
    font=dict(family="Arial", color="#243247", size=11),
    showlegend=False,
    scene=dict(
        bgcolor="#F8FAFC",
        xaxis=dict(visible=False, range=[-7, 8], showbackground=False),
        yaxis=dict(visible=False, range=[-5, 5], showbackground=False),
        zaxis=dict(visible=False, range=[-0.5, 4], showbackground=False),
        aspectmode="manual",
        aspectratio=dict(x=1.75, y=1.25, z=0.85),
        camera=dict(eye=dict(x=1.8, y=2.0, z=1.4), projection=dict(type="orthographic")),
        dragmode="orbit",
    ),
)

st.subheader("Interactive 3D Substation Model")
st.caption("Current-flow animation: press PLAY to keep particles moving continuously; press PAUSE to stop them. Smaller glowing particles show simulated flow from transformer to load bank. Drag to rotate • Scroll to zoom.")

# Render Plotly in an HTML component so JavaScript can keep cycling through
# animation frames until the user explicitly presses Pause. Native Plotly
# animation buttons only play the finite frame sequence once.
plot_id = "gridtwin-current-flow-plot"
post_script = r"""
const gd = document.getElementById('{plot_id}');
let frameIndex = 0;
let isPlaying = false;
let timerId = null;
const totalFrames = 120;
function playCurrentFlow() {
  if (isPlaying) return;
  isPlaying = true;
  const playBtn = document.getElementById('gt-play');
  const pauseBtn = document.getElementById('gt-pause');
  playBtn.classList.add('active');
  pauseBtn.classList.remove('active');
  const step = () => {
    if (!isPlaying) return;
    Plotly.animate(gd, [String(frameIndex)], {
      mode: 'immediate',
      frame: {duration: 45, redraw: true},
      transition: {duration: 0}
    }).then(() => {
      frameIndex = (frameIndex + 1) % totalFrames;
      if (isPlaying) timerId = setTimeout(step, 0);
    }).catch(() => { if (isPlaying) timerId = setTimeout(step, 50); });
  };
  step();
}
function pauseCurrentFlow() {
  isPlaying = false;
  if (timerId !== null) clearTimeout(timerId);
  const playBtn = document.getElementById('gt-play');
  const pauseBtn = document.getElementById('gt-pause');
  playBtn.classList.remove('active');
  pauseBtn.classList.add('active');
  Plotly.animate(gd, [], {mode: 'immediate', frame: {duration: 0, redraw: false}, transition: {duration: 0}});
}
document.getElementById('gt-play').addEventListener('click', playCurrentFlow);
document.getElementById('gt-pause').addEventListener('click', pauseCurrentFlow);
"""
plot_html = fig.to_html(
    full_html=False,
    include_plotlyjs="cdn",
    config={"displaylogo": False, "scrollZoom": True, "responsive": True},
    div_id=plot_id,
    post_script=post_script,
)
controls_html = r"""
<div class="gt-controls">
  <button id="gt-play" class="gt-button gt-play" type="button">▶ &nbsp; PLAY CURRENT FLOW</button>
  <button id="gt-pause" class="gt-button gt-pause active" type="button">Ⅱ &nbsp; PAUSE</button>
  <span class="gt-status"><span class="gt-dot"></span> SIMULATED CURRENT FLOW</span>
</div>
<style>
  .gt-controls { display:flex; align-items:center; justify-content:center; flex-wrap:wrap; gap:12px; padding:14px 10px; font-family:Arial,sans-serif; background:#f8fafc; border-radius:14px 14px 0 0; }
  .gt-button { border:1px solid #cbd5e1; border-radius:10px; padding:12px 18px; font-size:13px; font-weight:700; letter-spacing:.3px; cursor:pointer; transition:all .18s ease; box-shadow:0 2px 5px rgba(15,23,42,.08); }
  .gt-play { color:#fff; background:linear-gradient(135deg,#0f766e,#0891b2); border-color:#0e7490; }
  .gt-pause { color:#334155; background:#fff; }
  .gt-button:hover { transform:translateY(-1px); box-shadow:0 4px 10px rgba(15,23,42,.15); }
  .gt-button.active { outline:2px solid #7dd3fc; outline-offset:2px; }
  .gt-status { display:flex; align-items:center; gap:7px; font-size:10px; font-weight:700; color:#64748b; letter-spacing:.8px; }
  .gt-dot { width:8px; height:8px; border-radius:50%; background:#10b981; box-shadow:0 0 0 4px #d1fae5; }
</style>
"""
st.components.v1.html(
    f"<!doctype html><html><head><meta charset='utf-8'></head><body style='margin:0;background:#f8fafc'>{controls_html}{plot_html}</body></html>",
    height=850,
    scrolling=False,
)
# ---------- Monitoring panels ----------
st.divider()
st.subheader("Phase Monitoring")
cols = st.columns(3)
for col, (phase, color, current) in zip(cols, phase_data):
    with col:
        st.markdown(f"### <span style='color:{color}'>●</span> Phase {phase}", unsafe_allow_html=True)
        st.metric("Simulated current", f"{current} A")
        if current >= 150:
            st.error("High-current demo indicator")
        elif current >= 110:
            st.warning("Elevated-current demo indicator")
        else:
            st.success("Normal demo indicator")

st.caption(
    "Engineering note: transformer placement, phase routing, busbar topology, switchgear and load-bank layout "
    "are illustrative. The temperature is a simple visual estimate, not a validated thermal replica model. "
    "Confirm all electrical details against the project design before using for engineering decisions."
)
