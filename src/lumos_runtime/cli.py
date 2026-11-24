"""Command-line entry points for Lumos Runtime."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .inspection import inspect_host


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lumos-runtime")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect", help="List host-visible device candidates without opening them")
    asset_command = commands.add_parser("sim-assets", help="Download and verify the simulation visual meshes")
    simulation = commands.add_parser("simulate", help="Run the MuJoCo workbench")
    calibration = commands.add_parser("calibrate-wrist", help="Fit wrist calibration from paired captures offline")
    calibration.add_argument("session", type=Path, help="Calibration session JSON")
    calibration.add_argument("output", type=Path, help="New calibration JSON for simulate --wrist-calibration")
    for command in (asset_command, simulation, calibration):
        command.add_argument("--assets-dir", type=Path, help="Directory containing the nine visual STL files")
    simulation.add_argument("--steps", type=int, default=0, help="Physics steps to run before viewing or rendering")
    simulation.add_argument("--web", action="store_true", help="Open a MuJoCo Studio WebViewer server")
    simulation.add_argument("--port", type=int, default=8080, help="Studio WebViewer port")
    simulation.add_argument("--wrist-calibration", type=Path, help="Rectified wrist camera calibration JSON")
    simulation.add_argument("--wrist-image", type=Path, help="Save an RGB frame from the wrist camera")
    args = parser.parse_args(argv)

    if args.command == "inspect":
        print(json.dumps(asdict(inspect_host()), indent=2))
        return 0

    try:
        if args.command == "sim-assets":
            from .simulation import default_mesh_directory, fetch_meshes

            directory = args.assets_dir if args.assets_dir is not None else default_mesh_directory()
            fetch_meshes(directory)
            print(directory)
        elif args.command == "calibrate-wrist":
            from .wrist_calibration import calibrate

            calibrate(args.session, args.output, args.assets_dir)
        else:
            from .simulation.commands import simulate

            simulate(args)
    except ModuleNotFoundError as error:
        install = (
            "Install both the Lumos simulation and OpenArm calibration extras with Python 3.12."
            if args.command == "calibrate-wrist"
            else "Install lumos-runtime[simulation] with Python 3.11 or newer."
        )
        parser.exit(1, f"{error}. {install}\n")
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
