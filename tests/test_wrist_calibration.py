import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lumos_runtime.simulation import default_mesh_directory, load_workbench
from lumos_runtime.wrist_calibration import calibrate


@unittest.skipUnless(
    importlib.util.find_spec("mujoco")
    and importlib.util.find_spec("openarm_runtime")
    and importlib.util.find_spec("cv2")
    and importlib.util.find_spec("scipy")
    and len(list(default_mesh_directory().glob("*.STL"))) >= 9,
    "requires the simulation and OpenArm calibration extras and the workbench meshes",
)
class WristCalibrationTest(unittest.TestCase):
    def test_estimate_uses_camera_in_gripper_frame_and_preserves_held_out_views(self):
        import cv2
        import mujoco
        import numpy as np

        board_spec = {
            "type": "charuco", "squares_x": 6, "squares_y": 4, "square_size_m": 0.0225,
            "marker_size_m": 0.0165, "dictionary": "DICT_4X4_50",
        }
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        board = cv2.aruco.CharucoBoard((6, 4), 0.0225, 0.0165, dictionary)
        texture = board.generateImage((840, 560), marginSize=0)
        camera_matrix = np.array([[515, 0, 311], [0, 520, 245], [0, 0, 1]], dtype=float)
        model, data = load_workbench()
        initial = data.qpos[:6].copy()

        def gripper_in_base(angles):
            data.qpos[:6] = angles
            mujoco.mj_forward(model, data)
            gripper = data.body("gripper_base")
            transform = np.eye(4)
            transform[:3, :3] = gripper.xmat.reshape(3, 3)
            transform[:3, 3] = gripper.xpos
            return transform

        camera_in_gripper = np.eye(4)
        camera_in_gripper[:3, :3] = cv2.Rodrigues(np.array([0.2, -0.18, 0.17]))[0]
        camera_in_gripper[:3, 3] = [0.07, 0.01, 0.055]
        board_in_initial_camera = np.eye(4)
        board_in_initial_camera[:3, 3] = [-0.0675, -0.045, 0.32]
        board_in_base = gripper_in_base(initial) @ camera_in_gripper @ board_in_initial_camera
        board_corners = np.array([[0, 0, 0], [0.135, 0, 0], [0.135, 0.09, 0], [0, 0.09, 0]])
        texture_corners = np.float32([[0, 0], [840, 0], [840, 560], [0, 560]])
        generator = np.random.default_rng(22)
        samples = []
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for _ in range(1000):
                angles = initial + generator.uniform(-0.38, 0.38, 6)
                board_pose = np.linalg.inv(gripper_in_base(angles) @ camera_in_gripper) @ board_in_base
                rotation = cv2.Rodrigues(board_pose[:3, :3])[0]
                corners = cv2.projectPoints(board_corners, rotation, board_pose[:3, 3], camera_matrix, None)[0]
                corners = corners.reshape(4, 2)
                if board_pose[2, 3] < 0.23 or np.any(corners < [15, 15]) or np.any(corners > [625, 465]):
                    continue
                warp = cv2.getPerspectiveTransform(texture_corners, corners.astype(np.float32))
                image = cv2.warpPerspective(texture, warp, (640, 480), borderValue=245)
                index = len(samples)
                name = f"frame-{index:02}.png"
                self.assertTrue(cv2.imwrite(str(root / name), image))
                samples.append({
                    "image": name, "joints_rad": angles.tolist(),
                    "image_captured_at_s": float(index), "robot_received_at_s": index + 0.01,
                    "role": "fit" if index < 16 else "validation",
                })
                if len(samples) == 20:
                    break
            self.assertEqual(len(samples), 20)
            session = root / "session.json"
            session.write_text(json.dumps({
                "board": board_spec, "joint_state_source": "measured_feedback", "samples": samples,
            }), encoding="utf-8")
            output = root / "wrist.json"
            calibrate(session, output)
            report = json.loads(output.read_text(encoding="utf-8"))
            np.testing.assert_allclose(report["position_m"], camera_in_gripper[:3, 3], atol=0.005)
            estimated = np.asarray(report["hand_eye_estimate"]["transform"])
            rotation_error = cv2.Rodrigues(estimated[:3, :3].T @ camera_in_gripper[:3, :3])[0]
            self.assertLess(np.linalg.norm(rotation_error), 0.03)
            self.assertEqual(len(report["image_sha256"]), 20)
            self.assertEqual(report["hand_eye_estimate"]["samples"], 16)
            self.assertEqual(len(report["held_out"]["per_image"]), 4)
            calibrated_model, _ = load_workbench(wrist_calibration=output)
            self.assertEqual(calibrated_model.cam_resolution[calibrated_model.camera("wrist").id].tolist(),
                             [640, 480])
