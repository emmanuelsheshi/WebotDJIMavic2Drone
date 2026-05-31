"""Mavic 2 Pro controller — BetaFPV Mode 2 gamepad.

Control law from DataCollection reference:
  • Altitude  : PID on GPS altitude error  (left stick Y = climb/descend/hold)
  • Roll/Pitch: PID on angle error in degrees
  • Yaw       : PID on heading error in degrees
  • Motor mix : exact DataCollection X-frame layout

Gamepad (BetaFPV Mode 2):
    Left  Y  → Altitude (up=climb, centre=hold, down=descend)
    Left  X  → Yaw
    Right X  → Roll
    Right Y  → Pitch

Prerequisites:  pip install pygame
"""

import math
import pygame
from controller import Robot


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def clamp(value, value_min, value_max):
    return min(max(value, value_min), value_max)


def dead_zone(v, dz):
    if abs(v) < dz:
        return 0.0
    sign = 1.0 if v > 0.0 else -1.0
    return sign * (abs(v) - dz) / (1.0 - dz)


# ─────────────────────────────────────────────────────────────────────────────
# PID Controller  (matches DataCollection reference exactly)
# ─────────────────────────────────────────────────────────────────────────────

class PIDController:
    def __init__(self, kp, ki, kd, min_output=-10, max_output=10):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.min_output = min_output
        self.max_output = max_output
        self.integral = 0.0
        self.previous_error = 0.0
        self.first_update = True

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0
        p_term = self.kp * error
        self.integral = clamp(self.integral + error * dt, -5.0, 5.0)
        i_term = self.ki * self.integral
        if self.first_update:
            d_term = 0.0
            self.first_update = False
        else:
            d_term = self.kd * (error - self.previous_error) / dt
        self.previous_error = error
        return clamp(p_term + i_term + d_term, self.min_output, self.max_output)

    def reset(self):
        self.integral = 0.0
        self.previous_error = 0.0
        self.first_update = True


# ─────────────────────────────────────────────────────────────────────────────
# Gains — taken directly from DataCollection reference
# ─────────────────────────────────────────────────────────────────────────────

K_VERTICAL_THRUST = 70.0

ROLL_PID  = dict(kp=0.21, ki=0.1,  kd=0.1)

PITCH_PID = dict(kp=0.21, ki=0.2,  kd=0.09)
YAW_PID   = dict(kp=0.13, ki=0.01, kd=0.1)

ALT_PID   = dict(kp=2.0, ki=0.01, kd=2.0, min_output=-20, max_output=20)

MAX_TILT           = 10.0    # degrees max roll/pitch from stick
MAX_YAW_RATE       = 0.5     # degrees added to target yaw per sim-step
MAX_VERTICAL_SPEED = 0.01    # metres added to target altitude per sim-step

# ─────────────────────────────────────────────────────────────────────────────
# BetaFPV gamepad axis mapping  (Mode 2)
# ─────────────────────────────────────────────────────────────────────────────

AXIS_LEFT_X  = 3    # Yaw
AXIS_LEFT_Y  = 2    # Altitude
AXIS_RIGHT_X = 0    # Roll
AXIS_RIGHT_Y = 1    # Pitch
DEAD_ZONE    = 0.10

LAND_AXIS    = 4    # A4 — flip past centre to auto-land
LAND_SPEED   = 0.05 # metres per sim-step descent rate


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    robot    = Robot()
    timestep = int(robot.getBasicTimeStep())
    dt       = timestep / 1000.0

    # ── Sensors ───────────────────────────────────────────────────────────────
    imu  = robot.getDevice("inertial unit"); imu.enable(timestep)
    gps  = robot.getDevice("gps");           gps.enable(timestep)
    gyro = robot.getDevice("gyro");          gyro.enable(timestep)
    cam  = robot.getDevice("camera")
    if cam:
        cam.enable(timestep)

    # ── Motors ────────────────────────────────────────────────────────────────
    motor_fl = robot.getDevice("front left propeller")
    motor_fr = robot.getDevice("front right propeller")
    motor_rl = robot.getDevice("rear left propeller")
    motor_rr = robot.getDevice("rear right propeller")
    for m in (motor_fl, motor_fr, motor_rl, motor_rr):
        m.setPosition(float("inf"))
        m.setVelocity(0.0)

    # ── Gamepad ───────────────────────────────────────────────────────────────
    gamepad = None
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() > 0:
        gamepad = pygame.joystick.Joystick(0)
        gamepad.init()
        print(f"[Gamepad] {gamepad.get_name()} ({gamepad.get_numaxes()} axes)")
    else:
        print("[Gamepad] None found — drone will hover in place.")

    # ── PID instances ─────────────────────────────────────────────────────────
    roll_pid  = PIDController(**ROLL_PID)
    pitch_pid = PIDController(**PITCH_PID)
    yaw_pid   = PIDController(**YAW_PID)
    alt_pid   = PIDController(**ALT_PID)

    # ── State ─────────────────────────────────────────────────────────────────
    robot.step(timestep)
    target_altitude  = 1.0   # auto takeoff to 1 m on start
    target_yaw       = math.degrees(imu.getRollPitchYaw()[2]) % 360.0
    landing          = False
    landed           = False
    land_axis_prev   = gamepad.get_axis(LAND_AXIS) if gamepad else -1.0

    print("[Mavic2] Running — taking off to 1 m")

    # ── Simulation loop ───────────────────────────────────────────────────────
    while robot.step(timestep) != -1:

        # ── Sensors (degrees, matching DataCollection reference) ──────────
        roll_r, pitch_r, yaw_r = imu.getRollPitchYaw()
        roll     = math.degrees(roll_r)
        pitch    = math.degrees(pitch_r)
        yaw      = math.degrees(yaw_r) % 360.0
        altitude = gps.getValues()[2]

        # ── Gamepad ───────────────────────────────────────────────────────
        alt_cmd = yaw_cmd = roll_cmd = pitch_cmd = 0.0
        if gamepad:
            pygame.event.pump()
            land_axis_now = gamepad.get_axis(LAND_AXIS)
            if land_axis_now > 0 and land_axis_prev <= 0:  # rising edge
                landing = not landing
                if landing:
                    alt_pid.reset()
                    print("[Mavic2] Auto-land ON")
                else:
                    landing = False
                    target_altitude = 1.0
                    alt_pid.reset()
                    print("[Mavic2] Auto-land OFF — taking off")
            land_axis_prev = land_axis_now
            alt_cmd   =  dead_zone( gamepad.get_axis(AXIS_LEFT_Y),  DEAD_ZONE)
            yaw_cmd   = -dead_zone( gamepad.get_axis(AXIS_LEFT_X),  DEAD_ZONE)
            roll_cmd  =  dead_zone( gamepad.get_axis(AXIS_RIGHT_X), DEAD_ZONE)
            pitch_cmd =  dead_zone( gamepad.get_axis(AXIS_RIGHT_Y), DEAD_ZONE)

        # ── Auto-land ─────────────────────────────────────────────────────
        if landing:
            alt_cmd = yaw_cmd = roll_cmd = pitch_cmd = 0.0
            if altitude < 0.15:
                for m in (motor_fl, motor_fr, motor_rl, motor_rr):
                    m.setVelocity(0.0)
                print("[Mavic2] Landed — push throttle up to take off")
                landing = False
                landed  = True
                target_altitude = 0.0

        # ── Landed: wait for throttle up to re-arm ────────────────────────
        if landed:
            if alt_cmd > 0.1:
                landed = False
                target_altitude = 1.0
                alt_pid.reset()
                print("[Mavic2] Taking off to 1 m")
            else:
                for m in (motor_fl, motor_fr, motor_rl, motor_rr):
                    m.setVelocity(0.0)
                continue

        # ── Setpoints ─────────────────────────────────────────────────────
        if not landing:
            target_altitude = clamp(target_altitude + alt_cmd * MAX_VERTICAL_SPEED, 0.0, 10.0)
        target_yaw      = (target_yaw + yaw_cmd * MAX_YAW_RATE) % 360.0
        target_roll     = roll_cmd  * MAX_TILT
        target_pitch    = pitch_cmd * MAX_TILT

        # ── Errors ────────────────────────────────────────────────────────
        roll_error     = roll  - target_roll
        pitch_error    = pitch - target_pitch
        yaw_error      = ((target_yaw - yaw + 180.0) % 360.0) - 180.0
        altitude_error = target_altitude - altitude

        # ── PID outputs ───────────────────────────────────────────────────
        roll_input     = roll_pid.compute(roll_error,    dt)
        pitch_input    = pitch_pid.compute(pitch_error,  dt)
        yaw_input      = yaw_pid.compute(yaw_error,     dt)
        altitude_input = max(-20.0, -altitude * 6.0) if landing else alt_pid.compute(altitude_error, dt)
        # ── Motor mixing — DataCollection reference X-frame ───────────────
        #        FRONT
        #   FL (CCW)  FR (CW)
        #       ╲  ╱
        #       ╱  ╲
        #   RL (CW)  RR (CCW)
        #        REAR
        base = K_VERTICAL_THRUST + altitude_input

        fl = base - yaw_input + pitch_input - roll_input
        fr = base + yaw_input + pitch_input + roll_input
        rl = base + yaw_input - pitch_input - roll_input
        rr = base - yaw_input - pitch_input + roll_input

        motor_fl.setVelocity( fl)
        motor_fr.setVelocity(-fr)
        motor_rl.setVelocity(-rl)
        motor_rr.setVelocity( rr)


if __name__ == "__main__":
    main()
