# 🚁 Mavic 2 Pro — Webots Controller

A Python controller for the **DJI Mavic 2 Pro** drone inside [Webots](https://cyberbotics.com/), driven by a real gamepad (BetaFPV Mode 2 layout). Full PID flight control with auto takeoff, auto land, and motor arming.

---

## ✨ Features

- **Auto Takeoff** — on start, the drone automatically climbs to 1 metre and hovers
- **Manual Flight** — full roll, pitch, yaw and altitude control via gamepad
- **Auto Land** — smooth proportional descent, motors cut on touchdown
- **Re-arm** — push throttle up after landing to take off again
- **PID Flight Control** — independent PID loops for roll, pitch, yaw and altitude
- **Gamepad Tester** — standalone GUI tool to identify your controller's axes and buttons

---

## 📁 Project Structure

```
controllers/
└── Mavic2controller/
    ├── Mavic2controller.py   # Main drone controller
    ├── mavicDataCollection.py # Data logging & live plotting
    └── gamepad_test.py       # Gamepad axis/button visualiser
```

---

## 🎮 Gamepad Layout (Mode 2)

| Stick / Switch | Action |
|---|---|
| Left Y | Throttle (up / down) |
| Left X | Yaw (rotate left / right) |
| Right X | Roll (strafe left / right) |
| Right Y | Pitch (forward / backward) |
| **A4 switch** | **Auto-land toggle** |

> A4 is a two-position switch. Flip to `+1` → auto-land starts. Flip back to `-1` and to `+1` again → cancels and re-arms.

---

## 🧠 How the PID Works

Each axis has its own PID controller running every simulation step:

```
Roll   → kp=0.21  ki=0.1   kd=0.1
Pitch  → kp=0.21  ki=0.2   kd=0.09
Yaw    → kp=0.13  ki=0.01  kd=0.1
Alt    → kp=2.0   ki=0.01  kd=2.0
```

Motor mixing follows a standard **X-frame** layout:

```
      FRONT
FL (CCW)  FR (CW)
    ╲  ╱
    ╱  ╲
RL (CW)  RR (CCW)
      REAR
```

---

## 🛠️ Requirements

```bash
pip install pygame
```

- [Webots R2023+](https://cyberbotics.com/)
- Python 3.8+
- Any USB gamepad (tested with BetaFPV controller)

---

## 🚀 Running

1. Open the world in Webots
2. Make sure your gamepad is plugged in
3. Hit **Play** — the drone auto-arms and climbs to 1 m

---

## 🕹️ Gamepad Tester

Not sure which axis is which on your controller? Run this standalone (no Webots needed):

```bash
python gamepad_test.py
```

Opens a GUI window showing all axes as live bars and all buttons highlighted when pressed.

---

## ✈️ Auto Land Behaviour

| State | What happens |
|---|---|
| A4 flipped to `+1` | Drone descends smoothly (force scales with height) |
| Altitude < 0.15 m | Motors cut, drone sits on ground |
| Throttle pushed up | Drone re-arms and climbs back to 1 m |

---

## 📊 Data Collection

`mavicDataCollection.py` logs flight data and plots roll, pitch, yaw and altitude live in a separate thread. Run it as the controller instead of `Mavic2controller.py` when you want to analyse flight performance.
