"""Preview the operator-arm pose for a given mechanical-arm starting pose."""

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class JointAlignment:
    operator_servo_id: int
    mechanical_angle_rad: float
    operator_current_deg: float
    operator_target_deg: float
    operator_delta_deg: float
    within_calibrated_range: bool


def _six_angles(values: Sequence[float], name: str) -> tuple[float, ...]:
    if len(values) != 6 or any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
        for value in values
    ):
        raise ValueError(f"{name} must contain six finite numbers")
    return tuple(float(value) for value in values)


def plan_startup_alignment(
    calibration: dict,
    operator_deg_by_id: Sequence[float],
    mechanical_rad: Sequence[float] | None = None,
) -> list[JointAlignment]:
    """Invert the calibrated joint mapping on the operator's current encoder branch."""
    if (
        not isinstance(calibration, dict)
        or type(calibration.get("format_version")) is not int
        or calibration["format_version"] != 1
    ):
        raise ValueError("expected a format_version=1 calibration")
    servo_ids = calibration["joint_map"]
    if (
        len(servo_ids) != 6
        or any(type(value) is not int for value in servo_ids)
        or sorted(servo_ids) != list(range(6))
    ):
        raise ValueError("joint_map must contain each servo ID from 0 to 5")
    signs = _six_angles(calibration["signs"], "signs")
    if any(sign not in (-1.0, 1.0) for sign in signs):
        raise ValueError("joint signs must be +1 or -1")
    gain = calibration["gain"]
    if isinstance(gain, bool) or not isinstance(gain, (int, float)) or not 0 < gain <= 1:
        raise ValueError("gain must be in (0, 1]")

    current_by_id = _six_angles(operator_deg_by_id, "operator_deg_by_id")
    operator_home = _six_angles(calibration["leader_home_deg"], "leader_home_deg")
    lower = _six_angles(calibration["leader_range_min_deg"], "leader_range_min_deg")
    upper = _six_angles(calibration["leader_range_max_deg"], "leader_range_max_deg")
    mechanical_home = _six_angles(calibration["lumos_home_rad"], "lumos_home_rad")
    mechanical = mechanical_home if mechanical_rad is None else _six_angles(mechanical_rad, "mechanical_rad")

    plan = []
    for index, servo_id in enumerate(servo_ids):
        home = operator_home[index]
        low, high = lower[index], upper[index]
        if not low <= home <= high:
            raise ValueError(f"servo {servo_id} reference is outside its calibration range")
        current = current_by_id[servo_id]
        branch_offset = 360.0 * round((current - home) / 360.0)
        target = home + math.degrees(mechanical[index] - mechanical_home[index]) / (signs[index] * gain)
        plan.append(JointAlignment(
            operator_servo_id=servo_id,
            mechanical_angle_rad=mechanical[index],
            operator_current_deg=current,
            operator_target_deg=target + branch_offset,
            operator_delta_deg=target + branch_offset - current,
            within_calibrated_range=low - 1e-9 <= target <= high + 1e-9,
        ))
    return plan
