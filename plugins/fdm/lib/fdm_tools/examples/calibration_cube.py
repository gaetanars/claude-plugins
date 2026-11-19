"""20 mm calibration cube with a 5 mm through-hole — validates the toolchain."""

from build123d import Align, Box, Cylinder, Mode, BuildPart, chamfer, Axis

from fdm_tools import check

SIZE = 20.0
HOLE_D = 5.0

with BuildPart() as cube:
    Box(SIZE, SIZE, SIZE, align=(Align.CENTER, Align.CENTER, Align.MIN))
    Cylinder(HOLE_D / 2, SIZE, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
    chamfer(cube.edges().group_by(Axis.Z)[-1], 1.0)  # top edges only, keeps the first layer sharp

check(cube.part, "out/calibration_cube")
