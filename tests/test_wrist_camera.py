import importlib.util
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import xml.etree.ElementTree as ET

from lumos_runtime.simulation import _configure_wrist_camera


@unittest.skipUnless(importlib.util.find_spec("mujoco") and os.environ.get("MUJOCO_GL"),
                     "requires the simulation extra and a headless GL backend")
class WristProjectionTest(unittest.TestCase):
    def test_optical_axis_projects_to_off_center_principal_point(self):
        import mujoco
        import numpy as np

        scene = ET.fromstring(
            "<mujoco><visual><global offwidth='640' offheight='480'/></visual></mujoco>"
        )
        robot = ET.SubElement(scene, "worldbody")
        ET.SubElement(robot, "camera", name="wrist", xyaxes="1 0 0 0 1 0", fovy="45")
        ET.SubElement(robot, "geom", type="sphere", pos="0 0 1", size="0.03", rgba="1 0 0 1")
        with TemporaryDirectory() as directory:
            calibration = Path(directory) / "wrist.json"
            calibration.write_text(json.dumps({
                "resolution": [640, 480],
                "intrinsics": [510, 520, 280, 275],
                "position_m": [0, 0, 0],
                "quaternion_wxyz": [1, 0, 0, 0],
            }), encoding="utf-8")
            _configure_wrist_camera(scene, robot, calibration)
        model = mujoco.MjModel.from_xml_string(ET.tostring(scene, encoding="unicode"))
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        with mujoco.Renderer(model, height=480, width=640) as renderer:
            renderer.update_scene(data, camera="wrist")
            rgb = renderer.render()
        rows, cols = np.nonzero((rgb[:, :, 0] > 100) & (rgb[:, :, 1] < 20) & (rgb[:, :, 2] < 20))
        np.testing.assert_allclose([cols.mean(), rows.mean()], [280, 275], atol=1.0)
