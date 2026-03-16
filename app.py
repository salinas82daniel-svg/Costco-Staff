import tkinter as tk
from tkinter import ttk

BG = "#f4f4f4"
LINE = "#222222"
YELLOW = "#ffe94d"
BLUE = "#2459ff"
ORANGE = "#f7b52c"
TRAY = "#111111"
PURPLE = "#8e44ad"
RED = "#cc2f2f"

class SimApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Grinding / Bundle Flow Simulator v5")
        self.root.geometry("1500x920")
        self.root.configure(bg=BG)

        self.mode = tk.StringVar(value="normal")
        self.trays_per_min = tk.DoubleVar(value=32.0)
        self.changeovers = tk.IntVar(value=0)
        self.sim_minutes = tk.DoubleVar(value=60.0)
        self.time_scale = tk.DoubleVar(value=120.0)
        self.show_labels = tk.BooleanVar(value=True)
        self.fit_to_window = tk.BooleanVar(value=False)

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

        self.design_w = 1900
        self.design_h = 820
        self.scale_factor = 1.0

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
        ttk.Scale(top, from_=10, to=90, variable=self.trays_per_min, orient="horizontal", length=180, command=lambda _=None: self._update_labels()).pack(side="left", padx=4)
        self.lbl_tpm = ttk.Label(top, text="")
        self.lbl_tpm.pack(side="left", padx=(0, 10))

        ttk.Label(top, text="Changeovers").pack(side="left")
        ttk.Spinbox(top, from_=0, to=20, width=5, textvariable=self.changeovers, command=self._update_labels).pack(side="left", padx=4)

        ttk.Label(top, text="Sim minutes").pack(side="left", padx=(8, 0))
        ttk.Spinbox(top, from_=10, to=240, width=6, textvariable=self.sim_minutes, command=self._update_labels).pack(side="left", padx=4)

        ttk.Label(top, text="Speed-up").pack(side="left", padx=(8, 0))
        ttk.Scale(top, from_=30, to=300, variable=self.time_scale, orient="horizontal", length=120, command=lambda _=None: self._update_labels()).pack(side="left", padx=4)
        self.lbl_scale = ttk.Label(top, text="")
        self.lbl_scale.pack(side="left", padx=(0, 8))

        controls = tk.Frame(self.root, bg=BG)
        controls.pack(fill="x", padx=8, pady=(0, 6))

        ttk.Button(controls, text="Start", command=self.start).pack(side="left")
        ttk.Button(controls, text="Pause", command=self.pause).pack(side="left", padx=4)
        ttk.Button(controls, text="Reset", command=self.reset).pack(side="left", padx=4)
        ttk.Checkbutton(controls, text="Show Labels", variable=self.show_labels, command=self._refresh_mode).pack(side="left", padx=6)
        ttk.Checkbutton(controls, text="Fit to window", variable=self.fit_to_window, command=self._redraw_scaled).pack(side="left", padx=6)

        self.status = ttk.Label(controls, text="Ready. Normal: red trays become blue cases. Bundle: orange trays become purple boxes.")
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

        canvas_wrap = tk.Frame(self.root, bg=BG)
        canvas_wrap.pack(fill="both", expand=True, padx=8, pady=6)

        self.canvas = tk.Canvas(canvas_wrap, width=1420, height=720, bg=BG, highlightthickness=0, scrollregion=(0, 0, self.design_w, self.design_h))
        self.hbar = ttk.Scrollbar(canvas_wrap, orient="horizontal", command=self.canvas.xview)
        self.vbar = ttk.Scrollbar(canvas_wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")
        canvas_wrap.rowconfigure(0, weight=1)
        canvas_wrap.columnconfigure(0, weight=1)

        self.root.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        if self.fit_to_window.get():
            self._redraw_scaled()

    def sx(self, x): return x * self.scale_factor
    def sy(self, y): return y * self.scale_factor

    def _redraw_scaled(self):
        if self.fit_to_window.get():
            w = max(1000, self.canvas.winfo_width())
            h = max(500, self.canvas.winfo_height())
            self.scale_factor = min(w / self.design_w, h / self.design_h)
            self.canvas.configure(scrollregion=(0, 0, self.design_w * self.scale_factor, self.design_h * self.scale_factor))
            self.hbar.grid_remove()
            self.vbar.grid_remove()
        else:
            self.scale_factor = 1.0
            self.canvas.configure(scrollregion=(0, 0, self.design_w, self.design_h))
            self.hbar.grid()
            self.vbar.grid()
        self._draw_layout()
        self._refresh_mode()

    def _draw_layout(self):
        c = self.canvas
        c.delete("all")
        c.create_text(self.sx(950), self.sy(28), text="Grinding Room / Bundle Operation Flow", font=("Arial", max(12, int(20 * self.scale_factor)), "bold"))

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
        self.canvas.create_line(self.sx(80), self.sy(300), self.sx(80), self.sy(420), fill=RED, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(80), self.sy(420), self.sx(620), self.sy(420), fill=RED, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(620), self.sy(420), self.sx(620), self.sy(195), fill=RED, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(620), self.sy(195), self.sx(685), self.sy(195), fill=RED, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(685), self.sy(195), self.sx(685), self.sy(275), fill=RED, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(685), self.sy(275), self.sx(715), self.sy(275), fill=RED, width=max(2, int(3 * self.scale_factor)))

        self.canvas.create_line(self.sx(715), self.sy(275), self.sx(715), self.sy(420), fill=BLUE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(715), self.sy(420), self.sx(1300), self.sy(420), fill=BLUE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(1300), self.sy(420), self.sx(1300), self.sy(325), fill=BLUE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(1300), self.sy(325), self.sx(1375), self.sy(325), fill=BLUE, width=max(2, int(3 * self.scale_factor)))

        self.canvas.create_line(self.sx(715), self.sy(275), self.sx(715), self.sy(615), fill=ORANGE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(715), self.sy(615), self.sx(1605), self.sy(615), fill=ORANGE, width=max(2, int(3 * self.scale_factor)))

        self.canvas.create_line(self.sx(1605), self.sy(615), self.sx(1660), self.sy(615), fill=PURPLE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(1660), self.sy(615), self.sx(1660), self.sy(300), fill=PURPLE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(1660), self.sy(300), self.sx(1300), self.sy(300), fill=PURPLE, width=max(2, int(3 * self.scale_factor)))

        legend_x = 1420
        self._legend_box(legend_x, 120, YELLOW, "Grinding labor")
        self._legend_box(legend_x, 160, ORANGE, "Bundle labor / bundle trays")
        self._legend_box(legend_x, 200, TRAY, "Tray")
        self._legend_box(legend_x, 240, BLUE, "Regular boxes")
        self._legend_box(legend_x, 280, PURPLE, "Bundle boxes")

        self._emp("2", 85, 110, YELLOW)
        self._emp("1", 505, 135, YELLOW)
        self._emp("3", 315, 225, YELLOW)
        self._emp("4", 640, 255, YELLOW, "4")
        self._emp("5", 700, 255, YELLOW, "5")
        self._emp("6", 705, 430, YELLOW, "6")
        self._emp("7", 760, 430, YELLOW, "7")
        self._emp("8", 1210, 410, YELLOW, "8")

        self._emp("4", 720, 560, ORANGE, "4_orange")
        self._emp("5", 720, 610, ORANGE, "5_orange")
        self._emp("6", 760, 665, ORANGE, "6_orange")
        self._emp("7", 760, 250, ORANGE, "7_orange")
        self._note("Box Maker Costco", 835, 250, key="7_note")

        self._emp("3", 1665, 560, BLUE, "3_blue")
        self._emp("2", 1665, 595, BLUE, "2_blue")
        self._emp("1", 1665, 630, BLUE, "1_blue")
        self._emp("5", 1545, 320, BLUE, "5_blue")

    def _legend_box(self, x, y, color, text):
        self.canvas.create_rectangle(self.sx(x), self.sy(y), self.sx(x + 70), self.sy(y + 26), fill=color, outline="")
        self.canvas.create_text(self.sx(x + 95), self.sy(y + 13), text=text, anchor="w", font=("Arial", max(9, int(11 * self.scale_factor))))

    def _rect(self, x1, y1, x2, y2, label, vertical=False, bold=False):
        self.canvas.create_rectangle(self.sx(x1), self.sy(y1), self.sx(x2), self.sy(y2), outline=LINE, width=max(1, int(2 * self.scale_factor)))
        if label:
            font = ("Arial", max(9, int((16 if bold else 11) * self.scale_factor)), "bold" if bold else "normal")
            if vertical:
                self.canvas.create_text(self.sx((x1 + x2) / 2), self.sy((y1 + y2) / 2), text=label, angle=90, font=font)
            else:
                self.canvas.create_text(self.sx((x1 + x2) / 2), self.sy((y1 + y2) / 2), text=label, font=font)

    def _emp(self, label, x, y, color, key):
        rect = self.canvas.create_rectangle(self.sx(x), self.sy(y), self.sx(x + 68), self.sy(y + 28), fill=color, outline="")
        text = self.canvas.create_text(self.sx(x + 34), self.sy(y + 14), text=label, font=("Arial", max(9, int(12 * self.scale_factor))))
        self.employee_items[key] = rect
        self.employee_labels[key] = text

    def _note(self, text, x, y, key):
        self.employee_labels[key] = self.canvas.create_text(self.sx(x), self.sy(y), text=text, anchor="w", font=("Arial", max(8, int(10 * self.scale_factor))))

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
            text="Bundle mode: 4 and 5 move to first two orange squares, 6 moves to the lower orange square, 7 becomes Box Maker Costco."
            if bundle else
            "Normal mode: regular trays end between 4 and 5, then become regular boxes."
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
        item = self.canvas.create_rectangle(self.sx(74), self.sy(300), self.sx(86), self.sy(312), fill=TRAY, outline=TRAY)
        self.tray_items.append({"id": item, "stage": "drop_vemag"})

    def _spawn_regular_case(self):
        item = self.canvas.create_rectangle(self.sx(707), self.sy(268), self.sx(723), self.sy(284), fill=BLUE, outline=BLUE)
        self.case_items.append({"id": item, "stage": "regular_down"})

    def _spawn_bundle_case(self):
        item = self.canvas.create_rectangle(self.sx(1600), self.sy(607), self.sx(1616), self.sy(623), fill=PURPLE, outline=PURPLE)
        self.case_items.append({"id": item, "stage": "bundle_right"})

    def _move_trays(self, dt_real):
        remove = []
        speed_px = 260 * self.scale_factor * dt_real
        for tray in self.tray_items:
            item = tray["id"]
            x1, y1, x2, y2 = self.canvas.coords(item)

            if tray["stage"] == "drop_vemag":
                if y2 < self.sy(420):
                    self.canvas.move(item, 0, speed_px)
                else:
                    tray["stage"] = "horizontal"
            elif tray["stage"] == "horizontal":
                if x2 < self.sx(620):
                    self.canvas.move(item, speed_px, 0)
                else:
                    tray["stage"] = "up_to_pack"
            elif tray["stage"] == "up_to_pack":
                if y1 > self.sy(195):
                    self.canvas.move(item, 0, -speed_px)
                else:
                    tray["stage"] = "down_loop"
            elif tray["stage"] == "down_loop":
                if y2 < self.sy(275):
                    self.canvas.move(item, 0, speed_px)
                else:
                    tray["stage"] = "decision_point"
            elif tray["stage"] == "decision_point":
                if x2 < self.sx(715):
                    self.canvas.move(item, speed_px, 0)
                else:
                    if self.mode.get() == "normal":
                        remove.append(tray)
                        self.tray_total += 1
                        self.regular_pack_buffer += 1
                        if self.regular_pack_buffer >= 12:
                            self.regular_pack_buffer = 0
                            self.regular_case_total += 1
                            self._spawn_regular_case()
                    else:
                        tray["stage"] = "down_bundle"
            elif tray["stage"] == "down_bundle":
                if y2 < self.sy(615):
                    self.canvas.move(item, 0, speed_px)
                else:
                    tray["stage"] = "bundle_across"
            elif tray["stage"] == "bundle_across":
                if x2 < self.sx(1605):
                    self.canvas.move(item, speed_px, 0)
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
        speed_px = 190 * self.scale_factor * dt_real
        for case in self.case_items:
            item = case["id"]
            x1, y1, x2, y2 = self.canvas.coords(item)
            if case["stage"] == "regular_down":
                if y2 < self.sy(420):
                    self.canvas.move(item, 0, speed_px)
                else:
                    case["stage"] = "regular_right"
            elif case["stage"] == "regular_right":
                if x2 < self.sx(1300):
                    self.canvas.move(item, speed_px, 0)
                else:
                    case["stage"] = "regular_up"
            elif case["stage"] == "regular_up":
                if y1 > self.sy(325):
                    self.canvas.move(item, 0, -speed_px)
                else:
                    case["stage"] = "regular_pallet"
            elif case["stage"] == "regular_pallet":
                if x2 < self.sx(1375):
                    self.canvas.move(item, speed_px, 0)
                else:
                    remove.append(case)
            elif case["stage"] == "bundle_right":
                if x2 < self.sx(1660):
                    self.canvas.move(item, speed_px, 0)
                else:
                    case["stage"] = "bundle_up"
            elif case["stage"] == "bundle_up":
                if y1 > self.sy(300):
                    self.canvas.move(item, 0, -speed_px)
                else:
                    case["stage"] = "bundle_left"
            elif case["stage"] == "bundle_left":
                if x1 > self.sx(1300):
                    self.canvas.move(item, -speed_px, 0)
                else:
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
