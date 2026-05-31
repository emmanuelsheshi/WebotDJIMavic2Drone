import pygame, sys, tkinter as tk

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No gamepad found.")
    sys.exit(1)

pad = pygame.joystick.Joystick(0)
pad.init()

# ── GUI ───────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title(pad.get_name())
root.resizable(False, False)

tk.Label(root, text="AXES", font=("Courier", 11, "bold")).grid(row=0, column=0, columnspan=3, pady=(8,2))

axis_labels = []
axis_bars   = []
for i in range(pad.get_numaxes()):
    tk.Label(root, text=f"A{i}", font=("Courier", 10), width=3).grid(row=i+1, column=0, padx=(8,2))
    cv = tk.Canvas(root, width=200, height=18, bg="#222", highlightthickness=0)
    cv.grid(row=i+1, column=1, padx=4)
    lbl = tk.Label(root, text="+0.000", font=("Courier", 10), width=7)
    lbl.grid(row=i+1, column=2, padx=(0,8))
    axis_bars.append(cv)
    axis_labels.append(lbl)

sep_row = pad.get_numaxes() + 2
tk.Label(root, text="BUTTONS", font=("Courier", 11, "bold")).grid(row=sep_row, column=0, columnspan=3, pady=(10,4))

btn_labels = []
COLS = 4
for i in range(pad.get_numbuttons()):
    r = sep_row + 1 + i // COLS
    c = i % COLS
    lbl = tk.Label(root, text=f"B{i}\n--", font=("Courier", 9), width=5,
                   relief="groove", bg="#333", fg="white", pady=4)
    lbl.grid(row=r, column=c, padx=3, pady=2)
    btn_labels.append(lbl)

def update():
    pygame.event.pump()
    for i, (cv, lbl) in enumerate(zip(axis_bars, axis_labels)):
        v = pad.get_axis(i)
        cv.delete("all")
        mid = 100
        end = int(mid + v * 95)
        cv.create_rectangle(min(mid, end), 2, max(mid, end), 16,
                             fill="#00aaff", outline="")
        cv.create_line(mid, 0, mid, 18, fill="#888")
        lbl.config(text=f"{v:+.3f}")
    for i, lbl in enumerate(btn_labels):
        if pad.get_button(i):
            lbl.config(text=f"B{i}\nON", bg="#00aa44", fg="white")
        else:
            lbl.config(text=f"B{i}\n--", bg="#333", fg="white")
    root.after(50, update)

update()
root.mainloop()
pygame.quit()

