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


def remove_track(
    board: pcbnew.BOARD,
    net_name: str,
    start: tuple[float, float],
    end: tuple[float, float],
) -> None:
    """Remove one exact router segment before replacing its topology."""
    start_point, end_point = point(*start), point(*end)
    matches = [
        item for item in board.GetTracks()
        if not isinstance(item, pcbnew.PCB_VIA)
        and item.GetNetname() == net_name
        and (
            (item.GetStart() == start_point and item.GetEnd() == end_point)
            or (item.GetStart() == end_point and item.GetEnd() == start_point)
        )
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one {net_name} track {start}->{end}, found {len(matches)}"
        )
    board.Remove(matches[0])


def apply_reviewed_repairs(board: pcbnew.BOARD) -> None:
    """Repair the small set of deterministic pin-escape opens left by Freerouting."""
    # AP63203 VOUT pads 2 and 3 are intentionally common; the router reaches
    # pad 3, so bridge the 0.35 mm package gap at lead width.
    add_path(board, "SYS_5V", [(77.8625, 69.0), (77.8625, 69.95)], 0.4)

    # TPS61232 VOUT pads 4 and 7 sit on opposite sides of the exposed GND pad.
    # Escape to B.Cu at lead width, then route around the thermal land.
    add_path(board, "SYS_5V", [(53.475, 69.5), (54.5, 69.5)], 0.28)
    add_path(board, "SYS_5V", [(50.24, 69.5), (49.5, 69.5)], 0.28)
    add_via(board, "SYS_5V", (54.5, 69.5), 0.7, 0.3)
    add_via(board, "SYS_5V", (49.5, 69.5), 0.7, 0.3)
    add_path(
        board, "SYS_5V",
        [(54.5, 69.5), (54.5, 71.6), (49.5, 71.6), (49.5, 69.5)],
        0.6, pcbnew.B_Cu,
    )

    # The router wraps U6 GND pads 1/4 around its left edge, trapping BAT pads
    # 2/3. Replace that GND loop with two plane vias and leave a valid BAT exit.
    remove_track(board, "GND", (13.0, 70.25), (12.5632, 70.25))
    remove_track(board, "GND", (12.5632, 70.25), (12.2786, 70.5346))
    remove_track(board, "GND", (12.2786, 70.5346), (12.2786, 71.4694))
    remove_track(board, "GND", (12.2786, 71.4694), (12.5592, 71.75))
    # Join GND pads 1/4 directly to the exposed GND land. Their 0.25 mm traces
    # overlap the thermal pad by 0.025 mm without entering the BAT escape rows.
    add_path(board, "GND", [(13.0, 70.25), (14.0, 70.25)], 0.25)
    add_path(board, "GND", [(13.0, 71.75), (14.0, 71.75)], 0.25)
    add_path(
        board, "BAT_CELL",
        [(13.0, 70.75), (11.5, 70.75), (11.5, 70.2127), (11.5315, 70.2127)],
        0.25,
    )

    # Escape both USB-C VBUS pad groups toward the connector body, change to
    # B.Cu, pass between the upper/lower shell stakes, then return beside F1.
    for pad_x, via_x in ((32.6, 33.2), (37.4, 36.8)):
        add_path(
            board, "VBUS_RAW",
            [(pad_x, 87.645), (pad_x, 88.2), (via_x, 89.1)],
            0.3,
        )
        add_via(board, "VBUS_RAW", (via_x, 89.1), 0.8, 0.35)
        add_path(board, "VBUS_RAW", [(via_x, 89.1), (via_x, 90.3)], 0.5, pcbnew.B_Cu)
    add_path(board, "VBUS_RAW", [(33.2, 90.3), (42.0, 90.3), (42.0, 86.1375)], 0.8, pcbnew.B_Cu)
    add_via(board, "VBUS_RAW", (42.0, 86.1375), 0.8, 0.35)
    add_path(board, "VBUS_RAW", [(42.0, 86.1375), (43.0, 86.1375)], 0.8)
    # Terminate residual router GND branches and both SAM-M10Q ground sides on
    # the continuous In1.Cu reference plane.
    for position in ((91.9595, 76.5193), (90.825, 80.1875)):
        add_via(board, "GND", position, 0.8, 0.35)
    add_path(board, "GND", [(14.2, 10.875), (13.3, 10.875)], 0.5)
    add_path(board, "GND", [(21.8, 10.875), (22.7, 10.875)], 0.5)
    add_via(board, "GND", (13.3, 10.875), 0.8, 0.35)
    add_via(board, "GND", (22.7, 10.875), 0.8, 0.35)

    for zone in board.Zones():
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.BuildConnectivity()


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
