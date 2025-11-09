import sys
import math
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QFormLayout, QSlider, QLabel, QStyleFactory
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import vtk


class LegSimulation(QMainWindow):
    def __init__(self):
        super().__init__()

        # ── Sliders ──────────────────────────────────────────────
        self.massSlider   = self.create_slider(0, 20, 1, 10)

        # Exercise weight: 0–500 g in 50 g steps, then 1000/1500/2000/2500 g
        grams_list = list(range(0, 501, 50)) + [1000, 1500, 2000, 2500]
        self.massW_values_kg = [g / 1000.0 for g in grams_list]
        self.massW = self.create_slider(0, len(self.massW_values_kg) - 1, 1, 0)

        # UI "Leg angle" (0..45). Flexion used in physics = 90 − this.
        self.angle_slider = self.create_slider(0, 45, 1, 30)
        self.shin_length  = self.create_slider(0.1, 1.0, 0.01, 0.5)

        # Angle_t is patellar alpha, constrained to 11.5..20°
        self.angle_t      = self.create_slider(11.5, 20.0, 0.1, 13.0)

        # ── Labels ───────────────────────────────────────────────
        self.Fg_label      = QLabel()
        self.Fe_label      = QLabel()
        self.angle_label   = QLabel()
        self.length_label  = QLabel()
        self.angle_t_label = QLabel()
        self.Ft_label      = QLabel()
        self.t_net_label   = QLabel()

        # ── VTK Widget ───────────────────────────────────────────
        self.vtk_widget = self.create_vtk_widget()

        # macOS-only slider styling to prevent disappearing handles
        if sys.platform == "darwin":
            mac_slider_css = """
            QSlider::groove:horizontal {
                height: 8px; background: #d0d0d0; border-radius: 4px;
            }
            QSlider::sub-page:horizontal {
                background: #2d7dff; border-radius: 4px;
            }
            QSlider::add-page:horizontal {
                background: #d0d0d0; border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #404040; border: 1px solid #404040;
                width: 18px; height: 18px; margin: -6px 0; border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1e90ff; border-color: #1e90ff;
            }
            QSlider::handle:horizontal:pressed {
                background: #1565c0; border-color: #1565c0;
            }
            QSlider::groove:horizontal:disabled,
            QSlider::add-page:horizontal:disabled,
            QSlider::sub-page:horizontal:disabled {
                background: #c0c0c0;
            }
            QSlider::handle:horizontal:disabled {
                background: #a0a0a0; border-color: #808080;
            }
            """
            for s in (self.massSlider, self.massW, self.angle_slider,
                      self.shin_length, self.angle_t):
                s.setStyleSheet(mac_slider_css)

        # Layout for sliders & labels
        form = QFormLayout()
        form.addRow("Leg mass (kg):",        self.massSlider)
        form.addRow("Exercise weight (kg):", self.massW)
        form.addRow("Leg angle (deg):",      self.angle_slider)
        form.addRow("Shin length (m):",      self.shin_length)
        form.addRow("Angle_t (deg):",        self.angle_t)
        form.addRow("Fg:",      self.Fg_label)
        form.addRow("Fe:",      self.Fe_label)
        form.addRow("Angle:",   self.angle_label)
        form.addRow("Length:",  self.length_label)
        form.addRow("Angle_t:", self.angle_t_label)
        form.addRow("Ft:",      self.Ft_label)
        form.addRow("Torque:",  self.t_net_label)

        main_widget = QWidget()
        layout = QHBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.vtk_widget)
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        # ── Connectors (two-way binding between flexion and alpha) ─────────
        self.massSlider.valueChanged.connect(self.update_simulation)
        self.massW.valueChanged.connect(self.update_simulation)
        self.shin_length.valueChanged.connect(self.update_simulation)

        self.angle_slider.valueChanged.connect(self.on_leg_angle_changed)
        self.angle_t.valueChanged.connect(self.on_alpha_changed)

        self.setWindowTitle("Leg Force Simulation")
        self.resize(1200, 600)

        # model references
        self.thigh_actor = None
        self.shin_actor  = None

        # model geometry
        self.load_thigh_model("thigh_model.stl")
        self.load_shin_model("shin_model.stl")

        self.setup_camera()
        self.create_force_arrows()

        # Guard to avoid feedback loops
        self._syncing = False

        # Initialize alpha from current leg angle
        self.on_leg_angle_changed()

    # ── Helpers for float-backed sliders ────────────────────────
    def set_slider_value(self, slider, val_float):
        scale = slider.property("float_scale")
        slider.blockSignals(True)
        slider.setValue(int(round(val_float * scale)))
        slider.blockSignals(False)
        # macOS paint quirk fix: force a restyle/repaint so handle stays visible
        if sys.platform == "darwin":
            slider.style().unpolish(slider)
            slider.style().polish(slider)
            slider.update()

    def create_slider(self, min_val, max_val, step, init_val):
        s = QSlider(Qt.Horizontal)
        if isinstance(min_val, float) or isinstance(max_val, float):
            s.setMinimum(int(min_val * 100))
            s.setMaximum(int(max_val * 100))
            s.setSingleStep(int(step * 100))
            s.setValue(int(init_val * 100))
            s.setProperty("float_scale", 100.0)
        else:
            s.setMinimum(min_val)
            s.setMaximum(max_val)
            s.setSingleStep(step)
            s.setValue(init_val)
            s.setProperty("float_scale", 1.0)
        return s

    def get_slider_value(self, slider):
        return slider.value() / slider.property("float_scale")

    def get_exercise_weight_kg(self):
        idx = int(self.massW.value())
        idx = max(0, min(idx, len(self.massW_values_kg) - 1))
        return self.massW_values_kg[idx]

    def create_vtk_widget(self):
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        widget = QVTKRenderWindowInteractor(self)
        self.ren = vtk.vtkRenderer()
        widget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = widget.GetRenderWindow().GetInteractor()
        # Enable normal rotate/pan/zoom interactions (also activates wheel zoom)
        self.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.iren.Initialize()
        return widget

    # ── Alpha model: monotonic piecewise-linear ─────────────────
    # Anchors: (flexion°, alpha°) — 45→11.5, 65→13.5, 75→14.0, 90→20.0
    ALPHA_POINTS = [
        (45.0, 11.5),
        (65.0, 13.5),
        (75.0, 14.0),
        (90.0, 20.0),
    ]

    def alpha_from_flexion(self, flex_deg: float) -> float:
        pts = self.ALPHA_POINTS
        if flex_deg <= pts[0][0]:
            (x0, y0), (x1, y1) = pts[0], pts[1]
            return y0 + (y1 - y0) * (flex_deg - x0) / (x1 - x0)
        if flex_deg >= pts[-1][0]:
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
            return y0 + (y1 - y0) * (flex_deg - x0) / (x1 - x0)
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            if x0 <= flex_deg <= x1:
                t = (flex_deg - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)
        return 11.5

    def flexion_from_alpha(self, alpha_deg: float) -> float:
        alpha_deg = max(11.5, min(20.0, alpha_deg))
        pts = self.ALPHA_POINTS
        if alpha_deg <= pts[0][1]:
            (x0, y0), (x1, y1) = pts[0], pts[1]
            return x0 + (x1 - x0) * (alpha_deg - y0) / (y1 - y0)
        if alpha_deg >= pts[-1][1]:
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
            return x0 + (x1 - x0) * (alpha_deg - y0) / (y1 - y0)
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            if y0 <= alpha_deg <= y1 or y1 <= alpha_deg <= y0:
                t = (alpha_deg - y0) / (y1 - y0)
                return x0 + t * (x1 - x0)
        return 65.0

    # ── Binding handlers ─────────────────────────────────────────
    def on_leg_angle_changed(self):
        if getattr(self, "_syncing", False):
            return
        self._syncing = True
        try:
            angle_val = self.get_slider_value(self.angle_slider)  # 0..45
            flex = 90.0 - angle_val                               # 45..90
            alpha = self.alpha_from_flexion(flex)
            alpha = max(11.5, min(20.0, alpha))
            self.set_slider_value(self.angle_t, alpha)
        finally:
            self._syncing = False
        self.update_simulation()

    def on_alpha_changed(self):
        if getattr(self, "_syncing", False):
            return
        self._syncing = True
        try:
            alpha = self.get_slider_value(self.angle_t)           # 11.5..20
            flex = self.flexion_from_alpha(alpha)                 # 45..90
            new_angle_val = 90.0 - flex                           # 0..45
            new_angle_val = max(0.0, min(45.0, new_angle_val))
            self.set_slider_value(self.angle_slider, new_angle_val)
        finally:
            self._syncing = False
        self.update_simulation()

    # Rotational movement
    def load_thigh_model(self, filename):
        r = vtk.vtkSTLReader()
        r.SetFileName(filename)
        r.Update()

        tform = vtk.vtkTransform()
        tform.RotateZ(-90)
        tform.RotateX(-90)

        tf_filter = vtk.vtkTransformPolyDataFilter()
        tf_filter.SetTransform(tform)
        tf_filter.SetInputData(r.GetOutput())
        tf_filter.Update()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(tf_filter.GetOutput())

        self.thigh_actor = vtk.vtkActor()
        self.thigh_actor.SetMapper(mapper)
        self.ren.AddActor(self.thigh_actor)

    def load_shin_model(self, filename):
        r = vtk.vtkSTLReader()
        r.SetFileName(filename)
        r.Update()
        shin_poly = r.GetOutput()

        base_tf = vtk.vtkTransform()
        base_tf.RotateZ(-90)
        base_tf.RotateX(-90)

        pre_tf = vtk.vtkTransformPolyDataFilter()
        pre_tf.SetTransform(base_tf)
        pre_tf.SetInputData(shin_poly)
        pre_tf.Update()

        thigh_ymax = self.thigh_actor.GetBounds()[3] if self.thigh_actor else 0.0
        shin_ymin  = pre_tf.GetOutput().GetBounds()[2]
        shift_in_y = thigh_ymax - shin_ymin - 2

        final_tf = vtk.vtkTransform()
        final_tf.Concatenate(base_tf)
        final_tf.Translate(1.9, shift_in_y, .06)

        final_tf_filter = vtk.vtkTransformPolyDataFilter()
        final_tf_filter.SetTransform(final_tf)
        final_tf_filter.SetInputData(shin_poly)
        final_tf_filter.Update()
        self.shin_polydata = final_tf_filter.GetOutput()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(self.shin_polydata)

        self.shin_actor = vtk.vtkActor()
        self.shin_actor.SetMapper(mapper)
        self.ren.AddActor(self.shin_actor)

        b = self.shin_polydata.GetBounds()
        self.shin_actor.SetOrigin(b[1], 0.5 * (b[2] + b[3]), 0.5 * (b[4] + b[5]))

    # Scene setup
    def setup_camera(self):
        cam = self.ren.GetActiveCamera()
        cam.SetPosition(0, -1.5, 0)
        cam.SetFocalPoint(0, 0, 0)
        cam.SetViewUp(0, 0, 1)
        cam.SetParallelProjection(True)
        self.ren.ResetCamera()

    # Force Arrows
    def shift_arrow_to_x_minus1(self, arrow_source):
        arrow_source.Update()
        arrow_poly = arrow_source.GetOutput()

        shift_tf = vtk.vtkTransform()
        shift_tf.Translate(-2.0, 0.0, 0.0)

        shift_filter = vtk.vtkTransformPolyDataFilter()
        shift_filter.SetTransform(shift_tf)
        shift_filter.SetInputData(arrow_poly)
        shift_filter.Update()
        return shift_filter.GetOutput()

    def create_force_arrows(self):
        # Green arrow (tibial tendon force)
        a_src_g = vtk.vtkArrowSource()
        mapper_g = vtk.vtkPolyDataMapper()
        mapper_g.SetInputData(self.shift_arrow_to_x_minus1(a_src_g))

        self.arrow_actor_tibia = vtk.vtkActor()
        self.arrow_actor_tibia.SetMapper(mapper_g)
        self.arrow_actor_tibia.GetProperty().SetColor(0, 1, 0)
        self.arrow_actor_tibia.SetOrigin(-1, 0, 0)
        self.ren.AddActor(self.arrow_actor_tibia)

        # Red arrow (external weight)
        a_src_r = vtk.vtkArrowSource()
        mapper_r = vtk.vtkPolyDataMapper()
        mapper_r.SetInputData(self.shift_arrow_to_x_minus1(a_src_r))

        self.arrow_actor_ankle = vtk.vtkActor()
        self.arrow_actor_ankle.SetMapper(mapper_r)
        self.arrow_actor_ankle.GetProperty().SetColor(1, 0, 0)
        self.arrow_actor_ankle.SetOrigin(-1, 0, 0)
        self.ren.AddActor(self.arrow_actor_ankle)

    # Physics formulas
    def update_simulation(self):
        mass       = self.get_slider_value(self.massSlider)
        massW_kg   = self.get_exercise_weight_kg()
        angle_val  = self.get_slider_value(self.angle_slider)
        shin_len   = self.get_slider_value(self.shin_length)
        angle_t    = self.get_slider_value(self.angle_t)

        Fg    = mass    * 9.81
        Fe    = massW_kg * 9.81
        angle = 90.0 - angle_val  # knee flexion (deg)

        self.Fg_label.setText(f"{Fg:.2f} N (from {mass:.2f} kg)")
        self.Fe_label.setText(f"{Fe:.2f} N (from {massW_kg:.2f} kg)")
        self.angle_label.setText(f"{angle:.2f} deg")
        self.length_label.setText(f"{shin_len:.2f} m")
        self.angle_t_label.setText(f"{angle_t:.2f} deg")

        angle_rad    = math.radians(angle)
        angle_t2_rad = math.radians(angle_t)
        r_t = shin_len
        r_g = shin_len / 3.0
        r_e = shin_len
        denom = (r_t * math.sin(angle_t2_rad)) or 1e-9

        Ft   = ((r_e * math.sin(angle_rad)) / denom) * Fe \
             + ((r_g * Fg * math.sin(angle_rad)) / denom)
        t_net = (r_t * Ft * math.sin(angle_t2_rad)
                 - r_g * Fg * math.sin(angle_rad)
                 - r_e * Fe * math.sin(angle_rad))

        self.Ft_label.setText(f"{Ft:.2f} N")
        self.t_net_label.setText(f"{t_net:.2f} N m")

        # Rotate shin
        if self.shin_actor:
            self.shin_actor.SetOrientation(0, -angle_val, 0)

        # Re-position force arrows
        if self.shin_actor:
            knee_x, knee_y, knee_z = self.shin_actor.GetOrigin()

            # Green arrow (tibial tendon)
            tform_g = vtk.vtkTransform()
            tform_g.Translate(knee_x - 1.0, knee_y, knee_z - 1.5)
            tform_g.RotateY(90)
            scale_g = 0.01 * abs(Ft)
            tform_g.Scale(scale_g, scale_g, scale_g)
            self.arrow_actor_tibia.SetUserTransform(tform_g)

            # Red arrow (external weight)
            tform_r = vtk.vtkTransform()
            tform_r.Translate(knee_x - 2.5, knee_y, knee_z - .5)
            tform_r.RotateY(90)
            scale_r = max(0.016 * abs(Fe), 0.05)
            tform_r.Scale(scale_r, scale_r, scale_r)
            self.arrow_actor_ankle.SetUserTransform(tform_r)

        self.vtk_widget.GetRenderWindow().Render()


# QApplication define
def main():
    app = QApplication(sys.argv)

    # macOS: use Fusion style so sliders repaint reliably (Windows unaffected)
    if sys.platform == "darwin":
        app.setStyle(QStyleFactory.create("Fusion"))

    # Global font size
    font = QFont()
    font.setPointSize(14)
    app.setFont(font)

    w = LegSimulation()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
