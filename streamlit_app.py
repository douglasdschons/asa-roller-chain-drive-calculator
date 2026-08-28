"""Streamlit interface for the exact rigid-link chain-drive solver."""

from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from matplotlib.patches import Circle

from chain_drive_geometry import (
    build_chain_path_points,
    build_result_table_rows,
    calculate_chain_drive_geometry,
    get_chain_data,
    load_chain_catalog,
    to_float,
)


APP_DIR = Path(__file__).resolve().parent
CSV_PATH = APP_DIR / "data" / "enco_asa_chains.csv"
FIGURES_DIR = APP_DIR / "docs" / "figures"
INSTRUCTIONS_IMAGE_PATH = FIGURES_DIR / "instructions.png"
ASA_DIMENSIONS_IMAGE_PATH = FIGURES_DIR / "enco_asa_dimensions.png"

GITHUB_REPOSITORY_URL = (
    "https://github.com/douglasdschons/asa-roller-chain-drive-calculator"
)
LINKEDIN_PROFILE_URL = "https://www.linkedin.com/in/douglasdschons/?locale=pt"
APP_VERSION = "2.0.0"


@st.cache_data
def load_chain_catalog_cached(csv_path_as_string: str) -> pd.DataFrame:
    return load_chain_catalog(Path(csv_path_as_string))


def calculate_total_chain_weight_kg(result: dict) -> float:
    actual_chain_length_m = result["chain_links"]["actual_chain_length_mm"] / 1000.0
    return actual_chain_length_m * result["chain_data"]["weight_kg_per_m"]


def build_chain_drive_figure(result: dict):
    """Build the corrected pitch locus with exact rigid-link roller centers."""
    chain_data = result["chain_data"]
    pitch_radii = result["pitch_radii"]
    tangent_points = result["tangent_points"]
    chain_links = result["chain_links"]
    corrected_geometry = result["corrected_geometry"]
    pitch_mm = result["inputs"]["pitch_mm"]

    roller_radius_mm = to_float(chain_data["roller_diameter_mm"]) / 2.0
    point_a = tangent_points["A"]
    point_b = tangent_points["B"]
    chain_path_points = build_chain_path_points(result)
    roller_centers = result["roller_centers"]

    fig = plt.figure(figsize=(17, 8))
    grid = fig.add_gridspec(
        nrows=2,
        ncols=2,
        width_ratios=[2.3, 1.0],
        height_ratios=[1.0, 1.0],
    )
    ax_geometry = fig.add_subplot(grid[:, 0])
    ax_table = fig.add_subplot(grid[0, 1])
    ax_image = fig.add_subplot(grid[1, 1])

    ax_geometry.plot(
        [point[0] for point in chain_path_points],
        [point[1] for point in chain_path_points],
        linewidth=1.5,
        label="Continuous roller-center locus",
    )
    ax_geometry.add_patch(
        Circle(
            point_a,
            pitch_radii["small_pitch_radius_mm"],
            fill=False,
            linestyle="--",
            linewidth=1,
        )
    )
    ax_geometry.add_patch(
        Circle(
            point_b,
            pitch_radii["large_pitch_radius_mm"],
            fill=False,
            linestyle="--",
            linewidth=1,
        )
    )

    closed_centers = roller_centers + roller_centers[:1]
    ax_geometry.plot(
        [point[0] for point in closed_centers],
        [point[1] for point in closed_centers],
        linewidth=0.8,
        color="tab:orange",
        label="Rigid pitch chords",
    )
    for roller_center in roller_centers:
        ax_geometry.add_patch(
            Circle(roller_center, roller_radius_mm, fill=False, linewidth=0.8)
        )

    ax_geometry.scatter(*point_a, s=60, label="Small sprocket center")
    ax_geometry.scatter(*point_b, s=60, label="Large sprocket center")
    ax_geometry.plot(
        [point_a[0], point_b[0]],
        [point_a[1], point_b[1]],
        linestyle="--",
        linewidth=1,
        label="Corrected center distance",
    )
    ax_geometry.text(
        (point_a[0] + point_b[0]) / 2.0,
        (point_a[1] + point_b[1]) / 2.0,
        f"{corrected_geometry['corrected_center_distance_mm']:.3f} mm",
        ha="center",
        va="bottom",
    )
    ax_geometry.set_aspect("equal", adjustable="box")
    ax_geometry.grid(True)
    ax_geometry.legend(loc="best")
    ax_geometry.set_xlabel("x [mm]")
    ax_geometry.set_ylabel("y [mm]")
    ax_geometry.set_title(
        f"ASA {chain_data['asa_size']} | P={pitch_mm:.2f} mm | "
        f"N={chain_links['selected_link_count']} | "
        f"C={corrected_geometry['corrected_center_distance_mm']:.3f} mm"
    )

    ax_table.axis("off")
    table = ax_table.table(
        cellText=build_result_table_rows(result),
        colLabels=["Parameter", "Value"],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.5)
    table.scale(1.0, 1.08)

    ax_image.axis("off")
    if ASA_DIMENSIONS_IMAGE_PATH.exists():
        ax_image.imshow(mpimg.imread(ASA_DIMENSIONS_IMAGE_PATH))

    fig.tight_layout()
    return fig


def render_project_links() -> None:
    st.divider()
    st.subheader("Project links")
    left, right = st.columns(2)
    with left:
        st.link_button("GitHub repository", GITHUB_REPOSITORY_URL, width="stretch")
    with right:
        st.link_button("LinkedIn profile", LINKEDIN_PROFILE_URL, width="stretch")


def run_streamlit_app() -> None:
    st.set_page_config(
        page_title="ASA Roller Chain Drive Calculator",
        page_icon="⚙️",
        layout="wide",
    )
    st.title("ASA Roller Chain Drive Calculator")
    st.caption(f"Version {APP_VERSION} | rigid-link discrete solver")
    st.markdown(
        """
        Exact geometric closure for open ASA roller-chain drives. The
        pitch-circle path is used as the roller-center locus, while every real
        chain link is enforced as a rigid chord of length equal to the pitch.
        """
    )

    if INSTRUCTIONS_IMAGE_PATH.exists():
        st.image(
            INSTRUCTIONS_IMAGE_PATH,
            caption="Input parameters for the ASA chain-drive calculator.",
            width="stretch",
        )

    try:
        catalog = load_chain_catalog_cached(str(CSV_PATH))
    except (FileNotFoundError, ValueError) as error:
        st.error(str(error))
        st.stop()

    available_sizes = catalog["asa_size"].astype(str).str.strip().tolist()
    default_index = available_sizes.index("80") if "80" in available_sizes else 0

    with st.sidebar:
        st.header("Input data")
        selected_asa_size = st.selectbox(
            "ASA chain size",
            options=available_sizes,
            index=default_index,
            format_func=lambda size: f"ASA {size}",
        )
        small_sprocket_teeth = st.number_input(
            "Small sprocket teeth", min_value=3, value=11, step=1
        )
        large_sprocket_teeth = st.number_input(
            "Large sprocket teeth", min_value=3, value=20, step=1
        )
        desired_center_distance_mm = st.number_input(
            "Desired center distance [mm]", min_value=1.0, value=400.0, step=1.0
        )
        require_even_link_count = st.checkbox(
            "Require an even link count (no offset link)", value=False
        )
        calculate_button = st.button("Calculate", type="primary")

    if not calculate_button:
        st.info("Set the input data in the sidebar and click Calculate.")
        render_project_links()
        st.stop()

    try:
        chain_data = get_chain_data(catalog, selected_asa_size)
        result = calculate_chain_drive_geometry(
            chain_data=chain_data,
            small_sprocket_teeth=int(small_sprocket_teeth),
            large_sprocket_teeth=int(large_sprocket_teeth),
            desired_center_distance_mm=float(desired_center_distance_mm),
            require_even_link_count=bool(require_even_link_count),
        )
    except (ValueError, RuntimeError) as error:
        st.error(str(error))
        st.stop()

    links = result["chain_links"]
    geometry = result["corrected_geometry"]
    weight = calculate_total_chain_weight_kg(result)

    col1, col2, col3 = st.columns(3)
    col1.metric("Selected links", f"{links['selected_link_count']}")
    col2.metric(
        "Corrected center", f"{geometry['corrected_center_distance_mm']:.9f} mm"
    )
    col3.metric(
        "Center correction", f"{geometry['center_distance_correction_mm']:+.9f} mm"
    )

    col4, col5, col6 = st.columns(3)
    col4.metric(
        "Closure residual", f"{geometry['closure_residual_mm']:.2e} mm"
    )
    col5.metric(
        "Maximum pitch error", f"{geometry['maximum_pitch_error_mm']:.2e} mm"
    )
    col6.metric("Total chain weight", f"{weight:.2f} kg")

    if links["requires_offset_link"]:
        st.warning("Odd link count: the physical assembly requires an offset link.")
    else:
        st.success("Even link count: no offset link is required.")

    fig = build_chain_drive_figure(result)
    st.pyplot(fig)
    plt.close(fig)

    st.subheader("Result table")
    st.dataframe(
        pd.DataFrame(build_result_table_rows(result), columns=["Parameter", "Value"]),
        width="stretch",
        hide_index=True,
    )
    with st.expander("Solver notes"):
        st.markdown(
            """
            - The continuous pitch path is only the locus and link-count estimate.
            - Consecutive roller centers are solved at an exact chord distance `p`.
            - Center distance is solved from the discrete closure residual.
            - Candidate link counts are ranked by distance from the requested center.
            """
        )

    render_project_links()


if __name__ == "__main__":
    run_streamlit_app()
