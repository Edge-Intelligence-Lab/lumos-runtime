"""MuJoCo workbench for the LumosTouch V3."""

import gzip
import hashlib
from importlib.resources import files
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen
import xml.etree.ElementTree as ET


RESOURCES = files(__package__)


def default_mesh_directory() -> Path:
    cache_root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return cache_root / "lumos-runtime" / "touch-v3" / "meshes"


def _mesh_manifest() -> dict:
    return json.loads(RESOURCES.joinpath("meshes.json").read_text(encoding="utf-8"))["meshes"]


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fetch_meshes(directory: Path) -> None:
    """Cache the published visual assets, verifying them before replacement."""
    directory.mkdir(parents=True, exist_ok=True)
    for name, entry in _mesh_manifest().items():
        target = directory / name
        if target.is_file() and _digest(target.read_bytes()) == entry["sha256"]:
            continue
        with urlopen(entry["url"], timeout=30) as response:
            content = gzip.decompress(response.read())
        if _digest(content) != entry["sha256"]:
            raise ValueError(f"Checksum mismatch for {name}")
        # Write beside the destination so replacement is atomic on this filesystem.
        pending = NamedTemporaryFile(dir=directory, delete=False)
        temporary_path = Path(pending.name)
        try:
            with pending:
                pending.write(content)
            temporary_path.replace(target)
        finally:
            temporary_path.unlink(missing_ok=True)


def _vector(data: dict, name: str, length: int) -> tuple[float, ...]:
    values = data[name]
    if not isinstance(values, list) or len(values) != length:
        raise ValueError(f"{name} must contain {length} numbers")
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
        raise ValueError(f"{name} must contain finite numbers")
    return tuple(values)


def _configure_wrist_camera(scene: ET.Element, robot: ET.Element, path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        width, height = _vector(data, "resolution", 2)
        fx, fy, cx, cy = _vector(data, "intrinsics", 4)
        position = _vector(data, "position_m", 3)
        quaternion = _vector(data, "quaternion_wxyz", 4)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid wrist calibration in {path}: {error}") from error
    if type(width) is not int or type(height) is not int or min(width, height, fx, fy) <= 0:
        raise ValueError("Wrist calibration requires integer image dimensions and positive focal lengths")
    norm = math.hypot(*quaternion)
    if not math.isclose(norm, 1.0, abs_tol=0.001):
        raise ValueError("Wrist calibration quaternion must have unit length")

    # OpenCV optical axes (right, down, forward) -> MuJoCo (right, up, back).
    w, x, y, z = (value / norm for value in quaternion)
    camera = robot.find(".//camera[@name='wrist']")
    camera.attrib.pop("xyaxes")
    camera.attrib.pop("fovy")
    camera.set("pos", " ".join(map(str, position)))
    camera.set("quat", f"{-x} {w} {z} {-y}")
    camera.set("resolution", f"{width} {height}")
    camera.set("sensorsize", f"{width * 1e-5} {height * 1e-5}")
    camera.set("focalpixel", f"{fx} {fy}")
    camera.set("principalpixel", f"{width / 2 - cx} {height / 2 - cy}")
    framebuffer = scene.find("visual/global")
    framebuffer.set("offwidth", str(max(width, int(framebuffer.get("offwidth")))))
    framebuffer.set("offheight", str(max(height, int(framebuffer.get("offheight")))))


def load_workbench(mesh_directory: Path | None = None, wrist_calibration: Path | None = None):
    """Return a MuJoCo model and data initialized in the workbench preview pose."""
    import mujoco

    directory = mesh_directory if mesh_directory is not None else default_mesh_directory()
    assets = {}
    for name, entry in _mesh_manifest().items():
        path = directory / name
        if not path.is_file():
            raise ValueError(f"Missing {path}. Run lumos-runtime sim-assets first.")
        content = path.read_bytes()
        if _digest(content) != entry["sha256"]:
            raise ValueError(f"Checksum mismatch for {path}. Run lumos-runtime sim-assets to refresh it.")
        assets[name] = content

    robot = ET.fromstring(RESOURCES.joinpath("touch_v3.xml").read_bytes())
    scene = ET.fromstring(RESOURCES.joinpath("workbench.xml").read_bytes())
    if wrist_calibration is not None:
        _configure_wrist_camera(scene, robot, wrist_calibration)
    assets["touch_v3.xml"] = ET.tostring(robot)
    model = mujoco.MjModel.from_xml_string(ET.tostring(scene, encoding="unicode"), assets)
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("preview").id)
    mujoco.mj_forward(model, data)
    return model, data
