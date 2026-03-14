import tkinter as tk
from tkinter import ttk

BG = "#f4f4f4"
LINE_COLOR = "#222222"
YELLOW = "#ffe94d"
BLUE = "#21a7df"
ORANGE = "#f7b52c"
TRAY = "#111111"

class TrayFlowSimulator:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Grinding / Bundling Flow Simulator")
        self.root.geometry("1450x860")
        self.root.configure(bg=BG)

        self.mode = tk.StringVar(value="normal")
        self.grinding_speed = tk.DoubleVar(value=32.0)
        self.bundle_speed = tk.DoubleVar(value=40.0)
        self.animate = tk.BooleanVar(value=True)
        self.show_labels = tk.BooleanVar(value=True)

        self.trays_main = []
        self.trays_bundle = []
        self.last_main_spawn = 0.0
        self.time_accum = 0.0
        self.running = True

        self.employee_items = {}
        self.employee_labels = {}

        self._build_ui()
        self._build_layout()
        self._tick()

    def _build_ui(self) -> None:
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=12, pady=8)

        ttk.Label(top, text="Mode:").pack(side="left", padx=(0, 6))
        ttk.Radiobutton(top, text="Normal Pack", value="normal", variable=self.mode, command=self.refresh_mode).pack(side="left")
        ttk.Radiobutton(top, text="Bundle Mode", value="bundle", variable=self.mode, command=self.refresh_mode).pack(side="left", padx=(8, 14))

        ttk.Label(top, text="Grinding trays/min").pack(side="left")
        ttk.Scale(top, from_=10, to=90, variable=self.grinding_speed, orient="horizontal", length=180).pack(side="left", padx=6)
        self.grind_value = ttk.Label(top, text="32.0")
        self.grind_value.pack(side="left", padx=(0, 16))

        ttk.Label(top, text="Bundling trays/min").pack(side="left")
        ttk.Scale(top, from_=10, to=90, variable=self.bundle_speed, orient="horizontal", length=180).pack(side="left", padx=6)
        self.bundle_value = ttk.Label(top, text="40.0")
        self.bundle_value.pack(side="left", padx=(0, 16))

        controls = tk.Frame(self.root, bg=BG)
        controls.pack(fill="x", padx=12, pady=(0, 8))

        ttk.Button(controls, text="Pause / Resume", command=self.toggle_running).pack(side="left")
        ttk.Button(controls, text="Reset Trays", command=self.reset_trays).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="Animate", variable=self.animate).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="Show Labels", variable=self.show_labels, command=self.refresh_mode).pack(side="left", padx=8)

        self.status_label = ttk.Label(
            controls,
            text="Goal: show why existing grinding labor cannot fully cover bundle labor at the same time.",
        )
        self.status_label.pack(side="left", padx=18)

        info = tk.Frame(self.root, bg=BG)
        info.pack(fill="x", padx=12, pady=(0, 8))

        self.kpi_label = ttk.Label(info, text="")
        self.kpi_label.pack(side="left")

        note = ttk.Label(
            info,
            text="Yellow = grinding crew | Blue = dedicated bundle labor | Orange = grinding labor pulled into bundle line",
        )
        note.pack(side="left", padx=18)

        self.canvas = tk.Canvas(self.root, width=1410, height=720, bg=BG, highlightthickness=0)
        self.canvas.pack(padx=10, pady=6)

    def _build_layout(self) -> None:
        c = self.canvas
        c.delete("all")
        c.create_text(705, 25, text="Grinding Room / Bundle Operation Flow", font=("Arial", 20, "bold"))

        self._station("Grinding Room", 80, 45, 610, 95, bold=True)
        self._station("Vemag / Brick", 15, 115, 75, 332, vertical=True)
        self._station("Blender Mixer Augers", 200, 120, 530, 155)
        self._station("Product Dump", 610, 45, 675, 155, vertical=True)
        self._station("Grinder", 535, 120, 610, 155)
        self._station("Denester", 140, 175, 265, 255)
        self._station("Multivac", 80, 292, 530, 332)
        self._station("", 530, 175, 645, 215)
        self._station("", 530, 215, 645, 255)
        self._station("", 530, 255, 645, 332)
        self._station("", 645, 175, 725, 332)

        self._station("Index Conveyor", 750, 385, 955, 425)
        self._station("Shanklin", 955, 365, 1145, 445)
        self._station("Heat Tunnel", 1210, 365, 1400, 445)
        self._station("Pack", 1400, 385, 1465, 425)
        self._station("Pallet", 1210, 255, 1270, 305)
        self._station("Tape, conveyor", 1270, 275, 1460, 305)

        c.create_line(75, 312, 645, 312, fill=LINE_COLOR, width=2)
        c.create_line(645, 312, 645, 405, fill=LINE_COLOR, width=2)
        c.create_line(645, 405, 750, 405, fill=LINE_COLOR, width=2)
        c.create_line(1145, 405, 1210, 405, fill=LINE_COLOR, width=2)
        c.create_line(1400, 405, 1460, 405, fill=LINE_COLOR, width=2)

        c.create_rectangle(980, 120, 1035, 145, fill=YELLOW, outline="")
        c.create_text(1070, 133, text="Grinding labor", anchor="w", font=("Arial", 11))
        c.create_rectangle(980, 155, 1035, 180, fill=BLUE, outline="")
        c.create_text(1070, 168, text="Dedicated bundle labor", anchor="w", font=("Arial", 11))
        c.create_rectangle(980, 190, 1035, 215, fill=ORANGE, outline="")
        c.create_text(1070, 203, text="Grinding labor pulled into bundle tasks", anchor="w", font=("Arial", 11))

        # Grinding labor
        self._employee("2", 110, 135, YELLOW)
        self._employee("1", 560, 158, YELLOW)
        self._employee("3", 260, 215, YELLOW)
        self._employee("4", 655, 235, YELLOW)
        self._employee("5", 775, 235, YELLOW)
        self._employee("6", 760, 332, YELLOW)
        self._employee("7", 810, 332, YELLOW)
        self._employee("8", 870, 312, YELLOW)

        # Pulled grinding labor
        self._employee("4", 700, 405, ORANGE, key="4_orange")
        self._employee("6", 760, 465, ORANGE, key="6_orange")
        self._employee("7", 825, 525, ORANGE, key="7_orange")
        self._employee("8", 1160, 280, ORANGE, key="8_orange")

        # Dedicated bundle labor
        self._employee("6", 1070, 215, BLUE, key="6_blue")
        self._employee("4", 1040, 365, BLUE, key="4_blue")
        self._employee("5", 1420, 280, BLUE, key="5_blue")
        self._employee("3", 1485, 405, BLUE, key="3_blue")
        self._employee("2", 1485, 430, BLUE, key="2_blue")
        self._employee("1", 1425, 450, BLUE, key="1_blue")

        self.refresh_mode()

    def _station(self, label, x1, y1, x2, y2, vertical=False, bold=False):
        self.canvas.create_rectangle(x1, y1, x2, y2, outline=LINE_COLOR, width=2)
        if label:
            font = ("Arial", 15, "bold") if bold else ("Arial", 11)
            if vertical:
                self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=label, angle=90, font=font)
            else:
                self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=label, font=font)

    def _employee(self, label, x, y, color, key=None):
        key = key or label
        rect = self.canvas.create_rectangle(x, y, x + 62, y + 22, fill=color, outline="")
        text = self.canvas.create_text(x + 31, y + 11, text=label, font=("Arial", 11))
        self.employee_items[key] = rect
        self.employee_labels[key] = text

    def toggle_running(self):
        self.running = not self.running

    def reset_trays(self):
        for item in self.trays_main + self.trays_bundle:
            self.canvas.delete(item)
        self.trays_main.clear()
        self.trays_bundle.clear()
        self.last_main_spawn = 0.0
        self.time_accum = 0.0

    def refresh_mode(self):
        bundle_mode = self.mode.get() == "bundle"
        show_labels = self.show_labels.get()

        for key in ["6_blue", "4_blue", "5_blue", "3_blue", "2_blue", "1_blue"]:
            state = "normal" if bundle_mode else "hidden"
            self.canvas.itemconfigure(self.employee_items[key], state=state)
            self.canvas.itemconfigure(self.employee_labels[key], state=state if show_labels else "hidden")

        for key in ["4_orange", "6_orange", "7_orange", "8_orange"]:
            state = "normal" if bundle_mode else "hidden"
            self.canvas.itemconfigure(self.employee_items[key], state=state)
            self.canvas.itemconfigure(self.employee_labels[key], state=state if show_labels else "hidden")

        for key in ["1", "2", "3", "4", "5", "6", "7", "8"]:
            self.canvas.itemconfigure(self.employee_labels[key], state="normal" if show_labels else "hidden")

        if bundle_mode:
            self.status_label.config(text="Bundle mode: positions 4,5,6,7,8 are pulled from grinding to support the bundle line.")
        else:
            self.status_label.config(text="Normal mode: all yellow crew stays on the grinding line.")

        self._update_kpis()

    def _spawn_main_tray(self):
        item = self.canvas.create_rectangle(90, 304, 100, 314, fill=TRAY, outline=TRAY)
        self.trays_main.append(item)

    def _spawn_bundle_tray(self):
        item = self.canvas.create_rectangle(754, 399, 764, 409, fill=TRAY, outline=TRAY)
        self.trays_bundle.append(item)

    def _move_main_trays(self, dt):
        speed = self.grinding_speed.get()
        pixels_per_second = speed * 1.55 if self.animate.get() else 0
        remove = []
        for item in self.trays_main:
            x1, y1, x2, y2 = self.canvas.coords(item)
            if self.mode.get() == "normal":
                if x2 < 635:
                    self.canvas.move(item, pixels_per_second * dt, 0)
                else:
                    remove.append(item)
            else:
                if x2 < 645:
                    self.canvas.move(item, pixels_per_second * dt, 0)
                elif y2 < 405:
                    self.canvas.move(item, 0, pixels_per_second * dt * 0.9)
                elif x2 < 750:
                    self.canvas.move(item, pixels_per_second * dt, 0)
                else:
                    remove.append(item)
                    self._spawn_bundle_tray()
        for item in remove:
            if item in self.trays_main:
                self.canvas.delete(item)
                self.trays_main.remove(item)

    def _move_bundle_trays(self, dt):
        speed = self.bundle_speed.get()
        pixels_per_second = speed * 1.35 if self.animate.get() else 0
        remove = []
        for item in self.trays_bundle:
            x1, y1, x2, y2 = self.canvas.coords(item)
            if x2 < 1145:
                self.canvas.move(item, pixels_per_second * dt, 0)
            elif x2 < 1400:
                self.canvas.move(item, pixels_per_second * dt * 0.85, 0)
            elif x2 < 1462:
                self.canvas.move(item, pixels_per_second * dt * 0.65, 0)
            else:
                remove.append(item)
        for item in remove:
            if item in self.trays_bundle:
                self.canvas.delete(item)
                self.trays_bundle.remove(item)

    def _update_kpis(self):
        grind = self.grinding_speed.get()
        bundle = self.bundle_speed.get()
        lbs_hr = grind * 60
        if self.mode.get() == "bundle":
            msg = f"Grinding: {grind:.1f} trays/min (~{lbs_hr:,.0f} lbs/hr) | Bundle: {bundle:.1f} trays/min | Yellow positions pulled: 4,5,6,7,8"
        else:
            msg = f"Grinding: {grind:.1f} trays/min (~{lbs_hr:,.0f} lbs/hr) | Bundle line idle"
        self.kpi_label.config(text=msg)

    def _tick(self):
        self.grind_value.config(text=f"{self.grinding_speed.get():.1f}")
        self.bundle_value.config(text=f"{self.bundle_speed.get():.1f}")
        self._update_kpis()

        dt = 0.05
        if self.running:
            self.time_accum += dt
            main_interval = max(0.10, 60.0 / max(1.0, self.grinding_speed.get()) / 4.0)
            if self.time_accum - self.last_main_spawn >= main_interval:
                self._spawn_main_tray()
                self.last_main_spawn = self.time_accum
            self._move_main_trays(dt)
            self._move_bundle_trays(dt)

        self.root.after(50, self._tick)

def main():
    root = tk.Tk()
    app = TrayFlowSimulator(root)
    root.mainloop()

if __name__ == "__main__":
    main()
