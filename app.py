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

DESIGN_W = 1900
DESIGN_H = 820

SCALE = min((WINDOW_W - 40) / DESIGN_W, (WINDOW_H - 180) / DESIGN_H)

def sx(x): return x * SCALE
def sy(y): return y * SCALE

class SimApp:

    def __init__(self, root):

        self.root = root
        self.root.title("Grinding / Bundle Flow Simulator")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.configure(bg=BG)

        self.mode = tk.StringVar(value="normal")
        self.trays_per_min = tk.DoubleVar(value=32.0)
        self.sim_minutes = tk.DoubleVar(value=60.0)
        self.time_scale = tk.DoubleVar(value=120.0)
        self.show_labels = tk.BooleanVar(value=True)

        self.running = False
        self.elapsed_sim_sec = 0
        self.last_spawn = 0

        self.tray_total = 0
        self.regular_case_total = 0
        self.bundle_case_total = 0
        self.regular_buffer = 0
        self.bundle_buffer = 0

        self.trays = []
        self.cases = []

        self._build_ui()
        self._draw_layout()
        self._tick()

    def _build_ui(self):

        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x")

        ttk.Radiobutton(top,text="Normal Pack",variable=self.mode,value="normal").pack(side="left")
        ttk.Radiobutton(top,text="Bundle Mode",variable=self.mode,value="bundle").pack(side="left")

        ttk.Label(top,text="Trays/min").pack(side="left",padx=10)

        ttk.Scale(
            top,
            from_=10,
            to=90,
            variable=self.trays_per_min,
            orient="horizontal",
            length=200
        ).pack(side="left")

        ttk.Button(top,text="Start",command=self.start).pack(side="left",padx=10)
        ttk.Button(top,text="Pause",command=self.pause).pack(side="left")
        ttk.Button(top,text="Reset",command=self.reset).pack(side="left")

        self.canvas = tk.Canvas(
            self.root,
            width=int(DESIGN_W*SCALE),
            height=int(DESIGN_H*SCALE),
            bg=BG,
            highlightthickness=0
        )
        self.canvas.pack()

    def _rect(self,x1,y1,x2,y2,label,vertical=False):

        self.canvas.create_rectangle(sx(x1),sy(y1),sx(x2),sy(y2),outline=LINE,width=2)

        if vertical:
            self.canvas.create_text(
                sx((x1+x2)/2),
                sy((y1+y2)/2),
                text=label,
                angle=90
            )
        else:
            self.canvas.create_text(
                sx((x1+x2)/2),
                sy((y1+y2)/2),
                text=label
            )

    def _emp(self,label,x,y,color,key=None):

        rect = self.canvas.create_rectangle(
            sx(x),
            sy(y),
            sx(x+60),
            sy(y+28),
            fill=color,
            outline=""
        )

        text = self.canvas.create_text(
            sx(x+30),
            sy(y+14),
            text=label
        )

    def _draw_layout(self):

        c=self.canvas
        c.delete("all")

        self._rect(80,0,650,55,"Grinding Room")
        self._rect(30,95,80,490,"Vemag / Brick",True)
        self._rect(190,95,500,135,"Blender Mixer Augers")
        self._rect(500,95,585,135,"Grinder")
        self._rect(585,0,645,135,"Product Dump",True)
        self._rect(125,155,285,285,"Denester")
        self._rect(80,402,585,455,"Multivac")

        self._rect(800,560,1035,610,"Index Conveyor")
        self._rect(1035,530,1260,620,"Shanklin")
        self._rect(1335,530,1605,620,"Heat Tunnel")
        self._rect(1605,560,1675,610,"Pack")

        self._rect(1300,300,1375,350,"Pallet")
        self._rect(1375,320,1650,350,"Tape")

        # employees

        self._emp("2",85,110,YELLOW)
        self._emp("1",505,135,YELLOW)
        self._emp("3",315,225,YELLOW)
        self._emp("4",640,255,YELLOW)
        self._emp("5",700,255,YELLOW)

        self._emp("5",720,585,YELLOW) # moved up
        self._emp("6",760,665,YELLOW)
        self._emp("7",760,250,YELLOW)

        self._emp("8",1210,410,YELLOW)

        # blue employees
        self._emp("5",1085,545,BLUE) # centered at shanklin
        self._emp("4",1495,455,BLUE)
        self._emp("3",1665,560,BLUE)
        self._emp("2",1665,595,BLUE)
        self._emp("1",1635,630,BLUE)

    def start(self):
        self.running=True

    def pause(self):
        self.running=False

    def reset(self):

        self.running=False
        self.trays.clear()
        self.cases.clear()

        self.canvas.delete("tray")
        self.canvas.delete("case")

        self.elapsed_sim_sec=0
        self.last_spawn=0

    def _spawn_tray(self):

        size=10

        tray=self.canvas.create_rectangle(
            sx(74),
            sy(300),
            sx(74+size),
            sy(300+size),
            fill=TRAY,
            outline=TRAY,
            tags="tray"
        )

        path=[
            (80,420),
            (620,420),
            (620,195),
            (685,195),
            (685,275),
            (715,275)
        ]

        self.trays.append({
            "id":tray,
            "path":path,
            "i":0,
            "bundle":False
        })

    def _spawn_regular_case(self):

        size=12

        case=self.canvas.create_rectangle(
            sx(707),
            sy(268),
            sx(707+size),
            sy(268+size),
            fill=BLUE,
            outline=BLUE,
            tags="case"
        )

        path=[
            (715,420),
            (1300,420),
            (1300,325),
            (1375,325)
        ]

        self.cases.append({"id":case,"path":path,"i":0})

    def _spawn_bundle_case(self):

        size=12

        case=self.canvas.create_rectangle(
            sx(1600),
            sy(607),
            sx(1600+size),
            sy(607+size),
            fill=PURPLE,
            outline=PURPLE,
            tags="case"
        )

        path=[
            (1660,615),
            (1660,300),
            (1300,300)
        ]

        self.cases.append({"id":case,"path":path,"i":0})

    def _move(self,item,path,speed):

        coords=self.canvas.coords(item)
        cx=(coords[0]+coords[2])/2
        cy=(coords[1]+coords[3])/2

        if path["i"]>=len(path["path"]):
            return True

        tx,ty=path["path"][path["i"]]
        tx,ty=sx(tx),sy(ty)

        dx,dy=tx-cx,ty-cy
        dist=math.hypot(dx,dy)

        if dist<speed:
            self.canvas.move(item,dx,dy)
            path["i"]+=1
        else:
            self.canvas.move(item,speed*dx/dist,speed*dy/dist)

        return path["i"]>=len(path["path"])

    def _tick(self):

        dt=0.05

        if self.running:

            self.elapsed_sim_sec+=dt*self.time_scale.get()

            interval=60/self.trays_per_min.get()

            if self.elapsed_sim_sec-self.last_spawn>interval:

                self._spawn_tray()
                self.last_spawn=self.elapsed_sim_sec

            speed=250*SCALE*dt

            remove=[]

            for t in self.trays:

                done=self._move(t["id"],t,speed)

                if done:

                    if self.mode.get()=="normal":

                        remove.append(t)
                        self.regular_buffer+=1

                        if self.regular_buffer>=12:

                            self.regular_buffer=0
                            self._spawn_regular_case()

                    else:

                        if not t["bundle"]:

                            t["bundle"]=True
                            t["path"]=[(715,615),(1605,615)]
                            t["i"]=0

                        else:

                            remove.append(t)
                            self.bundle_buffer+=1

                            if self.bundle_buffer>=12:

                                self.bundle_buffer=0
                                self._spawn_bundle_case()

            for r in remove:
                self.canvas.delete(r["id"])
                self.trays.remove(r)

            for c in list(self.cases):

                if self._move(c["id"],c,200*SCALE*dt):
                    self.canvas.delete(c["id"])
                    self.cases.remove(c)

        self.root.after(50,self._tick)

def main():

    root=tk.Tk()
    SimApp(root)
    root.mainloop()

if __name__=="__main__":
    main()
