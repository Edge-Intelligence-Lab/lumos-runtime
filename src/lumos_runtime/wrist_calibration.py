"""Offline eye-in-hand calibration from X5 wrist images and paired joint feedback."""

import hashlib
import json
from pathlib import Path


def calibrate(session_path: Path, output: Path, mesh_directory: Path | None = None) -> None:
    import cv2
    import mujoco
    import numpy as np
    from openarm_runtime import camera_calibration, camera_intrinsics
    from scipy.spatial.transform import Rotation

    from .simulation import RESOURCES, load_workbench

    raw = session_path.read_bytes()
    session = json.loads(raw)
    if session.get("joint_state_source") != "measured_feedback":
        raise ValueError("Use measured follower joint feedback for wrist calibration")
    board = session["board"]
    samples = session["samples"]
    # The two roles are chosen before fitting and shared by both calibration stages.
    roles = [sample["role"] for sample in samples]
    if set(roles) != {"fit", "validation"} or roles.count("fit") < 8 or roles.count("validation") < 3:
        raise ValueError("Provide at least eight fit samples and three held-out validation samples")

    model, state = load_workbench(mesh_directory)
    joint_addresses = [model.joint(f"joint{index}").qposadr[0] for index in range(1, 7)]
    tool = model.body("gripper_base").id
    detected = []
    robot_poses = []
    image_size = None
    image_digests = {}
    seen_digests = set()
    for sample in samples:
        image_path = (session_path.parent / sample["image"]).resolve()
        joints = np.asarray(sample["joints_rad"], dtype=float)
        if joints.shape != (6,) or not np.isfinite(joints).all():
            raise ValueError(f"{image_path}: expected six finite follower joint angles in radians")

        image_time = float(sample["image_captured_at_s"])
        robot_time = float(sample["robot_received_at_s"])
        if not np.isfinite([image_time, robot_time]).all() or abs(image_time - robot_time) > 0.05:
            raise ValueError(f"{image_path}: image and joint feedback must be paired within 50 ms")
        image_bytes = image_path.read_bytes()
        image_digest = hashlib.sha256(image_bytes).hexdigest()
        if image_digest in seen_digests:
            raise ValueError(f"Repeated calibration image content: {image_path}")
        seen_digests.add(image_digest)
        image_digests[sample["image"]] = image_digest
        if not image_bytes:
            raise ValueError(f"Empty calibration image: {image_path}")
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Cannot decode calibration image: {image_path}")
        size = (image.shape[1], image.shape[0])
        if image_size is not None and size != image_size:
            raise ValueError("All wrist images must use the same resolution and capture mode")
        image_size = size
        try:
            detection = camera_intrinsics.detect(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), board)
        except ValueError as error:
            raise ValueError(f"{image_path}: {error}") from error
        if detection["board_frame_status"] != "indexed_charuco_board":
            raise ValueError("Wrist extrinsics require an indexed ChArUco board")
        detected.append({"id": sample["image"], "role": sample["role"], "detection": detection})

        state.qpos[joint_addresses] = joints
        mujoco.mj_forward(model, state)
        pose = np.eye(4)
        pose[:3, :3] = state.xmat[tool].reshape(3, 3)
        pose[:3, 3] = state.xpos[tool]
        robot_poses.append(pose)

    optics = camera_intrinsics.solve(detected, image_size)
    if max(optics["fit_rms_px"], optics["validation_rms_px"]) > 1.5:
        raise ValueError("Wrist intrinsics exceed 1.5 px fitting or held-out reprojection RMS")
    matrix = np.asarray(optics["matrix"])
    distortion = np.asarray(optics["distortion"])
    paired = []
    for sample, view, robot_pose in zip(samples, detected, robot_poses, strict=True):
        points = np.asarray(view["detection"]["objects"], dtype=np.float64)
        pixels = np.asarray(view["detection"]["pixels"], dtype=np.float64)
        ok, rotation, translation = cv2.solvePnP(points, pixels, matrix, distortion)
        if not ok or translation[2, 0] <= 0:
            raise ValueError(f"{sample['image']}: solving the board pose failed")
        board_pose = np.eye(4)
        board_pose[:3, :3] = cv2.Rodrigues(rotation)[0]
        board_pose[:3, 3] = translation.ravel()
        projected = cv2.projectPoints(points, rotation, translation, matrix, distortion)[0].reshape(-1, 2)
        rms = float(np.sqrt(np.mean(np.sum((projected - pixels) ** 2, axis=1))))
        if rms > 1.5:
            raise ValueError(f"{sample['image']}: board reprojection RMS {rms:.2f} px exceeds 1.5 px")
        paired.append({
            "base_from_tool": robot_pose.tolist(),
            "camera_from_board": board_pose.tolist(),
            "image_captured_at_s": sample["image_captured_at_s"],
            "robot_received_at_s": sample["robot_received_at_s"],
            "reprojection_rms_px": rms,
        })

    fit = [sample for sample, role in zip(paired, roles, strict=True) if role == "fit"]
    estimate = camera_calibration.fit({
        "schema": "openarm.camera-calibration.observations.v1",
        "mode": "wrist",
        "units": "m",
        "joint_state_source": "measured_feedback",
        "base_frame": "base_link",
        "tool_frame": "gripper_base",
        "camera_name": "wrist",
        "robot_model_sha256": hashlib.sha256(RESOURCES.joinpath("touch_v3.xml").read_bytes()).hexdigest(),
        "intrinsics_source": "same-session pinhole fit with predeclared held-out views",
        "samples": fit,
    })
    camera_in_tool = np.asarray(estimate["transform"])

    def board_in_base(observation):
        return np.asarray(observation["base_from_tool"]) @ camera_in_tool @ observation["camera_from_board"]

    fit_poses = np.asarray([board_in_base(sample) for sample in fit])
    fit_board_position = fit_poses[:, :3, 3].mean(axis=0)
    fit_board_rotation = Rotation.from_matrix(fit_poses[:, :3, :3]).mean()
    checks = []
    for sample, observation in zip(samples, paired, strict=True):
        if sample["role"] == "validation":
            pose = board_in_base(observation)
            position_error = float(np.linalg.norm(pose[:3, 3] - fit_board_position))
            rotation_error = float((fit_board_rotation.inv() * Rotation.from_matrix(pose[:3, :3])).magnitude())
            checks.append({"image": sample["image"], "translation_m": position_error, "rotation_rad": rotation_error})
    translation_rms = float(np.sqrt(np.mean([item["translation_m"] ** 2 for item in checks])))
    rotation_rms = float(np.sqrt(np.mean([item["rotation_rad"] ** 2 for item in checks])))
    if translation_rms > .005 or rotation_rms > .03:
        raise ValueError(f"Held-out board consistency failed: {translation_rms:.6f} m / {rotation_rms:.6f} rad RMS")

    quaternion = Rotation.from_matrix(camera_in_tool[:3, :3]).as_quat()
    result = {
        "resolution": list(image_size),
        # Rectify raw images with the same K and no crop to match this rendered pinhole model.
        "intrinsics": [float(matrix[0, 0]), float(matrix[1, 1]), float(matrix[0, 2]), float(matrix[1, 2])],
        "position_m": camera_in_tool[:3, 3].tolist(),
        "quaternion_wxyz": quaternion[[3, 0, 1, 2]].tolist(),
        "raw_distortion": distortion.tolist(),
        "board": board,
        "session_sha256": hashlib.sha256(raw).hexdigest(),
        "image_sha256": image_digests,
        "intrinsic_estimate": optics,
        "hand_eye_estimate": estimate,
        "held_out": {
            "translation_rms_m": translation_rms, "rotation_rms_rad": rotation_rms, "per_image": checks,
        },
    }
    content = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(content)
    print(output)
