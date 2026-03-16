import tkinter as tk
from tkinter import ttk

BG = "#f4f4f4"
LINE = "#222222"
YELLOW = "#ffe94d"
BLUE = "#21a7df"
ORANGE = "#f7b52c"
TRAY = "#111111"
CASE = "#2459ff"
RED = "#cc2f2f"

class SimApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Grinding / Bundle Flow Simulator v3")
        self.root.geometry("1700x930")
        self.root.configure(bg=BG)

        self.mode = tk.StringVar(value="normal")
        self.trays_per_min = tk.DoubleVar(value=32.0)
        self.bundle_trays_per_min = tk.DoubleVar(value=40.0)
        self.changeovers = tk.IntVar(value=0)
        self.sim_minutes = tk.DoubleVar(value=60.0)
        self.time_scale = tk.DoubleVar(value=120.0)
        self.running = False
        self.show_labels = tk.BooleanVar(value=True)

        self.tray_items = []
        self.case_items = []
        self.employee_items = {}
        self.employee_labels = {}

        self.elapsed_sim_sec = 0.0
        self.last_spawn_sec = 0.0
        self.normal_tray_count = 0
        self.case_count = 0
        self.tray_total = 0
        self.changeover_active = False
        self.changeover_end_sec = 0.0
        self.completed_changeovers = 0

        self._build_ui()
        self._draw_layout()
        self._refresh_mode()
        self._update_labels()
        self._tick()

    def _build_ui(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="Mode").pack(side="left")
        ttk.Radiobutton(top, text="Normal Pack", variable=self.mode, value="normal", command=self._refresh_mode).pack(side="left", padx=4)
        ttk.Radiobutton(top, text="Bundle Mode", variable=self.mode, value="bundle", command=self._refresh_mode).pack(side="left", padx=(0, 12))

        ttk.Label(top, text="Grinding trays/min").pack(side="left")
        ttk.Scale(top, from_=10, to=90, variable=self.trays_per_min, orient="horizontal", length=180, command=lambda _=None: self._update_labels()).pack(side="left", padx=4)
        self.lbl_tpm = ttk.Label(top, text="")
        self.lbl_tpm.pack(side="left", padx=(0, 12))

        ttk.Label(top, text="Bundle trays/min").pack(side="left")
        ttk.Scale(top, from_=10, to=90, variable=self.bundle_trays_per_min, orient="horizontal", length=180, command=lambda _=None: self._update_labels()).pack(side="left", padx=4)
        self.lbl_btpm = ttk.Label(top, text="")
        self.lbl_btpm.pack(side="left", padx=(0, 12))

        ttk.Label(top, text="Changeovers").pack(side="left")
        ttk.Spinbox(top, from_=0, to=20, width=5, textvariable=self.changeovers, command=self._update_labels).pack(side="left", padx=4)

        ttk.Label(top, text="Sim minutes").pack(side="left", padx=(12, 0))
        ttk.Spinbox(top, from_=10, to=240, width=6, textvariable=self.sim_minutes, command=self._update_labels).pack(side="left", padx=4)

        ttk.Label(top, text="Speed-up").pack(side="left", padx=(12, 0))
        ttk.Scale(top, from_=30, to=300, variable=self.time_scale, orient="horizontal", length=140, command=lambda _=None: self._update_labels()).pack(side="left", padx=4)
        self.lbl_scale = ttk.Label(top, text="")
        self.lbl_scale.pack(side="left", padx=(0, 12))

        controls = tk.Frame(self.root, bg=BG)
        controls.pack(fill="x", padx=10, pady=(0, 8))

        ttk.Button(controls, text="Start", command=self.start).pack(side="left")
        ttk.Button(controls, text="Pause", command=self.pause).pack(side="left", padx=4)
        ttk.Button(controls, text="Reset", command=self.reset).pack(side="left", padx=4)
        ttk.Checkbutton(controls, text="Show Labels", variable=self.show_labels, command=self._refresh_mode).pack(side="left", padx=8)

        self.status = ttk.Label(controls, text="Ready. Normal mode now sends trays up and across between positions 4 and 5.")
        self.status.pack(side="left", padx=16)

        kpi_row = tk.Frame(self.root, bg=BG)
        kpi_row.pack(fill="x", padx=10, pady=(0, 8))
        self.kpis = {}
        for label in ["Minutes Simulated", "Trays Produced", "Cases Produced", "Completed Changeovers", "Backlog"]:
            box = tk.Frame(kpi_row, bg="white", highlightbackground="#bbbbbb", highlightthickness=1)
            box.pack(side="left", padx=4)
            tk.Label(box, text=label, font=("Arial", 10, "bold"), bg="white").pack(padx=10, pady=(6, 2))
            val = tk.Label(box, text="0", font=("Arial", 12), bg="white")
            val.pack(padx=10, pady=(0, 6))
            self.kpis[label] = val

        self.canvas = tk.Canvas(self.root, width=1660, height=760, bg=BG, highlightthickness=0)
        self.canvas.pack(padx=10, pady=6)

    def _draw_layout(self):
        c = self.canvas
        c.delete("all")
        c.create_text(830, 28, text="Grinding Room / Bundle Operation Flow", font=("Arial", 20, "bold"))

        self._rect(120, 50, 770, 110, "Grinding Room", bold=True)
        self._rect(40, 130, 110, 460, "Vemag / Brick", vertical=True)
        self._rect(250, 145, 690, 185, "Blender Mixer Augers")
        self._rect(695, 145, 790, 185, "Grinder")
        self._rect(790, 50, 875, 185, "Product Dump", vertical=True)
        self._rect(150, 215, 335, 315, "Denester")
        self._rect(120, 395, 690, 455, "Multivac")
        self._rect(690, 215, 840, 455, "")
        self._rect(840, 215, 930, 455, "")

        self._rect(980, 535, 1220, 580, "Index Conveyor")
        self._rect(1220, 515, 1410, 600, "Shanklin")
        self._rect(1510, 515, 1760, 600, "Heat Tunnel")
        self._rect(1760, 535, 1835, 580, "Pack")
        self._rect(1510, 360, 1585, 410, "Pallet")
        self._rect(1585, 380, 1775, 410, "Tape, conveyor")

        # Normal tray path (red) - horizontal, up, then across between 4 and 5
        c.create_line(110, 425, 840, 425, fill=RED, width=3)
        c.create_line(840, 425, 840, 225, fill=RED, width=3)
        c.create_line(840, 225, 1045, 225, fill=RED, width=3)

        # Case flow (blue)
        c.create_line(1045, 225, 1045, 455, fill=CASE, width=3)
        c.create_line(1045, 455, 1510, 455, fill=CASE, width=3)
        c.create_line(1510, 455, 1510, 385, fill=CASE, width=3)
        c.create_line(1510, 385, 1585, 385, fill=CASE, width=3)

        # Bundle path
        c.create_line(840, 455, 840, 560, fill=LINE, width=3)
        c.create_line(840, 560, 980, 560, fill=LINE, width=3)
        c.create_line(1410, 560, 1510, 560, fill=LINE, width=3)
        c.create_line(1760, 560, 1835, 560, fill=LINE, width=3)

        # Legend
        c.create_rectangle(1260, 150, 1325, 175, fill=YELLOW, outline="")
        c.create_text(1370, 163, text="Grinding labor", anchor="w", font=("Arial", 11))
        c.create_rectangle(1260, 190, 1325, 215, fill=BLUE, outline="")
        c.create_text(1415, 203, text="Dedicated bundle labor", anchor="w", font=("Arial", 11))
        c.create_rectangle(1260, 230, 1325, 255, fill=ORANGE, outline="")
        c.create_text(1450, 243, text="Grinding labor pulled into bundle tasks", anchor="w", font=("Arial", 11))
        c.create_rectangle(1260, 270, 1325, 295, fill=TRAY, outline="")
        c.create_text(1370, 283, text="Tray", anchor="w", font=("Arial", 11))
        c.create_rectangle(1260, 310, 1325, 335, fill=CASE, outline="")
        c.create_text(1395, 323, text="Full case (12 trays)", anchor="w", font=("Arial", 11))

        # Grinding labor
        self._emp("2", 155, 160, YELLOW)
        self._emp("1", 745, 190, YELLOW)
        self._emp("3", 330, 275, YELLOW)
        self._emp("4", 860, 310, YELLOW)
        self._emp("5", 1020, 310, YELLOW)
        self._emp("6", 1005, 455, YELLOW)
        self._emp("7", 1065, 455, YELLOW)
        self._emp("8", 1140, 430, YELLOW)

        # Pulled
        self._emp("4", 900, 535, ORANGE, "4_orange")
        self._emp("6", 970, 595, ORANGE, "6_orange")
        self._emp("7", 1040, 655, ORANGE, "7_orange")
        self._emp("8", 1430, 385, ORANGE, "8_orange")

        # Dedicated bundle
        self._emp("6", 1210, 275, BLUE, "6_blue")
        self._emp("4", 1185, 515, BLUE, "4_blue")
        self._emp("5", 1740, 385, BLUE, "5_blue")
        self._emp("3", 1830, 540, BLUE, "3_blue")
        self._emp("2", 1830, 575, BLUE, "2_blue")
        self._emp("1", 1750, 610, BLUE, "1_blue")

    def _rect(self, x1, y1, x2, y2, label, vertical=False, bold=False):
        self.canvas.create_rectangle(x1, y1, x2, y2, outline=LINE, width=2)
        if label:
            font = ("Arial", 16, "bold") if bold else ("Arial", 11)
            if vertical:
                self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=label, angle=90, font=font)
            else:
                self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=label, font=font)

    def _emp(self, label, x, y, color, key=None):
        key = key or label
        rect = self.canvas.create_rectangle(x, y, x+70, y+28, fill=color, outline="")
        text = self.canvas.create_text(x+35, y+14, text=label, font=("Arial", 12))
        self.employee_items[key] = rect
        self.employee_labels[key] = text

    def _refresh_mode(self):
        bundle = self.mode.get() == "bundle"
        for key in ["4_orange", "6_orange", "7_orange", "8_orange", "6_blue", "4_blue", "5_blue", "3_blue", "2_blue", "1_blue"]:
            show = bundle
            self.canvas.itemconfigure(self.employee_items[key], state="normal" if show else "hidden")
            self.canvas.itemconfigure(self.employee_labels[key], state="normal" if (show and self.show_labels.get()) else "hidden")
        for key in ["1", "2", "3", "4", "5", "6", "7", "8"]:
            self.canvas.itemconfigure(self.employee_labels[key], state="normal" if self.show_labels.get() else "hidden")
        self.status.config(
            text="Bundle mode: trays divert down to Index Conveyor; yellow 4,5,6,7,8 are no longer available for normal case flow."
            if bundle else
            "Normal mode: trays move across the red path, up, then across between positions 4 and 5."
        )

    def start(self):
        self.running = True

    def pause(self):
        self.running = False

    def reset(self):
        self.running = False
        self.elapsed_sim_sec = 0.0
        self.last_spawn_sec = 0.0
        self.normal_tray_count = 0
        self.case_count = 0
        self.tray_total = 0
        self.changeover_active = False
        self.changeover_end_sec = 0.0
        self.completed_changeovers = 0
        for item in list(self.tray_items) + list(self.case_items):
            self.canvas.delete(item["id"])
        self.tray_items = []
        self.case_items = []
        self._update_labels()
        self._refresh_mode()

    def _spawn_tray(self):
        item = self.canvas.create_rectangle(108, 420, 118, 430, fill=TRAY, outline=TRAY)
        self.tray_items.append({"id": item, "stage": "horizontal"})

    def _spawn_case(self):
        item = self.canvas.create_rectangle(1038, 218, 1052, 232, fill=CASE, outline=CASE)
        self.case_items.append({"id": item, "stage": "normal"})

    def _spawn_bundle_case(self):
        item = self.canvas.create_rectangle(1760, 552, 1774, 566, fill=CASE, outline=CASE)
        self.case_items.append({"id": item, "stage": "bundle"})

    def _move_trays(self, dt_real):
        remove = []
        speed_px = 250 * dt_real
        for tray in self.tray_items:
            item = tray["id"]
            x1, y1, x2, y2 = self.canvas.coords(item)

            if self.mode.get() == "normal":
                if tray["stage"] == "horizontal":
                    if x2 < 840:
                        self.canvas.move(item, speed_px, 0)
                    else:
                        tray["stage"] = "up"
                elif tray["stage"] == "up":
                    if y1 > 220:
                        self.canvas.move(item, 0, -speed_px)
                    else:
                        tray["stage"] = "across_pack"
                elif tray["stage"] == "across_pack":
                    if x2 < 1045:
                        self.canvas.move(item, speed_px, 0)
                    else:
                        remove.append(tray)
                        self.tray_total += 1
                        self.normal_tray_count += 1
                        if self.normal_tray_count >= 12:
                            self.normal_tray_count = 0
                            self.case_count += 1
                            self._spawn_case()
            else:
                if tray["stage"] == "horizontal":
                    if x2 < 840:
                        self.canvas.move(item, speed_px, 0)
                    else:
                        tray["stage"] = "down_to_bundle"
                elif tray["stage"] == "down_to_bundle":
                    if y2 < 560:
                        self.canvas.move(item, 0, speed_px)
                    else:
                        tray["stage"] = "to_index"
                elif tray["stage"] == "to_index":
                    if x2 < 980:
                        self.canvas.move(item, speed_px, 0)
                    else:
                        remove.append(tray)
                        self.tray_total += 1
                        self.normal_tray_count += 1
                        if self.normal_tray_count >= 12:
                            self.normal_tray_count = 0
                            self.case_count += 1
                            self._spawn_bundle_case()

        for tray in remove:
            if tray in self.tray_items:
                self.canvas.delete(tray["id"])
                self.tray_items.remove(tray)

    def _move_cases(self, dt_real):
        remove = []
        speed_px = 180 * dt_real
        for case in self.case_items:
            item = case["id"]
            x1, y1, x2, y2 = self.canvas.coords(item)
            if case["stage"] == "normal":
                if y2 < 455:
                    self.canvas.move(item, 0, speed_px)
                elif x2 < 1510:
                    self.canvas.move(item, speed_px, 0)
                elif y1 > 385:
                    self.canvas.move(item, 0, -speed_px)
                elif x2 < 1585:
                    self.canvas.move(item, speed_px, 0)
                else:
                    remove.append(case)
            elif case["stage"] == "bundle":
                if x2 < 1835:
                    self.canvas.move(item, speed_px, 0)
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
            self.status.config(text="Changeover complete. Production resumed.")

    def _update_labels(self):
        self.lbl_tpm.config(text=f"{self.trays_per_min.get():.1f}")
        self.lbl_btpm.config(text=f"{self.bundle_trays_per_min.get():.1f}")
        self.lbl_scale.config(text=f"{self.time_scale.get():.0f}x")
        self.kpis["Minutes Simulated"].config(text=f"{self.elapsed_sim_sec / 60:.1f}")
        self.kpis["Trays Produced"].config(text=str(self.tray_total))
        self.kpis["Cases Produced"].config(text=str(self.case_count))
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
