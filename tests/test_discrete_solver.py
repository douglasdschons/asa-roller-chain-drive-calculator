import math
import unittest

from discrete_solver import calculate_discrete_chain_drive_geometry


class DiscreteSolverRegressionTests(unittest.TestCase):
    def assert_valid_rigid_chain(self, result, pitch_mm, expected_count, offset):
        self.assertEqual(result["link_count"], expected_count)
        self.assertEqual(result["requires_offset_link"], offset)
        self.assertEqual(len(result["roller_centers"]), expected_count)
        self.assertEqual(len(result["link_poses"]), expected_count)
        self.assertLessEqual(abs(result["closure_residual_mm"]), 1.0e-8)
        self.assertLessEqual(result["maximum_pitch_error_mm"], 1.0e-8)

        points = result["roller_centers"]
        errors = []
        for index, start in enumerate(points):
            end = points[(index + 1) % expected_count]
            errors.append(math.dist(start, end) - pitch_mm)
        self.assertLessEqual(max(abs(error) for error in errors), 1.0e-8)

    def test_asa80_11t_20t_400mm_odd_solution(self):
        result = calculate_discrete_chain_drive_geometry(25.4, 11, 20, 400.0)
        self.assert_valid_rigid_chain(result, 25.4, 47, True)
        self.assertAlmostEqual(
            result["corrected_center_distance_mm"], 398.33865880057, places=7
        )
        self.assertAlmostEqual(result["center_correction_mm"], -1.66134119943, places=7)

    def test_asa80_11t_20t_even_constraint(self):
        result = calculate_discrete_chain_drive_geometry(
            25.4, 11, 20, 400.0, require_even_link_count=True
        )
        self.assert_valid_rigid_chain(result, 25.4, 48, False)
        self.assertAlmostEqual(
            result["corrected_center_distance_mm"], 411.109006689076, places=7
        )

    def test_asa80_9t_10t_explicit_odd_case(self):
        result = calculate_discrete_chain_drive_geometry(
            25.4,
            9,
            10,
            6.5 * 25.4,
            require_even_link_count=False,
            link_count_search_radius=1,
        )
        self.assert_valid_rigid_chain(result, 25.4, 23, True)
        self.assertAlmostEqual(
            result["corrected_center_distance_mm"], 171.309354056453, places=7
        )


if __name__ == "__main__":
    unittest.main()
