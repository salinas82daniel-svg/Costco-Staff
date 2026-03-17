import tkinter as tk
from tkinter import ttk
import math

BG = "#f4f4f4"
LINE = "#222222"
YELLOW = "#ffe94d"
BLUE = "#2459ff"
ORANGE = "#f7b52c"
TRAY = "#111111"
PURPLE = "#8e44ad"
RED = "#cc2f2f"

WINDOW_W = 1500
WINDOW_H = 920

# Design-space size (based on your diagram)
DESIGN_W = 1900
DESIGN_H = 820

# Always fit to window
SCALE = min((WINDOW_W - 40) / DESIGN_W, (WINDOW_H - 180) / DESIGN_H)


def sx(x):
    return x * SCALE


def sy(y):
    return y * SCALE


class SimApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Grinding / Bundle Flow Simulator v6")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.configure(bg=BG)

        self.mode = tk.StringVar(value="normal")
        self.trays_per_min = tk.DoubleVar(value=32.0)
        self.changeovers = tk.IntVar(value=0)
        self.sim_minutes = tk.DoubleVar(value=60.0)
        self.time_scale = tk.DoubleVar(value=120.0)
        self.show_labels = tk.BooleanVar(value=True)

        self.running = False
        self.elapsed_sim_sec = 0.0
        self.last_spawn_sec = 0.0
        self.completed_changeovers = 0
        self.changeover_active = False
        self.changeover_end_sec = 0.0

        self.tray_total = 0
        self.regular_case_total = 0
        self.bundle_case_total = 0
        self.regular_pack_buffer = 0
        self.bundle_pack_buffer = 0

        self.tray_items = []
        self.case_items = []
        self.employee_items = {}
        self.employee_labels = {}
        self.kpis = {}

        self._build_ui()
        self._draw_layout()
        self._refresh_mode()
        self._update_labels()
        self._tick()

    def _build_ui(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=8, pady=6)

        ttk.Label(top, text="Mode").pack(side="left")
        ttk.Radiobutton(top, text="Normal Pack", variable=self.mode, value="normal", command=self._refresh_mode).pack(side="left", padx=4)
        ttk.Radiobutton(top, text="Bundle Mode", variable=self.mode, value="bundle", command=self._refresh_mode).pack(side="left", padx=(0, 10))

        ttk.Label(top, text="Trays/min").pack(side="left")
        ttk.Scale(
            top,
            from_=10,
            to=90,
            variable=self.trays_per_min,
            orient="horizontal",
            length=180,
            command=lambda _=None: self._update_labels(),
        ).pack(side="left", padx=4)
        self.lbl_tpm = ttk.Label(top, text="")
        self.lbl_tpm.pack(side="left", padx=(0, 10))

        ttk.Label(top, text="Changeovers").pack(side="left")
        ttk.Spinbox(top, from_=0, to=20, width=5, textvariable=self.changeovers, command=self._update_labels).pack(side="left", padx=4)

        ttk.Label(top, text="Sim minutes").pack(side="left", padx=(8, 0))
        ttk.Spinbox(top, from_=10, to=240, width=6, textvariable=self.sim_minutes, command=self._update_labels).pack(side="left", padx=4)

        ttk.Label(top, text="Speed-up").pack(side="left", padx=(8, 0))
        ttk.Scale(
            top,
            from_=30,
            to=300,
            variable=self.time_scale,
            orient="horizontal",
            length=120,
            command=lambda _=None: self._update_labels(),
        ).pack(side="left", padx=4)
        self.lbl_scale = ttk.Label(top, text="")
        self.lbl_scale.pack(side="left", padx=(0, 8))

        controls = tk.Frame(self.root, bg=BG)
        controls.pack(fill="x", padx=8, pady=(0, 6))

        ttk.Button(controls, text="Start", command=self.start).pack(side="left")
        ttk.Button(controls, text="Pause", command=self.pause).pack(side="left", padx=4)
        ttk.Button(controls, text="Reset", command=self.reset).pack(side="left", padx=4)
        ttk.Checkbutton(controls, text="Show Labels", variable=self.show_labels, command=self._refresh_mode).pack(side="left", padx=6)

        self.status = ttk.Label(
            controls,
            text="Ready. Normal: red trays become blue regular boxes. Bundle: orange trays become purple bundle boxes.",
        )
        self.status.pack(side="left", padx=12)

        kpi_row = tk.Frame(self.root, bg=BG)
        kpi_row.pack(fill="x", padx=8, pady=(0, 6))

        for label in ["Minutes Simulated", "Trays Produced", "Regular Cases", "Bundle Cases", "Completed Changeovers", "Backlog"]:
            box = tk.Frame(kpi_row, bg="white", highlightbackground="#bbbbbb", highlightthickness=1)
            box.pack(side="left", padx=4)
            tk.Label(box, text=label, font=("Arial", 10, "bold"), bg="white").pack(padx=10, pady=(6, 2))
            val = tk.Label(box, text="0", font=("Arial", 12), bg="white")
            val.pack(padx=10, pady=(0, 6))
            self.kpis[label] = val

        self.canvas = tk.Canvas(
            self.root,
            width=int(DESIGN_W * SCALE),
            height=int(DESIGN_H * SCALE),
            bg=BG,
            highlightthickness=0,
        )
        self.canvas.pack(padx=8, pady=6)

    def _draw_layout(self):
        c = self.canvas
        c.delete("all")

        c.create_text(sx(950), sy(28), text="Grinding Room / Bundle Operation Flow", font=("Arial", max(12, int(20 * SCALE)), "bold"))

        # Stations
        self._rect(80, 0, 650, 55, "Grinding Room", bold=True)
        self._rect(30, 95, 80, 490, "Vemag / Brick", vertical=True)
        self._rect(190, 95, 500, 135, "Blender Mixer Augers")
        self._rect(500, 95, 585, 135, "Grinder")
        self._rect(585, 0, 645, 135, "Product Dump", vertical=True)
        self._rect(125, 155, 285, 285, "Denester")
        self._rect(80, 402, 585, 455, "Multivac")
        self._rect(585, 185, 660, 455, "")
        self._rect(660, 185, 760, 455, "")

        self._rect(800, 560, 1035, 610, "Index Conveyor")
        self._rect(1035, 530, 1260, 620, "Shanklin")
        self._rect(1335, 530, 1605, 620, "Heat Tunnel")
        self._rect(1605, 560, 1675, 610, "Pack")
        self._rect(1300, 300, 1375, 350, "Pallet")
        self._rect(1375, 320, 1650, 350, "Tape, conveyor")

        # Paths
        # Regular tray path (red)
        self._path_line([(80, 300), (80, 420), (620, 420), (620, 195), (685, 195), (685, 275), (715, 275)], RED)

        # Regular box path (blue)
        self._path_line([(715, 275), (715, 420), (1300, 420), (1300, 325), (1375, 325)], BLUE)

        # Bundle tray path (orange)
        self._path_line([(715, 275), (715, 615), (1605, 615)], ORANGE)

        # Bundle box path (purple)
        self._path_line([(1605, 615), (1660, 615), (1660, 300), (1300, 300)], PURPLE)

        # Legend
        legend_x = 1420
        self._legend_box(legend_x, 120, YELLOW, "Grinding labor")
        self._legend_box(legend_x, 160, ORANGE, "Bundle labor / bundle trays")
        self._legend_box(legend_x, 200, TRAY, "Tray")
        self._legend_box(legend_x, 240, BLUE, "Regular boxes")
        self._legend_box(legend_x, 280, PURPLE, "Bundle boxes")

        # Normal labor
        self._emp("2", 85, 110, YELLOW, "2")
        self._emp("1", 505, 135, YELLOW, "1")
        self._emp("3", 315, 225, YELLOW, "3")
        self._emp("4", 640, 255, YELLOW, "4")
        self._emp("5", 700, 255, YELLOW, "5")
        self._emp("6", 705, 430, YELLOW, "6")
        self._emp("7", 760, 430, YELLOW, "7")
        self._emp("8", 1210, 410, YELLOW, "8")

        # Bundle moved workers (keep yellow per your request)
        self._emp("4", 720, 560, YELLOW, "4_orange")
        self._emp("5", 720, 610, YELLOW, "5_orange")
        self._emp("6", 760, 665, YELLOW, "6_orange")
        self._emp("7", 760, 250, YELLOW, "7_orange")
        self._note("Box Maker Costco", 835, 250, key="7_note")

        # Bundle-side workers
        self._emp("3", 1665, 560, BLUE, "3_blue")
        self._emp("2", 1665, 595, BLUE, "2_blue")
        self._emp("1", 1665, 630, BLUE, "1_blue")

        # Blue employee #5 in front of Shanklin
        self._emp("5", 995, 540, BLUE, "5_blue")

    def _path_line(self, pts, color):
        coords = []
        for x, y in pts:
            coords.extend([sx(x), sy(y)])
        self.canvas.create_line(*coords, fill=color, width=max(2, int(3 * SCALE)))

    def _legend_box(self, x, y, color, text):
        self.canvas.create_rectangle(sx(x), sy(y), sx(x + 70), sy(y + 26), fill=color, outline="")
        self.canvas.create_text(sx(x + 95), sy(y + 13), text=text, anchor="w", font=("Arial", max(9, int(11 * SCALE))))

    def _rect(self, x1, y1, x2, y2, label, vertical=False, bold=False):
        self.canvas.create_rectangle(sx(x1), sy(y1), sx(x2), sy(y2), outline=LINE, width=max(1, int(2 * SCALE)))
        if label:
            font = ("Arial", max(9, int((16 if bold else 11) * SCALE)), "bold" if bold else "normal")
            if vertical:
                self.canvas.create_text(sx((x1 + x2) / 2), sy((y1 + y2) / 2), text=label, angle=90, font=font)
            else:
                self.canvas.create_text(sx((x1 + x2) / 2), sy((y1 + y2) / 2), text=label, font=font)

    def _emp(self, label, x, y, color, key=None):
        key = key or label
        rect = self.canvas.create_rectangle(sx(x), sy(y), sx(x + 68), sy(y + 28), fill=color, outline="")
        text = self.canvas.create_text(sx(x + 34), sy(y + 14), text=label, font=("Arial", max(9, int(12 * SCALE))))
        self.employee_items[key] = rect
        self.employee_labels[key] = text

    def _note(self, text, x, y, key):
        self.employee_labels[key] = self.canvas.create_text(sx(x), sy(y), text=text, anchor="w", font=("Arial", max(8, int(10 * SCALE))))

    def _refresh_mode(self):
        bundle = self.mode.get() == "bundle"
        moved = ["4_orange", "5_orange", "6_orange", "7_orange", "7_note", "3_blue", "2_blue", "1_blue", "5_blue"]

        for key in moved:
            if key in self.employee_items:
                self.canvas.itemconfigure(self.employee_items[key], state="normal" if bundle else "hidden")
            if key in self.employee_labels:
                self.canvas.itemconfigure(self.employee_labels[key], state="normal" if (bundle and self.show_labels.get()) else "hidden")

        if bundle:
            for key in ["4", "5", "6", "7"]:
                self.canvas.itemconfigure(self.employee_items[key], state="hidden")
                self.canvas.itemconfigure(self.employee_labels[key], state="hidden")
        else:
            for key in ["4", "5", "6", "7"]:
                self.canvas.itemconfigure(self.employee_items[key], state="normal")
                self.canvas.itemconfigure(self.employee_labels[key], state="normal" if self.show_labels.get() else "hidden")

        for key in ["1", "2", "3", "8"]:
            self.canvas.itemconfigure(self.employee_labels[key], state="normal" if self.show_labels.get() else "hidden")

        self.status.config(
            text="Bundle mode: 4 and 5 move to first two yellow squares, 6 moves to the lower yellow square, 7 becomes Box Maker Costco."
            if bundle
            else "Normal mode: regular trays follow the red path and stop between 4 and 5, then become regular boxes."
        )

    def start(self):
        self.running = True

    def pause(self):
        self.running = False

    def reset(self):
        self.running = False
        self.elapsed_sim_sec = 0.0
        self.last_spawn_sec = 0.0
        self.completed_changeovers = 0
        self.changeover_active = False
        self.changeover_end_sec = 0.0
        self.tray_total = 0
        self.regular_case_total = 0
        self.bundle_case_total = 0
        self.regular_pack_buffer = 0
        self.bundle_pack_buffer = 0

        for item in list(self.tray_items) + list(self.case_items):
            self.canvas.delete(item["id"])
        self.tray_items.clear()
        self.case_items.clear()

        self._update_labels()
        self._refresh_mode()

    def _spawn_tray(self):
        size = max(6, int(10 * SCALE))
        x = sx(74)
        y = sy(300)
        item = self.canvas.create_rectangle(x, y, x + size, y + size, fill=TRAY, outline=TRAY)

        path = [
            (80, 420),
            (620, 420),
            (620, 195),
            (685, 195),
            (685, 275),
            (715, 275),
        ]
        self.tray_items.append({"id": item, "path": path, "idx": 0, "bundle": False})

    def _spawn_regular_case(self):
        size = max(8, int(12 * SCALE))
        x = sx(707)
        y = sy(268)
        item = self.canvas.create_rectangle(x, y, x + size, y + size, fill=BLUE, outline=BLUE)

        path = [
            (715, 420),
            (1300, 420),
            (1300, 325),
            (1375, 325),
        ]
        self.case_items.append({"id": item, "path": path, "idx": 0})

    def _spawn_bundle_case(self):
        size = max(8, int(12 * SCALE))
        x = sx(1600)
        y = sy(607)
        item = self.canvas.create_rectangle(x, y, x + size, y + size, fill=PURPLE, outline=PURPLE)

        path = [
            (1660, 615),
            (1660, 300),
            (1300, 300),
        ]
        self.case_items.append({"id": item, "path": path, "idx": 0})

    def _move_item_along_path(self, item_id, path_state, speed_px):
        coords = self.canvas.coords(item_id)
        x1, y1, x2, y2 = coords
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        if path_state["idx"] >= len(path_state["path"]):
            return True

        tx, ty = path_state["path"][path_state["idx"]]
        tx = sx(tx)
        ty = sy(ty)

        dx = tx - cx
        dy = ty - cy
        dist = math.hypot(dx, dy)

        if dist <= speed_px:
            self.canvas.move(item_id, dx, dy)
            path_state["idx"] += 1
        else:
            self.canvas.move(item_id, speed_px * dx / dist, speed_px * dy / dist)

        return path_state["idx"] >= len(path_state["path"])

    def _move_trays(self, dt_real):
        remove = []
        speed_px = 260 * SCALE * dt_real

        for tray in self.tray_items:
            done = self._move_item_along_path(tray["id"], tray, speed_px)
            if done:
                if self.mode.get() == "normal" and not tray["bundle"]:
                    remove.append(tray)
                    self.tray_total += 1
                    self.regular_pack_buffer += 1
                    if self.regular_pack_buffer >= 12:
                        self.regular_pack_buffer = 0
                        self.regular_case_total += 1
                        self._spawn_regular_case()
                else:
                    if not tray["bundle"]:
                        tray["bundle"] = True
                        tray["path"] = [(715, 615), (1605, 615)]
                        tray["idx"] = 0
                    else:
                        remove.append(tray)
                        self.tray_total += 1
                        self.bundle_pack_buffer += 1
                        if self.bundle_pack_buffer >= 12:
                            self.bundle_pack_buffer = 0
                            self.bundle_case_total += 1
                            self._spawn_bundle_case()

        for tray in remove:
            if tray in self.tray_items:
                self.canvas.delete(tray["id"])
                self.tray_items.remove(tray)

    def _move_cases(self, dt_real):
        remove = []
        speed_px = 190 * SCALE * dt_real

        for case in self.case_items:
            done = self._move_item_along_path(case["id"], case, speed_px)
            if done:
                remove.append(case)

        for case in remove:
            if case in self.case_items:
                self.canvas.delete(case["id"])
                self.case_items.remove(case)

    def _apply_changeovers(self):
        total_sim_sec = self.sim_minutes.get() * 60.0
        count = self.changeovers.get()
        if count <= 0:
            return

        interval = total_sim_sec / (count + 1)
        expected = 0
        for i in range(1, count + 1):
            if self.elapsed_sim_sec >= i * interval:
                expected = i

        if expected > self.completed_changeovers and not self.changeover_active:
            self.changeover_active = True
            self.completed_changeovers += 1
            self.changeover_end_sec = self.elapsed_sim_sec + 7 * 60
            self.status.config(text="Changeover active: 7 simulated minutes.")

        if self.changeover_active and self.elapsed_sim_sec >= self.changeover_end_sec:
            self.changeover_active = False
            self._refresh_mode()

    def _update_labels(self):
        self.lbl_tpm.config(text=f"{self.trays_per_min.get():.1f}")
        self.lbl_scale.config(text=f"{self.time_scale.get():.0f}x")
        self.kpis["Minutes Simulated"].config(text=f"{self.elapsed_sim_sec / 60:.1f}")
        self.kpis["Trays Produced"].config(text=str(self.tray_total))
        self.kpis["Regular Cases"].config(text=str(self.regular_case_total))
        self.kpis["Bundle Cases"].config(text=str(self.bundle_case_total))
        self.kpis["Completed Changeovers"].config(text=str(self.completed_changeovers))
        self.kpis["Backlog"].config(text=str(len(self.tray_items)))

    def _tick(self):
        dt_real = 0.05

        if self.running:
            total_limit = self.sim_minutes.get() * 60.0
            if self.elapsed_sim_sec < total_limit:
                self.elapsed_sim_sec += dt_real * self.time_scale.get()
                self._apply_changeovers()

                if not self.changeover_active:
                    interval = 60.0 / max(1.0, self.trays_per_min.get())
                    if self.elapsed_sim_sec - self.last_spawn_sec >= interval:
                        self._spawn_tray()
                        self.last_spawn_sec = self.elapsed_sim_sec

                self._move_trays(dt_real)
                self._move_cases(dt_real)
            else:
                self.running = False
                self.status.config(text="Simulation complete.")

        self._update_labels()
        self.root.after(50, self._tick)


def main():
    root = tk.Tk()
    app = SimApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
