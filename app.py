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
        self.root.title("Grinding / Bundle Flow Simulator v4")
        self.root.geometry("1450x900")
        self.root.configure(bg=BG)

        self.mode = tk.StringVar(value="normal")
        self.trays_per_min = tk.DoubleVar(value=32.0)
        self.bundle_trays_per_min = tk.DoubleVar(value=40.0)
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

        ttk.Label(top, text="Grinding trays/min").pack(side="left")
        ttk.Scale(top, from_=10, to=90, variable=self.trays_per_min, orient="horizontal", length=160, command=lambda _=None: self._update_labels()).pack(side="left", padx=4)
        self.lbl_tpm = ttk.Label(top, text="")
        self.lbl_tpm.pack(side="left", padx=(0, 10))

        ttk.Label(top, text="Bundle trays/min").pack(side="left")
        ttk.Scale(top, from_=10, to=90, variable=self.bundle_trays_per_min, orient="horizontal", length=160, command=lambda _=None: self._update_labels()).pack(side="left", padx=4)
        self.lbl_btpm = ttk.Label(top, text="")
        self.lbl_btpm.pack(side="left", padx=(0, 10))

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

        self.status = ttk.Label(controls, text="Ready. Red = regular tray path | Blue = regular box path | Orange = bundle tray path | Purple = bundle box path.")
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

        self.canvas = tk.Canvas(canvas_wrap, width=1380, height=720, bg=BG, highlightthickness=0, scrollregion=(0, 0, self.design_w, self.design_h))
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

    def sx(self, x):
        return x * self.scale_factor

    def sy(self, y):
        return y * self.scale_factor

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
        c.create_text(self.sx(950), self.sy(28), text="Grinding Room / Bundle Operation Flow", font=("Arial", int(20 * self.scale_factor), "bold"))

        # Main stations
        self._rect(120, 50, 760, 110, "Grinding Room", bold=True)
        self._rect(50, 140, 120, 500, "Vemag / Brick", vertical=True)
        self._rect(265, 165, 760, 210, "Blender Mixer Augers")
        self._rect(760, 165, 865, 210, "Grinder")
        self._rect(865, 50, 945, 210, "Product Dump", vertical=True)
        self._rect(190, 260, 355, 380, "Denester")
        self._rect(120, 430, 760, 485, "Multivac")
        self._rect(760, 285, 900, 485, "")
        self._rect(900, 285, 1010, 485, "")

        # Bundle stations
        self._rect(920, 575, 1145, 620, "Index Conveyor")
        self._rect(1145, 555, 1360, 645, "Shanklin")
        self._rect(1450, 555, 1735, 645, "Heat Tunnel")
        self._rect(1735, 575, 1798, 620, "Pack")
        self._rect(1450, 350, 1525, 405, "Pallet")
        self._rect(1525, 370, 1760, 405, "Tape, conveyor")

        # Paths
        # Regular trays (red): Vemag down -> horizontal -> up -> loop -> across to 5
        self.canvas.create_line(self.sx(120), self.sy(310), self.sx(120), self.sy(455), fill=RED, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(120), self.sy(455), self.sx(800), self.sy(455), fill=RED, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(800), self.sy(455), self.sx(800), self.sy(295), fill=RED, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(800), self.sy(295), self.sx(885), self.sy(295), fill=RED, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(885), self.sy(295), self.sx(885), self.sy(395), fill=RED, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(885), self.sy(395), self.sx(980), self.sy(395), fill=RED, width=max(2, int(3 * self.scale_factor)))

        # Regular cases (blue): from 5 area to 8 then tape/pallet
        self.canvas.create_line(self.sx(980), self.sy(395), self.sx(980), self.sy(470), fill=BLUE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(980), self.sy(470), self.sx(1180), self.sy(470), fill=BLUE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(1180), self.sy(470), self.sx(1450), self.sy(470), fill=BLUE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(1450), self.sy(470), self.sx(1450), self.sy(388), fill=BLUE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(1450), self.sy(388), self.sx(1525), self.sy(388), fill=BLUE, width=max(2, int(3 * self.scale_factor)))

        # Bundle trays (orange): split down to index then across to pack
        self.canvas.create_line(self.sx(885), self.sy(395), self.sx(885), self.sy(620), fill=ORANGE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(885), self.sy(620), self.sx(1735), self.sy(620), fill=ORANGE, width=max(2, int(3 * self.scale_factor)))

        # Bundle boxes (purple): pack up and left to pallet/tape
        self.canvas.create_line(self.sx(1735), self.sy(620), self.sx(1760), self.sy(620), fill=PURPLE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(1760), self.sy(620), self.sx(1760), self.sy(350), fill=PURPLE, width=max(2, int(3 * self.scale_factor)))
        self.canvas.create_line(self.sx(1760), self.sy(350), self.sx(1450), self.sy(350), fill=PURPLE, width=max(2, int(3 * self.scale_factor)))

        # Legend
        legend_x = 1310
        self._legend_box(legend_x, 150, YELLOW, "Grinding labor")
        self._legend_box(legend_x, 190, BLUE, "Regular box path / dedicated bundle labor")
        self._legend_box(legend_x, 230, ORANGE, "Bundle tray path / pulled labor")
        self._legend_box(legend_x, 270, TRAY, "Tray")
        self._legend_box(legend_x, 310, PURPLE, "Bundle box path")

        # employees
        self._emp("2", 170, 180, YELLOW)
        self._emp("1", 810, 205, YELLOW)
        self._emp("3", 340, 330, YELLOW)
        self._emp("4", 905, 330, YELLOW)
        self._emp("5", 1080, 330, YELLOW)
        self._emp("6", 1060, 470, YELLOW)
        self._emp("7", 1120, 470, YELLOW)
        self._emp("8", 1210, 445, YELLOW)

        self._emp("4", 830, 575, ORANGE, "4_orange")
        self._emp("6", 1465, 385, ORANGE, "6_orange")
        self._emp("5", 1700, 385, BLUE, "5_blue")
        self._emp("6", 1180, 215, BLUE, "6_blue")
        self._emp("4", 1160, 555, BLUE, "4_blue")
        self._emp("3", 1790, 585, BLUE, "3_blue")
        self._emp("2", 1790, 620, BLUE, "2_blue")
        self._emp("1", 1710, 655, BLUE, "1_blue")

    def _legend_box(self, x, y, color, text):
        self.canvas.create_rectangle(self.sx(x), self.sy(y), self.sx(x + 70), self.sy(y + 28), fill=color, outline="")
        self.canvas.create_text(self.sx(x + 105), self.sy(y + 14), text=text, anchor="w", font=("Arial", max(9, int(11 * self.scale_factor))))

    def _rect(self, x1, y1, x2, y2, label, vertical=False, bold=False):
        self.canvas.create_rectangle(self.sx(x1), self.sy(y1), self.sx(x2), self.sy(y2), outline=LINE, width=max(1, int(2 * self.scale_factor)))
        if label:
            font = ("Arial", max(9, int((16 if bold else 11) * self.scale_factor)), "bold" if bold else "normal")
            if vertical:
                self.canvas.create_text(self.sx((x1+x2)/2), self.sy((y1+y2)/2), text=label, angle=90, font=font)
            else:
                self.canvas.create_text(self.sx((x1+x2)/2), self.sy((y1+y2)/2), text=label, font=font)

    def _emp(self, label, x, y, color, key=None):
        key = key or label
        rect = self.canvas.create_rectangle(self.sx(x), self.sy(y), self.sx(x + 78), self.sy(y + 30), fill=color, outline="")
        text = self.canvas.create_text(self.sx(x + 39), self.sy(y + 15), text=label, font=("Arial", max(9, int(12 * self.scale_factor))))
        self.employee_items[key] = rect
        self.employee_labels[key] = text

    def _refresh_mode(self):
        bundle = self.mode.get() == "bundle"
        for key in ["4_orange", "6_orange", "6_blue", "4_blue", "5_blue", "3_blue", "2_blue", "1_blue"]:
            show = bundle
            self.canvas.itemconfigure(self.employee_items[key], state="normal" if show else "hidden")
            self.canvas.itemconfigure(self.employee_labels[key], state="normal" if (show and self.show_labels.get()) else "hidden")
        for key in ["1", "2", "3", "4", "5", "6", "7", "8"]:
            if key in self.employee_labels:
                self.canvas.itemconfigure(self.employee_labels[key], state="normal" if self.show_labels.get() else "hidden")
        self.status.config(
            text="Bundle mode: trays follow orange path, bundle boxes follow purple path."
            if bundle else
            "Normal mode: trays follow red path, loop around 4, go across to 5, and every 12 trays create a blue case."
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
        item = self.canvas.create_rectangle(self.sx(112), self.sy(305), self.sx(124), self.sy(317), fill=TRAY, outline=TRAY)
        self.tray_items.append({"id": item, "stage": "drop_vemag"})

    def _spawn_regular_case(self):
        item = self.canvas.create_rectangle(self.sx(972), self.sy(388), self.sx(988), self.sy(404), fill=BLUE, outline=BLUE)
        self.case_items.append({"id": item, "stage": "regular_down"})

    def _spawn_bundle_case(self):
        item = self.canvas.create_rectangle(self.sx(1752), self.sy(612), self.sx(1768), self.sy(628), fill=PURPLE, outline=PURPLE)
        self.case_items.append({"id": item, "stage": "bundle_up"})

    def _move_trays(self, dt_real):
        remove = []
        speed_px = 260 * self.scale_factor * dt_real
        for tray in self.tray_items:
            item = tray["id"]
            x1, y1, x2, y2 = self.canvas.coords(item)

            if self.mode.get() == "normal":
                if tray["stage"] == "drop_vemag":
                    if y2 < self.sy(455):
                        self.canvas.move(item, 0, speed_px)
                    else:
                        tray["stage"] = "horizontal"
                elif tray["stage"] == "horizontal":
                    if x2 < self.sx(800):
                        self.canvas.move(item, speed_px, 0)
                    else:
                        tray["stage"] = "up_to_4"
                elif tray["stage"] == "up_to_4":
                    if y1 > self.sy(295):
                        self.canvas.move(item, 0, -speed_px)
                    else:
                        tray["stage"] = "across_4_5"
                elif tray["stage"] == "across_4_5":
                    if x2 < self.sx(980):
                        self.canvas.move(item, speed_px, 0)
                    else:
                        remove.append(tray)
                        self.tray_total += 1
                        self.regular_pack_buffer += 1
                        if self.regular_pack_buffer >= 12:
                            self.regular_pack_buffer = 0
                            self.regular_case_total += 1
                            self._spawn_regular_case()
            else:
                if tray["stage"] == "drop_vemag":
                    if y2 < self.sy(455):
                        self.canvas.move(item, 0, speed_px)
                    else:
                        tray["stage"] = "horizontal"
                elif tray["stage"] == "horizontal":
                    if x2 < self.sx(885):
                        self.canvas.move(item, speed_px, 0)
                    else:
                        tray["stage"] = "down_bundle"
                elif tray["stage"] == "down_bundle":
                    if y2 < self.sy(620):
                        self.canvas.move(item, 0, speed_px)
                    else:
                        tray["stage"] = "bundle_across"
                elif tray["stage"] == "bundle_across":
                    if x2 < self.sx(1735):
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
                if y2 < self.sy(470):
                    self.canvas.move(item, 0, speed_px)
                else:
                    case["stage"] = "regular_right"
            elif case["stage"] == "regular_right":
                if x2 < self.sx(1450):
                    self.canvas.move(item, speed_px, 0)
                else:
                    case["stage"] = "regular_up"
            elif case["stage"] == "regular_up":
                if y1 > self.sy(388):
                    self.canvas.move(item, 0, -speed_px)
                else:
                    case["stage"] = "regular_pallet"
            elif case["stage"] == "regular_pallet":
                if x2 < self.sx(1525):
                    self.canvas.move(item, speed_px, 0)
                else:
                    remove.append(case)
            elif case["stage"] == "bundle_up":
                if y1 > self.sy(350):
                    self.canvas.move(item, 0, -speed_px)
                else:
                    case["stage"] = "bundle_left"
            elif case["stage"] == "bundle_left":
                if x1 > self.sx(1450):
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
        self.lbl_btpm.config(text=f"{self.bundle_trays_per_min.get():.1f}")
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
