import math
import unittest
from pathlib import Path

from chain_drive_geometry import (
    build_result_table_rows,
    calculate_chain_drive_geometry,
    get_chain_data,
    load_chain_catalog,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ChainDriveGeometryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = load_chain_catalog(PROJECT_ROOT / "data" / "enco_asa_chains.csv")
        cls.chain_data = get_chain_data(catalog, "80")

    def test_asa80_uses_discrete_closure_not_continuous_length_equality(self):
        result = calculate_chain_drive_geometry(
            chain_data=self.chain_data,
            small_sprocket_teeth=11,
            large_sprocket_teeth=20,
            desired_center_distance_mm=400.0,
        )

        links = result["chain_links"]
        geometry = result["corrected_geometry"]
        points = result["roller_centers"]

        self.assertEqual(links["selected_link_count"], 47)
        self.assertTrue(links["requires_offset_link"])
        self.assertAlmostEqual(
            geometry["corrected_center_distance_mm"], 398.33865880057, places=7
        )
        self.assertAlmostEqual(
            geometry["center_distance_correction_mm"], -1.66134119943, places=7
        )
        self.assertLessEqual(abs(geometry["closure_residual_mm"]), 1.0e-8)
        self.assertLessEqual(geometry["maximum_pitch_error_mm"], 1.0e-8)

        pitch_errors = [
            abs(math.dist(start, points[(index + 1) % len(points)]) - 25.4)
            for index, start in enumerate(points)
        ]
        self.assertLessEqual(max(pitch_errors), 1.0e-8)

        self.assertGreater(
            abs(geometry["continuous_path_minus_discrete_length_mm"]), 1.0
        )

    def test_result_table_uses_discrete_solver_terminology(self):
        result = calculate_chain_drive_geometry(
            chain_data=self.chain_data,
            small_sprocket_teeth=11,
            large_sprocket_teeth=20,
            desired_center_distance_mm=400.0,
        )
        labels = [row[0] for row in build_result_table_rows(result)]

        self.assertIn("Continuous link-count estimate", labels)
        self.assertIn("Nominal discrete chain length (N*p)", labels)
        self.assertIn("Rigid-link closure residual", labels)
        self.assertIn("Maximum pitch error", labels)


if __name__ == "__main__":
    unittest.main()
