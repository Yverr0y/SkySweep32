#!/usr/bin/env python3
"""Render high-resolution 3D CAD preview images for Sentinel Enclosure Rev B."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
ENC_DIR = HERE / "enclosures"
OUT_DIR = HERE / "previews"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def render_stl_mesh(mesh: trimesh.Trimesh, out_path: Path, title: str,
                    elev: float = 30, azim: float = -45, color: str = "#446688") -> None:
    fig = plt.figure(figsize=(12, 9), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#1e1e1e")
    fig.patch.set_facecolor("#1e1e1e")

    # Sample faces for smooth shading
    faces = mesh.faces
    vertices = mesh.vertices

    poly3d = Poly3DCollection(
        vertices[faces],
        alpha=0.9,
        facecolors=color,
        edgecolors="#223344",
        linewidths=0.1,
    )
    ax.add_collection3d(poly3d)

    # Auto-scale axes
    min_b, max_b = mesh.bounds[0], mesh.bounds[1]
    ax.set_xlim(min_b[0], max_b[0])
    ax.set_ylim(min_b[1], max_b[1])
    ax.set_zlim(min_b[2], max_b[2])

    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    plt.title(title, color="#ffffff", fontsize=14, pad=20)
    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"[OK] Rendered enclosure preview: {out_path} ({out_path.stat().st_size} bytes)")


def render_all_previews() -> None:
    bottom_mesh = trimesh.load(str(ENC_DIR / "skysweep32_pro_case_bottom_rev_b.stl"))
    lid_mesh = trimesh.load(str(ENC_DIR / "skysweep32_pro_case_lid_rev_b.stl"))

    # 1. Assembled Enclosure (Bottom + Lid)
    assembled = trimesh.util.concatenate([bottom_mesh, lid_mesh])
    render_stl_mesh(assembled, OUT_DIR / "preview_enclosure_iso.png",
                    "Sentinel Enclosure Rev B — Assembled 3D CAD View",
                    elev=35, azim=-55, color="#3a6073")

    # 2. Interior Bottom Case View
    render_stl_mesh(bottom_mesh, OUT_DIR / "preview_enclosure_interior.png",
                    "Sentinel Enclosure Rev B — Interior Case & Bosses View",
                    elev=50, azim=-45, color="#4a7083")


if __name__ == "__main__":
    render_all_previews()
