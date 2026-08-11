#!/usr/bin/env python3
"""Rebuild the Rev C routing from its reviewed Specctra session and repairs.

The autorouter receives a zone-free copy so every electrical net is explicitly
connected by copper before planes are restored. Freerouting is constrained to
one optimization thread because its 1.9.0 multi-thread optimizer is known to
create clearance violations.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
BOARD = HERE / "skysweep32_rev_c.kicad_pcb"
ROUTING_BOARD = HERE / "routing_input.kicad_pcb"
DSN = HERE / "routing_input.dsn"
SES = HERE / "reviewed_routing.ses"


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def net(board: pcbnew.BOARD, name: str) -> pcbnew.NETINFO_ITEM:
    value = board.FindNet(name)
    if value is None:
        raise ValueError(f"net not found: {name}")
    return value


def add_track(
    board: pcbnew.BOARD,
    net_item: pcbnew.NETINFO_ITEM,
    start: tuple[float, float],
    end: tuple[float, float],
    width: float,
    layer: int = pcbnew.F_Cu,
) -> None:
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(point(*start))
    track.SetEnd(point(*end))
    track.SetWidth(mm(width))
    track.SetLayer(layer)
    track.SetNet(net_item)
    board.Add(track)


def add_path(
    board: pcbnew.BOARD,
    net_name: str,
    points: list[tuple[float, float]],
    width: float,
    layer: int = pcbnew.F_Cu,
) -> None:
    net_item = net(board, net_name)
    for start, end in zip(points, points[1:]):
        add_track(board, net_item, start, end, width, layer)


def add_via(
    board: pcbnew.BOARD,
    net_name: str,
    position: tuple[float, float],
    diameter: float = 1.0,
    drill: float = 0.5,
) -> None:
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(point(*position))
    via.SetWidth(mm(diameter))
    via.SetDrill(mm(drill))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(net(board, net_name))
    board.Add(via)


def pad_has_copper_peer(board: pcbnew.BOARD, reference: str, number: str) -> bool:
    footprint = board.FindFootprintByReference(reference)
    if footprint is None:
        raise ValueError(f"footprint not found: {reference}")
    matches = [pad for pad in footprint.Pads() if pad.GetNumber() == number]
    if not matches:
        raise ValueError(f"pad not found: {reference}.{number}")
    board.BuildConnectivity()
    connected = board.GetConnectivity().GetConnectedPads(matches[0])
    return any(pad.GetNetCode() == matches[0].GetNetCode() for pad in connected if pad != matches[0])


def apply_reviewed_repairs(board: pcbnew.BOARD) -> None:
    gps_supply_open = not pad_has_copper_peer(board, "GPS1", "17")
    buck_bootstrap_open = not pad_has_copper_peer(board, "U3", "6")
    # Replace the autorouted CC2 path with a serviceable two-layer escape above
    # the data-pin fanout. CC2 is static configuration, not USB data.
    for track in list(board.GetTracks()):
        local_rf_ground = (
            track.GetNetname() == "GND"
            and max(track.GetStart().x, track.GetEnd().x) <= mm(9.0)
            and mm(42.0) <= min(track.GetStart().y, track.GetEnd().y)
            and max(track.GetStart().y, track.GetEnd().y) <= mm(47.0)
        )
        if track.GetNetname() in {"USB_CC2", "SUBGHZ_ANT"} or local_rf_ground:
            board.Remove(track)
    add_path(board, "USB_CC2", [(21.75, 77.645), (21.75, 79.0)], 0.2)
    add_via(board, "USB_CC2", (21.75, 79.0), 0.6, 0.3)
    add_path(
        board,
        "USB_CC2",
        [
            (21.75, 79.0),
            (23.0, 80.5),
            (25.6, 80.5),
            (31.175, 77.2),
        ],
        0.25,
        pcbnew.B_Cu,
    )
    add_via(board, "USB_CC2", (31.175, 77.2), 0.6, 0.3)
    add_path(board, "USB_CC2", [(31.175, 77.2), (31.175, 78.0)], 0.25)

    # Two dense-module escapes may be left open depending on route ordering.
    if gps_supply_open:
        add_path(board, "3V3", [(18.9, 26.125), (18.9, 27.1)], 0.25)
        add_via(board, "3V3", (18.9, 27.1), 0.6, 0.3)
    if buck_bootstrap_open:
        add_path(
            board,
            "BUCK_BST",
            [(48.1375, 68.05), (49.0, 67.1875), (49.0, 65.225), (50.225, 64.0)],
            0.25,
        )

    # AP63203 feedback pin: short Kelvin escape to the continuous 3V3 plane.
    # This avoids the adjacent switch-node routing and carries negligible load.
    add_path(board, "3V3", [(45.8625, 68.05), (45.8625, 66.0)], 0.25)
    add_via(board, "3V3", (45.8625, 66.0), 0.9, 0.4)

    # AP63203 switch pin requires a fine-pitch neck before widening into the
    # bootstrap/switch branch and inductor input.
    add_path(board, "BUCK_SW", [(48.1375, 69.0), (49.2, 69.0)], 0.25)
    add_path(
        board,
        "BUCK_SW",
        [(49.2, 69.0), (51.775, 66.425), (51.775, 64.0)],
        0.8,
    )

    # USB4105 duplicates VBUS on two fine-pitch pad groups. Neck down only for
    # connector escape, then join both groups on B.Cu before the resettable fuse.
    add_path(board, "VBUS_RAW", [(17.6, 77.645), (17.6, 75.7)], 0.2)
    add_via(board, "VBUS_RAW", (17.6, 75.7), 0.9, 0.4)
    # CC2 was rerouted above, leaving a straight fine-pitch escape.
    add_path(board, "VBUS_RAW", [(22.4, 77.645), (22.4, 76.6)], 0.2)
    add_via(board, "VBUS_RAW", (22.4, 76.6), 0.6, 0.3)
    add_via(board, "VBUS_RAW", (31.0, 73.3))
    add_path(
        board,
        "VBUS_RAW",
        [(17.6, 75.7), (20.0, 73.3), (31.0, 73.3)],
        0.8,
        pcbnew.B_Cu,
    )
    add_path(
        board,
        "VBUS_RAW",
        [(22.4, 76.6), (20.0, 73.3)],
        0.8,
        pcbnew.B_Cu,
    )
    add_path(board, "VBUS_RAW", [(31.0, 73.3), (33.0, 74.1375)], 0.8)

    # E07-900M10S pin 21 is the 50-ohm RF port. The short edge launch uses the
    # reviewed 0.30 mm nominal microstrip for the declared 0.18 mm prepreg.
    add_path(board, "GND", [(8.25, 43.0), (9.0, 43.0)], 0.25)
    add_via(board, "GND", (9.0, 43.0), 0.6, 0.3)
    add_path(board, "GND", [(8.25, 45.54), (9.0, 45.54)], 0.25)
    add_via(board, "GND", (9.0, 45.54), 0.6, 0.3)
    add_path(board, "SUBGHZ_ANT", [(2.55, 44.27), (8.25, 44.27)], 0.30)


def remove_zones(board: pcbnew.BOARD) -> None:
    for zone in list(board.Zones()):
        board.Remove(zone)

def prepare_routing_input() -> None:
    routing = pcbnew.LoadBoard(str(BOARD))
    remove_zones(routing)
    pcbnew.SaveBoard(str(ROUTING_BOARD), routing)
    if not pcbnew.ExportSpecctraDSN(routing, str(DSN)):
        raise RuntimeError("KiCad failed to export the Specctra DSN")



def route(router: Path, max_passes: int, reroute: bool) -> None:
    subprocess.run(
        [sys.executable, str(HERE / "generate_pcb.py"), "--placed-only"],
        cwd=HERE,
        check=True,
    )
    # Zone removal is isolated because KiCad 10's SWIG wrapper invalidates
    # unrelated board iterators after deleting ZONE objects in-process.
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--prepare-routing-input"],
        cwd=HERE,
        check=True,
    )

    if reroute:
        subprocess.run(
            [
                "java",
                "-jar",
                str(router),
                "-de",
                str(DSN),
                "-do",
                str(SES),
                "-mp",
                str(max_passes),
                "-mt",
                "1",
            ],
            cwd=HERE,
            check=True,
        )
    elif not SES.is_file():
        raise RuntimeError("routing session missing; use --reroute to create it")
    base = pcbnew.LoadBoard(str(BOARD))
    if not pcbnew.ImportSpecctraSES(base, str(SES)):
        raise RuntimeError("KiCad failed to import the Specctra session")
    apply_reviewed_repairs(base)
    pcbnew.SaveBoard(str(BOARD), base)
    print(f"[OK] Wrote routed board: {BOARD}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--router",
        type=Path,
        default=Path(os.environ.get("FREEROUTING_JAR", HERE.parents[1] / ".cache" / "hardware" / "freerouting-1.9.0.jar")),
        help="path to Freerouting 1.9.0 pinned by hardware/toolchain.json",
    )
    parser.add_argument("--max-passes", type=int, default=100)
    parser.add_argument(
        "--reroute",
        action="store_true",
        help="replace the reviewed session with a fresh single-thread Freerouting run",
    )
    parser.add_argument("--prepare-routing-input", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.prepare_routing_input:
        prepare_routing_input()
        return 0
    if args.reroute and not args.router.is_file():
        raise SystemExit(f"router not found: {args.router}; run python scripts/fetch_hardware_tools.py")
    route(args.router.resolve(), args.max_passes, args.reroute)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
