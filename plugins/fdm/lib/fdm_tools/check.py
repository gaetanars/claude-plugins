"""Export + verify a build123d part for FDM printing (build volume from the fdm profiles).

Usage from a part script, run with fdm-run:
    from fdm_tools import check
    check(part, "out/my_part")
"""

import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from build123d import export_step, export_stl
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

VIEWS = {"iso": (30, -60), "front": (0, -90), "right": (0, 0), "top": (90, -90)}

RESULTS = []  # issues list of each check() call, read by fdm_tools.run


def _printer():
    """Return (build volume, machine name, filament density, filament type) from $FDM_DATA/profiles."""
    data = os.environ.get("FDM_DATA")
    if not data:
        sys.exit("erreur : FDM_DATA absent, lancer la pièce avec fdm-run")
    machine_path = Path(data) / "profiles" / "machine.json"
    filament_path = Path(data) / "profiles" / "filament.json"
    path = machine_path
    try:
        machine = json.loads(machine_path.read_text())
        points = [[float(v) for v in p.split("x")] for p in machine["printable_area"]]
        width = max(p[0] for p in points) - min(p[0] for p in points)
        depth = max(p[1] for p in points) - min(p[1] for p in points)
        height = float(machine["printable_height"])
        name = machine.get("name", "?")
        path = filament_path
        filament = json.loads(filament_path.read_text())
        density = float(filament["filament_density"][0])
        kind = str(filament["filament_type"][0])
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as e:
        sys.exit(f"erreur : profil illisible {path} ({e}), relancer fdm-profiles")
    return (width, depth, height), name, density, kind


def render(mesh: trimesh.Trimesh, png: Path) -> None:
    fig = plt.figure(figsize=(12, 3.4))
    lo, hi = mesh.bounds
    center, half = (lo + hi) / 2, (hi - lo).max() / 2
    light = np.array([0.4, -0.5, 0.8]) / np.linalg.norm([0.4, -0.5, 0.8])
    shade = 0.35 + 0.65 * np.clip(mesh.face_normals @ light, 0, 1)
    colors = np.c_[0.2 * shade, 0.5 * shade, 0.9 * shade, np.ones_like(shade)]
    for i, (name, (elev, azim)) in enumerate(VIEWS.items(), 1):
        ax = fig.add_subplot(1, 4, i, projection="3d")
        ax.add_collection3d(Poly3DCollection(mesh.triangles, facecolors=colors, linewidths=0))
        for setter, c in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), center):
            setter(c - half, c + half)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(name)
        ax.set_xlabel("X"), ax.set_ylabel("Y"), ax.set_zlabel("Z")
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    plt.close(fig)


def check(part, out: str) -> trimesh.Trimesh:
    volume, machine, density, filament = _printer()
    base = Path(out)
    try:
        base.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.exit(f"erreur : création de {base.parent} impossible : {e}")
    step, stl, png = base.with_suffix(".step"), base.with_suffix(".stl"), base.with_suffix(".png")

    export_step(part, str(step))
    export_stl(part, str(stl), tolerance=0.01, angular_tolerance=0.1)
    mesh = trimesh.load_mesh(stl)

    size = mesh.extents
    issues = []
    if not mesh.is_watertight:
        issues.append("mesh is not watertight")
    if not mesh.is_winding_consistent:
        issues.append("inconsistent face winding")
    if mesh.volume <= 0:
        issues.append("non-positive volume (inverted normals?)")
    if any(s > m for s, m in zip(size, volume)):
        issues.append(f"exceeds build volume {volume[0]:g} × {volume[1]:g} × {volume[2]:g} mm ({machine})")
    if abs(mesh.bounds[0][2]) > 1e-3:
        issues.append(f"part does not sit on Z=0 (min Z = {mesh.bounds[0][2]:.3f})")

    # Overhang ratio: downward faces steeper than 45° not on the bed
    down = mesh.face_normals[:, 2] < -np.cos(np.radians(45))
    on_bed = mesh.triangles_center[:, 2] < 1e-3
    overhang_area = mesh.area_faces[down & ~on_bed].sum()

    render(mesh, png)

    print(f"--- {base.name} ---")
    print(f"size (X×Y×Z): {size[0]:.2f} × {size[1]:.2f} × {size[2]:.2f} mm")
    print(f"volume: {mesh.volume / 1000:.2f} cm³  (~{mesh.volume / 1000 * density:.1f} g {filament} if solid)")
    print(f"overhangs >45° needing support: {overhang_area:.1f} mm²")
    print(f"files: {step.name}, {stl.name}, {png.name}")
    print("OK" if not issues else "ISSUES:\n  - " + "\n  - ".join(issues))
    RESULTS.append(issues)
    return mesh
