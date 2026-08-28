"""Reference ASA 80 calculation using exact rigid-link closure."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chain_drive_geometry import (  # noqa: E402
    calculate_chain_drive_geometry,
    get_chain_data,
    load_chain_catalog,
)
from discrete_solver import format_result_report  # noqa: E402


def main() -> None:
    catalog = load_chain_catalog(PROJECT_ROOT / "data" / "enco_asa_chains.csv")
    chain_data = get_chain_data(catalog, "80")
    result = calculate_chain_drive_geometry(
        chain_data=chain_data,
        small_sprocket_teeth=11,
        large_sprocket_teeth=20,
        desired_center_distance_mm=400.0,
    )
    discrete_view = {
        "link_count": result["chain_links"]["selected_link_count"],
        "requires_offset_link": result["chain_links"]["requires_offset_link"],
        "corrected_center_distance_mm": result["corrected_geometry"][
            "corrected_center_distance_mm"
        ],
        "center_correction_mm": result["corrected_geometry"][
            "center_distance_correction_mm"
        ],
        "discrete_chain_length_mm": result["chain_links"]["actual_chain_length_mm"],
        "closure_residual_mm": result["corrected_geometry"]["closure_residual_mm"],
        "maximum_pitch_error_mm": result["corrected_geometry"][
            "maximum_pitch_error_mm"
        ],
    }
    print(format_result_report(discrete_view))


if __name__ == "__main__":
    main()
