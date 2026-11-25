import math
import unittest

from lumos_runtime.startup_alignment import plan_startup_alignment


class StartupAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.calibration = {
            "format_version": 1,
            "joint_map": [2, 1, 0, 3, 4, 5],
            "signs": [-1, 1, 1, 1, 1, -1],
            "gain": 0.5,
            "leader_home_deg": [10, 0, 0, 0, 0, 0],
            "leader_range_min_deg": [-30] * 6,
            "leader_range_max_deg": [30] * 6,
            "lumos_home_rad": [0.1, 0, 0, 0, 0, -0.2],
        }

    def test_saved_reference_aligns_on_the_current_encoder_branch(self):
        first, *_, last = plan_startup_alignment(self.calibration, [1, 0, 372, 0, 0, -359])
        self.assertEqual(first.operator_servo_id, 2)
        self.assertEqual(first.operator_target_deg, 370)
        self.assertEqual(first.operator_delta_deg, -2)
        self.assertEqual(last.operator_target_deg, -360)
        self.assertEqual(last.operator_delta_deg, -1)

    def test_inverts_sign_and_gain_and_flags_unreachable_pose(self):
        mechanical = [0.1 + math.radians(5), math.radians(16), 0, 0, 0, -0.2]
        first, second, *_ = plan_startup_alignment(self.calibration, [0] * 6, mechanical)
        self.assertAlmostEqual(first.operator_target_deg, 0)
        self.assertTrue(first.within_calibrated_range)
        self.assertAlmostEqual(second.operator_target_deg, 32)
        self.assertFalse(second.within_calibrated_range)

    def test_rejects_nonfinite_feedback(self):
        with self.assertRaisesRegex(ValueError, "six finite numbers"):
            plan_startup_alignment(self.calibration, [0, 0, 0, 0, 0, math.nan])
