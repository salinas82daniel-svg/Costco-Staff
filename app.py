import json
import math
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog

BG = "#f4f4f4"
LINE = "#222222"
YELLOW = "#ffe94d"
BLUE = "#2459ff"
TRAY = "#111111"
PURPLE = "#8e44ad"
RED = "#cc2f2f"
ORANGE = "#f7b52c"

WINDOW_W = 1500
WINDOW_H = 920
DESIGN_W = 1900
DESIGN_H = 820
SCALE = min((WINDOW_W - 40) / DESIGN_W, (WINDOW_H - 180) / DESIGN_H)


def sx(x): return x * SCALE
def sy(y): return y * SCALE
def ux(x): return x / SCALE
def uy(y): return y / SCALE


DEFAULT_LAYOUT = {
    "employees": [
        {"key": "2", "label": "2", "x": 85, "y": 110, "color": YELLOW},
        {"key": "1", "label": "1", "x": 505, "y": 135, "color": YELLOW},
        {"key": "3", "label": "3", "x": 315, "y": 225, "color": YELLOW},
        {"key": "4", "label": "4", "x": 640, "y": 255, "color": YELLOW},
        {"key": "5", "label": "5", "x": 700, "y": 255, "color": YELLOW},
        {"key": "6", "label": "6", "x": 705, "y": 430, "color": YELLOW},
        {"key": "7", "label": "7", "x": 760, "y": 430, "color": YELLOW},
        {"key": "8", "label": "8", "x": 1210, "y": 410, "color": YELLOW},

        {"key": "4_orange", "label": "4", "x": 720, "y": 560, "color": YELLOW},
        {"key": "5_orange", "label": "5", "x": 720, "y": 585, "color": YELLOW},
        {"key": "6_orange", "label": "6", "x": 760, "y": 665, "color": YELLOW},
        {"key": "7_orange", "label": "7", "x": 760, "y": 250, "color": YELLOW},

        {"key": "3_blue", "label": "3", "x": 1665, "y": 560, "color": BLUE},
        {"key": "2_blue", "label": "2", "x": 1665, "y": 595, "color": BLUE},
        {"key": "1_blue", "label": "1", "x": 1635, "y": 630, "color": BLUE},
        {"key": "5_blue", "label": "5", "x": 1085, "y": 545, "color": BLUE},
        {"key": "4_blue", "label": "4", "x": 1495, "y": 455, "color": BLUE},
    ],
    "notes": [
        {"key": "7_note", "text": "Box Maker Costco", "x": 835, "y": 250},
    ],
}


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Layout Editor + Simulator")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.configure(bg=BG)

        self.mode = tk.StringVar(value="edit")      # edit / sim
        self.flow = tk.StringVar(value="normal")    # normal / bundle
        self.show_labels = tk.BooleanVar(value=True)

        self.trays_per_min = tk.DoubleVar(value=32.0)
        self.changeovers = tk.IntVar(value=0)
        self.sim_minutes = tk.DoubleVar(value=60.0)
        self.time_scale = tk.DoubleVar(value=120.0)

        self.layout = json.loads(json.dumps(DEFAULT_LAYOUT))
        self.drag_item = None
        self.drag_offset = (0, 0)
        self.item_map = {}

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

        self.trays = []
        self.cases = []

        self._ui()
        self._draw()
        self._update_kpis()
        self._tick()

    def _ui(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=4, pady=4)

        ttk.Label(top, text="Mode").pack(side="left")
        ttk.Radiobutton(top, text="Edit", variable=self.mode, value="edit").pack(side="left")
        ttk.Radiobutton(top, text="Sim", variable=self.mode, value="sim").pack(side="left", padx=(0, 8))

        ttk.Radiobutton(top, text="Normal Pack", variable=self.flow, value="normal", command=self._draw).pack(side="left")
        ttk.Radiobutton(top, text="Bundle Mode", variable=self.flow, value="bundle", command=self._draw).pack(side="left", padx=(0, 8))

        ttk.Label(top, text="Trays/min").pack(side="left")
        ttk.Scale(top, from_=10, to=90, variable=self.trays_per_min, orient="horizontal", length=170).pack(side="left")
        self.lbl_tpm = ttk.Label(top, text="32.0")
        self.lbl_tpm.pack(side="left", padx=(6, 10))

        ttk.Label(top, text="Changeovers").pack(side="left")
        ttk.Spinbox(top, from_=0, to=20, width=5, textvariable=self.changeovers).pack(side="left", padx=(2, 10))

        ttk.Label(top, text="Sim minutes").pack(side="left")
        ttk.Spinbox(top, from_=1, to=480, width=6, textvariable=self.sim_minutes).pack(side="left", padx=(2, 10))

        ttk.Label(top, text="Speed-up").pack(side="left")
        ttk.Scale(top, from_=10, to=300, variable=self.time_scale, orient="horizontal", length=120).pack(side="left")
        self.lbl_speed = ttk.Label(top, text="120x")
        self.lbl_speed.pack(side="left", padx=(6, 10))

        controls = tk.Frame(self.root, bg=BG)
        controls.pack(fill="x", padx=4, pady=(0, 4))

        ttk.Button(controls, text="Add Emp", command=self.add_emp).pack(side="left")
        ttk.Button(controls, text="Add Note", command=self.add_note).pack(side="left", padx=4)
        ttk.Button(controls, text="Save", command=self.save).pack(side="left")
        ttk.Button(controls, text="Load", command=self.load).pack(side="left", padx=4)

        ttk.Button(controls, text="Start", command=self.start).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Pause", command=self.pause).pack(side="left", padx=4)
        ttk.Button(controls, text="Reset", command=self.reset).pack(side="left", padx=4)

        ttk.Checkbutton(controls, text="Show Labels", variable=self.show_labels, command=self._draw).pack(side="left", padx=8)

        self.status = ttk.Label(controls, text="Edit mode: drag employees/notes. Double-click to rename.")
        self.status.pack(side="left", padx=10)

        kpi_row = tk.Frame(self.root, bg=BG)
        kpi_row.pack(fill="x", padx=4, pady=(0, 4))

        self.kpis = {}
        for label in ["Minutes Simulated", "Trays Produced", "Regular Cases", "Bundle Cases", "Completed Changeovers", "Backlog"]:
            box = tk.Frame(kpi_row, bg="white", highlightbackground="#bbbbbb", highlightthickness=1)
            box.pack(side="left", padx=4)
            tk.Label(box, text=label, font=("Arial", 10, "bold"), bg="white").pack(padx=18, pady=(8, 2))
            val = tk.Label(box, text="0", font=("Arial", 12), bg="white")
            val.pack(padx=18, pady=(0, 8))
            self.kpis[label] = val

        self.canvas = tk.Canvas(self.root, width=int(DESIGN_W * SCALE), height=int(DESIGN_H * SCALE), bg=BG, highlightthickness=0)
        self.canvas.pack(padx=4, pady=4)

        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag_item", None))
        self.canvas.bind("<Double-Button-1>", self.rename)
        self.canvas.bind("<Button-3>", self.delete)

    def _path_line(self, pts, color):
        coords = []
        for x, y in pts:
            coords += [sx(x), sy(y)]
        self.canvas.create_line(*coords, fill=color, width=3)

    def _rect(self, x1, y1, x2, y2, label="", vertical=False, bold=False):
        self.canvas.create_rectangle(sx(x1), sy(y1), sx(x2), sy(y2), outline=LINE, width=2)
        if label:
            font = ("Arial", max(9, int((16 if bold else 11) * SCALE)), "bold" if bold else "normal")
            if vertical:
                self.canvas.create_text(sx((x1 + x2) / 2), sy((y1 + y2) / 2), text=label, angle=90, font=font)
            else:
                self.canvas.create_text(sx((x1 + x2) / 2), sy((y1 + y2) / 2), text=label, font=font)

    def _legend_box(self, x, y, color, text):
        self.canvas.create_rectangle(sx(x), sy(y), sx(x + 70), sy(y + 26), fill=color, outline="")
        self.canvas.create_text(sx(x + 95), sy(y + 13), text=text, anchor="w")

    def _draw(self):
        c = self.canvas
        c.delete("all")
        self.item_map.clear()

        # Title
        c.create_text(sx(950), sy(28), text="Grinding Room / Bundle Operation Flow", font=("Arial", max(12, int(20 * SCALE)), "bold"))

        # Machine boxes
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
        self._path_line([(80, 300), (80, 420), (620, 420), (620, 195), (685, 195), (685, 275), (715, 275)], RED)
        self._path_line([(715, 275), (715, 420), (1300, 420), (1300, 325), (1375, 325)], BLUE)
        self._path_line([(715, 275), (715, 615), (1605, 615)], ORANGE)
        self._path_line([(1605, 615), (1660, 615), (1660, 300), (1300, 300)], PURPLE)

        # Legend
        legend_x = 1420
        self._legend_box(legend_x, 120, YELLOW, "Grinding labor")
        self._legend_box(legend_x, 160, ORANGE, "Bundle labor / bundle trays")
        self._legend_box(legend_x, 200, TRAY, "Tray")
        self._legend_box(legend_x, 240, BLUE, "Regular boxes")
        self._legend_box(legend_x, 280, PURPLE, "Bundle boxes")

        show_bundle = self.flow.get() == "bundle"
        for e in self.layout["employees"]:
            key = e["key"]
            if not show_bundle and ("_orange" in key or "_blue" in key):
                continue
            if show_bundle and key in {"4", "5", "6", "7"}:
                continue
            self.draw_emp(e)

        for n in self.layout["notes"]:
            if not show_bundle and n["key"] == "7_note":
                continue
            self.draw_note(n)

        if self.mode.get() == "edit":
            self.status.config(text="Edit mode: drag employees/notes. Double-click to rename.")
        else:
            if show_bundle:
                self.status.config(text="Bundle mode simulation.")
            else:
                self.status.config(text="Normal mode simulation.")

    def draw_emp(self, e):
        x, y = e["x"], e["y"]
        r = self.canvas.create_rectangle(sx(x), sy(y), sx(x + 60), sy(y + 30), fill=e["color"], outline="")
        t = self.canvas.create_text(sx(x + 30), sy(y + 15), text=e["label"])
        self.item_map[r] = ("emp", e)
        self.item_map[t] = ("emp", e)
        if not self.show_labels.get():
            self.canvas.itemconfigure(t, state="hidden")

    def draw_note(self, n):
        t = self.canvas.create_text(sx(n["x"]), sy(n["y"]), text=n["text"], anchor="w")
        self.item_map[t] = ("note", n)

    def click(self, e):
        if self.mode.get() != "edit":
            return
        i = self.canvas.find_closest(e.x, e.y)
        if not i:
            return
        item = i[0]
        if item not in self.item_map:
            return
        kind, obj = self.item_map[item]
        self.drag_item = (kind, obj)
        self.drag_offset = (ux(e.x) - obj["x"], uy(e.y) - obj["y"])

    def drag(self, e):
        if self.mode.get() != "edit" or not self.drag_item:
            return
        kind, obj = self.drag_item
        obj["x"] = ux(e.x) - self.drag_offset[0]
        obj["y"] = uy(e.y) - self.drag_offset[1]
        self._draw()

    def rename(self, e):
        if self.mode.get() != "edit":
            return
        i = self.canvas.find_closest(e.x, e.y)
        if not i:
            return
        item = i[0]
        if item not in self.item_map:
            return
        kind, obj = self.item_map[item]
        val = simpledialog.askstring("Edit", "Text", initialvalue=obj["label"] if kind == "emp" else obj["text"])
        if val:
            if kind == "emp":
                obj["label"] = val
            else:
                obj["text"] = val
        self._draw()

    def delete(self, e):
        if self.mode.get() != "edit":
            return
        i = self.canvas.find_closest(e.x, e.y)
        if not i:
            return
        item = i[0]
        if item not in self.item_map:
            return
        kind, obj = self.item_map[item]
        if kind == "emp":
            self.layout["employees"].remove(obj)
        else:
            self.layout["notes"].remove(obj)
        self._draw()

    def add_emp(self):
        key = f"emp_{len(self.layout['employees']) + 1}"
        self.layout["employees"].append({"key": key, "label": "E", "x": 900, "y": 400, "color": YELLOW})
        self._draw()

    def add_note(self):
        key = f"note_{len(self.layout['notes']) + 1}"
        self.layout["notes"].append({"key": key, "text": "Note", "x": 900, "y": 200})
        self._draw()

    def save(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if f:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(self.layout, fh, indent=2)

    def load(self):
        f = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if f:
            with open(f, "r", encoding="utf-8") as fh:
                self.layout = json.load(fh)
            self._draw()

    def start(self):
        self.mode.set("sim")
        self.running = True
        self._draw()

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
        for item in list(self.trays) + list(self.cases):
            self.canvas.delete(item["id"])
        self.trays.clear()
        self.cases.clear()
        self._draw()
        self._update_kpis()

    def spawn_tray(self):
        size = max(6, int(10 * SCALE))
        r = self.canvas.create_rectangle(sx(70), sy(300), sx(70) + size, sy(300) + size, fill=TRAY, outline=TRAY)
        self.trays.append({
            "id": r,
            "path": [(80, 420), (620, 420), (620, 195), (685, 195), (685, 275), (715, 275)],
            "i": 0,
            "bundle": False
        })

    def spawn_regular_case(self):
        size = max(8, int(12 * SCALE))
        r = self.canvas.create_rectangle(sx(707), sy(268), sx(707) + size, sy(268) + size, fill=BLUE, outline=BLUE)
        self.cases.append({
            "id": r,
            "path": [(715, 420), (1300, 420), (1300, 325), (1375, 325)],
            "i": 0
        })

    def spawn_bundle_case(self):
        size = max(8, int(12 * SCALE))
        r = self.canvas.create_rectangle(sx(1600), sy(607), sx(1600) + size, sy(607) + size, fill=PURPLE, outline=PURPLE)
        self.cases.append({
            "id": r,
            "path": [(1660, 615), (1660, 300), (1300, 300)],
            "i": 0
        })

    def move(self, item, speed=2.0):
        coords = self.canvas.coords(item["id"])
        cx = (coords[0] + coords[2]) / 2
        cy = (coords[1] + coords[3]) / 2
        if item["i"] >= len(item["path"]):
            return True
        tx, ty = item["path"][item["i"]]
        tx, ty = sx(tx), sy(ty)
        dx, dy = tx - cx, ty - cy
        d = math.hypot(dx, dy)
        if d < speed:
            self.canvas.move(item["id"], dx, dy)
            item["i"] += 1
        else:
            self.canvas.move(item["id"], dx / d * speed, dy / d * speed)
        return item["i"] >= len(item["path"])

    def _update_kpis(self):
        self.lbl_tpm.config(text=f"{self.trays_per_min.get():.1f}")
        self.lbl_speed.config(text=f"{int(self.time_scale.get())}x")
        self.kpis["Minutes Simulated"].config(text=f"{self.elapsed_sim_sec / 60:.1f}")
        self.kpis["Trays Produced"].config(text=str(self.tray_total))
        self.kpis["Regular Cases"].config(text=str(self.regular_case_total))
        self.kpis["Bundle Cases"].config(text=str(self.bundle_case_total))
        self.kpis["Completed Changeovers"].config(text=str(self.completed_changeovers))
        self.kpis["Backlog"].config(text=str(len(self.trays)))

    def _tick(self):
        dt_real = 0.05
        if self.running and self.mode.get() == "sim":
            total_limit = self.sim_minutes.get() * 60.0
            if self.elapsed_sim_sec < total_limit:
                self.elapsed_sim_sec += dt_real * self.time_scale.get()

                interval = 60.0 / max(1.0, self.trays_per_min.get())
                if self.elapsed_sim_sec - self.last_spawn_sec >= interval:
                    self.spawn_tray()
                    self.last_spawn_sec = self.elapsed_sim_sec

                remove = []
                for t in self.trays:
                    if self.move(t, 2.6):
                        if self.flow.get() == "normal" and not t["bundle"]:
                            remove.append(t)
                            self.tray_total += 1
                            self.regular_pack_buffer += 1
                            if self.regular_pack_buffer >= 12:
                                self.regular_pack_buffer = 0
                                self.regular_case_total += 1
                                self.spawn_regular_case()
                        else:
                            if not t["bundle"]:
                                t["bundle"] = True
                                t["path"] = [(715, 615), (1605, 615)]
                                t["i"] = 0
                            else:
                                remove.append(t)
                                self.tray_total += 1
                                self.bundle_pack_buffer += 1
                                if self.bundle_pack_buffer >= 12:
                                    self.bundle_pack_buffer = 0
                                    self.bundle_case_total += 1
                                    self.spawn_bundle_case()

                for t in remove:
                    self.canvas.delete(t["id"])
                    self.trays.remove(t)

                remove_cases = []
                for c in self.cases:
                    if self.move(c, 2.0):
                        remove_cases.append(c)
                for c in remove_cases:
                    self.canvas.delete(c["id"])
                    self.cases.remove(c)
            else:
                self.running = False
                self.status.config(text="Simulation complete.")

        self._update_kpis()
        self.root.after(50, self._tick)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
