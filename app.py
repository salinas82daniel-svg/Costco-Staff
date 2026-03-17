import json
import math
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog, messagebox

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


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Layout Editor + Simulator")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.configure(bg=BG)

        self.mode = tk.StringVar(value="edit")
        self.flow = tk.StringVar(value="normal")

        self.layout = {"employees": [], "notes": []}
        self.drag_item = None
        self.drag_offset = (0, 0)
        self.item_map = {}

        self.running = False
        self.elapsed = 0
        self.trays = []
        self.cases = []

        self._ui()
        self._draw()
        self._tick()

    def _ui(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x")

        ttk.Radiobutton(top, text="Edit", variable=self.mode, value="edit", command=self._draw).pack(side="left")
        ttk.Radiobutton(top, text="Sim", variable=self.mode, value="sim", command=self._draw).pack(side="left")

        ttk.Button(top, text="Add Emp", command=self.add_emp).pack(side="left")
        ttk.Button(top, text="Add Note", command=self.add_note).pack(side="left")
        ttk.Button(top, text="Save", command=self.save).pack(side="left")
        ttk.Button(top, text="Load", command=self.load).pack(side="left")

        ttk.Button(top, text="Start", command=self.start).pack(side="left")
        ttk.Button(top, text="Pause", command=self.pause).pack(side="left")

        self.canvas = tk.Canvas(self.root, width=int(DESIGN_W*SCALE), height=int(DESIGN_H*SCALE), bg=BG)
        self.canvas.pack()

        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag_item", None))
        self.canvas.bind("<Double-Button-1>", self.rename)
        self.canvas.bind("<Button-3>", self.delete)

    def _draw(self):
        c = self.canvas
        c.delete("all")
        self.item_map.clear()

        # paths
        self.line([(80,300),(80,420),(620,420),(620,195),(685,195),(685,275),(715,275)], RED)
        self.line([(715,275),(715,420),(1300,420),(1300,325),(1375,325)], BLUE)
        self.line([(715,275),(715,615),(1605,615)], ORANGE)
        self.line([(1605,615),(1660,615),(1660,300),(1300,300)], PURPLE)

        for e in self.layout["employees"]:
            self.draw_emp(e)

        for n in self.layout["notes"]:
            self.draw_note(n)

    def line(self, pts, color):
        coords=[]
        for x,y in pts:
            coords += [sx(x), sy(y)]
        self.canvas.create_line(*coords, fill=color, width=3)

    def draw_emp(self, e):
        x,y=e["x"],e["y"]
        r=self.canvas.create_rectangle(sx(x),sy(y),sx(x+60),sy(y+30),fill=e["color"])
        t=self.canvas.create_text(sx(x+30),sy(y+15),text=e["label"])
        self.item_map[r]=("emp",e)
        self.item_map[t]=("emp",e)

    def draw_note(self, n):
        t=self.canvas.create_text(sx(n["x"]),sy(n["y"]),text=n["text"],anchor="w")
        self.item_map[t]=("note",n)

    def click(self,e):
        if self.mode.get()!="edit": return
        i=self.canvas.find_closest(e.x,e.y)
        if not i: return
        item=i[0]
        if item not in self.item_map: return
        kind,obj=self.item_map[item]
        self.drag_item=(kind,obj)
        if kind=="emp":
            self.drag_offset=(ux(e.x)-obj["x"], uy(e.y)-obj["y"])
        else:
            self.drag_offset=(ux(e.x)-obj["x"], uy(e.y)-obj["y"])

    def drag(self,e):
        if not self.drag_item: return
        kind,obj=self.drag_item
        obj["x"]=ux(e.x)-self.drag_offset[0]
        obj["y"]=uy(e.y)-self.drag_offset[1]
        self._draw()

    def rename(self,e):
        i=self.canvas.find_closest(e.x,e.y)
        if not i: return
        item=i[0]
        if item not in self.item_map: return
        kind,obj=self.item_map[item]
        val=simpledialog.askstring("Edit","Text")
        if val:
            if kind=="emp": obj["label"]=val
            else: obj["text"]=val
        self._draw()

    def delete(self,e):
        i=self.canvas.find_closest(e.x,e.y)
        if not i: return
        item=i[0]
        if item not in self.item_map: return
        kind,obj=self.item_map[item]
        if kind=="emp":
            self.layout["employees"].remove(obj)
        else:
            self.layout["notes"].remove(obj)
        self._draw()

    def add_emp(self):
        self.layout["employees"].append({"label":"E","x":900,"y":400,"color":YELLOW})
        self._draw()

    def add_note(self):
        self.layout["notes"].append({"text":"Note","x":900,"y":200})
        self._draw()

    def save(self):
        f=filedialog.asksaveasfilename(defaultextension=".json")
        if f:
            json.dump(self.layout, open(f,"w"))

    def load(self):
        f=filedialog.askopenfilename()
        if f:
            self.layout=json.load(open(f))
            self._draw()

    def start(self):
        self.mode.set("sim")
        self.running=True

    def pause(self):
        self.running=False

    def spawn_tray(self):
        r=self.canvas.create_rectangle(sx(70),sy(300),sx(80),sy(310),fill="black")
        self.trays.append({"id":r,"path":[(80,420),(620,420),(620,195),(685,195),(685,275),(715,275)],"i":0})

    def move(self,item,dt):
        coords=self.canvas.coords(item["id"])
        cx=(coords[0]+coords[2])/2
        cy=(coords[1]+coords[3])/2
        if item["i"]>=len(item["path"]): return True
        tx,ty=item["path"][item["i"]]
        tx,ty=sx(tx),sy(ty)
        dx,dy=tx-cx,ty-cy
        d=math.hypot(dx,dy)
        if d<2:
            item["i"]+=1
        else:
            self.canvas.move(item["id"],dx/d*2,dy/d*2)
        return False

    def _tick(self):
        if self.running:
            self.spawn_tray()
            remove=[]
            for t in self.trays:
                if self.move(t,0.05):
                    remove.append(t)
            for t in remove:
                self.canvas.delete(t["id"])
                self.trays.remove(t)

        self.root.after(50,self._tick)


def main():
    root=tk.Tk()
    App(root)
    root.mainloop()

if __name__=="__main__":
    main()
