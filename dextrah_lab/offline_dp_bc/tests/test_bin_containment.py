import math
import unittest

from dextrah_lab.offline_dp_bc.bin_containment import projected_box_half_extents


class BinContainmentTest(unittest.TestCase):
    def test_identity_preserves_centered_half_extents(self):
        projected = projected_box_half_extents((0.03, 0.05, 0.04), (1.0, 0.0, 0.0, 0.0))

        self.assertEqual(projected, (0.03, 0.05, 0.04))

    def test_yaw_quarter_turn_swaps_xy_extents(self):
        half_angle = math.pi / 4.0
        projected = projected_box_half_extents(
            (0.03, 0.05, 0.04),
            (math.cos(half_angle), 0.0, 0.0, math.sin(half_angle)),
        )

        self.assertAlmostEqual(projected[0], 0.05)
        self.assertAlmostEqual(projected[1], 0.03)
        self.assertAlmostEqual(projected[2], 0.04)

    def test_normalizes_quaternion(self):
        unit = projected_box_half_extents((0.03, 0.05, 0.04), (1.0, 0.0, 0.0, 0.0))
        scaled = projected_box_half_extents((0.03, 0.05, 0.04), (4.0, 0.0, 0.0, 0.0))

        self.assertEqual(scaled, unit)

    def test_centered_bounds_remove_root_offset_false_negative(self):
        half_bin_y = 0.5 * 0.17024909061404367
        center_error_y = 0.03774091183154854
        root_radius = 0.05594612658023834
        centered_half_y = projected_box_half_extents(
            (0.03587455903120018, 0.04783419160749519, 0.042828334716132406),
            (1.0, 0.0, 0.0, 0.0),
        )[1]

        centered_margin = half_bin_y - centered_half_y - center_error_y
        legacy_margin = half_bin_y - root_radius - center_error_y

        self.assertGreaterEqual(centered_margin, -0.001)
        self.assertLess(legacy_margin, -0.008)

    def test_rejects_zero_quaternion(self):
        with self.assertRaises(ValueError):
            projected_box_half_extents((0.03, 0.05, 0.04), (0.0, 0.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
