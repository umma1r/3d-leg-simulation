import os, math
from trame.app import get_server
from trame.widgets import html, vuetify, vtk as wvtk
from trame.ui.vuetify import SinglePageWithDrawerLayout
import vtk

def load_stl(p):
    r = vtk.vtkSTLReader(); r.SetFileName(p); r.Update(); return r.GetOutput()

def tf_poly(poly, tf):
    f = vtk.vtkTransformPolyDataFilter(); f.SetTransform(tf); f.SetInputData(poly); f.Update(); return f.GetOutput()

class LegScene:
    def __init__(self, thigh="thigh_model.stl", shin="shin_model.stl"):
        # Renderer / window (offscreen + interactor for trame)
        self.ren = vtk.vtkRenderer(); self.ren.SetBackground(0,0,0)
        self.win = vtk.vtkRenderWindow(); self.win.AddRenderer(self.ren)
        self.win.OffScreenRenderingOn()

        self.iren = vtk.vtkRenderWindowInteractor()
        self.iren.SetRenderWindow(self.win)
        self.iren.Initialize()

        # Thigh
        t_pd = load_stl(thigh)
        t = vtk.vtkTransform(); t.RotateZ(-90); t.RotateX(-90)
        t_tf = tf_poly(t_pd, t)
        t_m = vtk.vtkPolyDataMapper(); t_m.SetInputData(t_tf)
        self.thigh = vtk.vtkActor(); self.thigh.SetMapper(t_m); self.ren.AddActor(self.thigh)

        # Shin
        s_pd = load_stl(shin)
        base = vtk.vtkTransform(); base.RotateZ(-90); base.RotateX(-90)
        s_pre = tf_poly(s_pd, base)
        thigh_top = self.thigh.GetBounds()[3]; shin_bot = s_pre.GetBounds()[2]
        shift_y = thigh_top - shin_bot - 2
        final = vtk.vtkTransform(); final.Concatenate(base); final.Translate(1.9, shift_y, .06)
        s_tf = tf_poly(s_pd, final)
        self.shin_m = vtk.vtkPolyDataMapper(); self.shin_m.SetInputData(s_tf)
        self.shin = vtk.vtkActor(); self.shin.SetMapper(self.shin_m); self.ren.AddActor(self.shin)

        # Arrows (tendon = green, external = red)
        self.arr_t = self._arrow((0,1,0)); self.ren.AddActor(self.arr_t)
        self.arr_fe= self._arrow((1,0,0)); self.ren.AddActor(self.arr_fe)

        cam = self.ren.GetActiveCamera()
        cam.SetPosition(0,-1.5,0); cam.SetFocalPoint(0,0,0); cam.SetViewUp(0,0,1)
        self.ren.ResetCamera(); self.win.Render()

    def _arrow(self, color):
        src = vtk.vtkArrowSource()
        tf  = vtk.vtkTransform(); tf.Translate(-2,0,0)
        f = vtk.vtkTransformPolyDataFilter(); f.SetTransform(tf); f.SetInputConnection(src.GetOutputPort()); f.Update()
        m = vtk.vtkPolyDataMapper(); m.SetInputData(f.GetOutput())
        a = vtk.vtkActor(); a.SetMapper(m); a.GetProperty().SetColor(*color); a.SetOrigin(-1,0,0)
        return a

    def render_window(self): return self.win

    def update(self, mass, massW, angle_val, shin_len, angle_t):
        Fg = mass*9.81; Fe = massW*9.81; angle = 90 - angle_val
        a = math.radians(angle); at = math.radians(angle_t)
        rt, rg, re = shin_len, shin_len/3, shin_len
        denom = (rt*math.sin(at)) or 1e-9
        Ft = ((re*math.sin(a))/denom)*Fe + ((rg*Fg*math.sin(a))/denom)
        t_net = rt*Ft*math.sin(at) - rg*Fg*math.sin(a) - re*Fe*math.sin(a)

        self.shin.SetOrientation(0, -angle_val, 0)
        kx, ky, kz = self.shin.GetOrigin()

        tg = vtk.vtkTransform(); tg.Translate(kx-1.0, ky, kz-1.5); tg.RotateY(90); sg = 0.01*abs(Ft); tg.Scale(sg,sg,sg)
        self.arr_t.SetUserTransform(tg)
        tr = vtk.vtkTransform(); tr.Translate(kx-2.5, ky, kz-0.5); tr.RotateY(90); sr = max(0.016*abs(Fe),0.05); tr.Scale(sr,sr,sr)
        self.arr_fe.SetUserTransform(tr)

        self.win.Render()
        return dict(Fg=Fg, Fe=Fe, Angle=angle, Length=shin_len, Angle_t=angle_t, Ft=Ft, Torque=t_net)

# UI (Vue2)
server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller
scene = LegScene("thigh_model.stl", "shin_model.stl")

state.mass=10.0; state.massW=5.0; state.angle_val=30.0; state.shin_len=0.50; state.angle_t=30.0

@state.change("mass","massW","angle_val","shin_len","angle_t")
def on_change(mass, massW, angle_val, shin_len, angle_t, **_):
    vals = scene.update(mass, massW, angle_val, shin_len, angle_t)
    state.update(vals); ctrl.view_update()

with SinglePageWithDrawerLayout(server, title="Leg Force Simulation") as layout:
    with layout.content:
        with vuetify.VRow(dense=True, classes="pa-2"):
            with vuetify.VCol(cols=3):
                vuetify.VSlider(v_model=("mass", state.mass),    min=0,   max=20, step=1,    label="Leg mass (kg)")
                vuetify.VSlider(v_model=("massW", state.massW),  min=0,   max=10, step=1,    label="Exercise weight (kg)")
                vuetify.VSlider(v_model=("angle_val", state.angle_val), min=0, max=45, step=1, label="Leg angle (deg)")
                vuetify.VSlider(v_model=("shin_len", state.shin_len),   min=0.1, max=1.0, step=0.01, label="Shin length (m)")
                vuetify.VSlider(v_model=("angle_t", state.angle_t),     min=30, max=60, step=1, label="Angle_t (deg)")
                html.Pre("{{ 'Fg: {:.2f} N\\nFe: {:.2f} N\\nAngle: {:.2f} deg\\nLength: {:.2f} m\\nAngle_t: {:.2f} deg\\nFt: {:.2f} N\\nTorque: {:.2f} N·m'.format(Fg or 0, Fe or 0, Angle or 0, Length or 0, Angle_t or 0, Ft or 0, Torque or 0) }}")
            with vuetify.VCol(cols=9, classes="pa-0"):
                view = wvtk.VtkRemoteView(scene.render_window(), ref="view")
                ctrl.view_update = lambda: view.update()

# initial render
on_change(state.mass, state.massW, state.angle_val, state.shin_len, state.angle_t)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server.start(address="0.0.0.0", port=port, open_browser=False)
