from math import pi, sin, asin, sqrt, floor, atan2, cos
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import streamlit as st
from matplotlib.patches import Circle


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

CSV_PATH = DATA_DIR / "enco_asa_chains.csv"
ASA_DIMENSIONS_IMAGE_STEM = "enco_asa_dimensions"


def load_chain_catalog(csv_path: str | Path) -> pd.DataFrame:
    """
    Load the ENCO ASA chain catalog from a semicolon-separated CSV file.
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Catalog file not found: {csv_path}\n"
            "Check if the CSV file exists inside the data folder."
        )

    catalog = pd.read_csv(
        csv_path,
        sep=";",
        encoding="utf-8-sig",
        dtype={
            "asa_size": str,
            "pitch_P_in_text": str,
        },
    )

    catalog.columns = catalog.columns.str.strip()

    required_columns = [
        "asa_size",
        "pitch_P_in_text",
        "pitch_P_mm",
        "inner_width_E_mm",
        "roller_diameter_R_mm",
        "plate_height_H_mm",
        "pin_diameter_G_mm",
        "overall_width_L_mm",
        "plate_thickness_T_mm",
        "breaking_load_kgf",
        "weight_kg_per_m",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in catalog.columns
    ]

    if missing_columns:
        raise ValueError(
            "Catalog CSV is missing required columns:\n"
            f"{missing_columns}\n\n"
            "Columns found in the file:\n"
            f"{catalog.columns.tolist()}"
        )

    return catalog


@st.cache_data
def load_chain_catalog_cached(csv_path_as_string: str) -> pd.DataFrame:
    """
    Cached wrapper used by Streamlit to avoid reloading the CSV on every rerun.
    """
    return load_chain_catalog(Path(csv_path_as_string))


def normalize_asa_size(asa_size: str | int) -> str:
    """
    Normalize user input such as 'ASA 80', 'ASA80', '80', or '80-1' to '80'.
    """
    asa_size = str(asa_size).upper().replace("ASA", "").strip()

    if "-" in asa_size:
        asa_size = asa_size.split("-")[0].strip()

    return asa_size


def to_float(value) -> float:
    """
    Convert catalog values to float.

    Accepts:
        - comma decimal notation: 25,40
        - dot decimal notation: 25.40
        - Brazilian thousands notation: 5.670
    """
    if isinstance(value, str):
        value = value.strip().replace(" ", "")

        if "," in value:
            value = value.replace(".", "").replace(",", ".")
        else:
            parts = value.split(".")

            if len(parts) == 2 and len(parts[1]) == 3 and parts[0].isdigit():
                value = value.replace(".", "")

    return float(value)


def find_reference_image(data_dir: Path, image_stem: str) -> Path | None:
    """
    Find a reference image by file stem.

    Accepted extensions:
        .png, .jpg, .jpeg, .webp, .bmp
    """
    allowed_extensions = [".png", ".jpg", ".jpeg", ".webp", ".bmp"]

    for extension in allowed_extensions:
        image_path = data_dir / f"{image_stem}{extension}"

        if image_path.exists():
            return image_path

    for image_path in data_dir.glob(f"{image_stem}.*"):
        if image_path.suffix.lower() in allowed_extensions:
            return image_path

    return None


def get_chain_data(catalog: pd.DataFrame, asa_size: str | int) -> dict:
    """
    Return catalog data for a selected ASA chain size.

    ENCO notation:
        P = pitch
        E = inner width
        R = roller diameter
        H = plate height
        G = pin diameter
        L = overall width
        T = plate thickness
    """
    asa_size = normalize_asa_size(asa_size)

    catalog = catalog.copy()
    catalog["asa_size"] = catalog["asa_size"].astype(str).str.strip()

    result = catalog[catalog["asa_size"] == asa_size]

    if result.empty:
        available_sizes = catalog["asa_size"].astype(str).tolist()
        raise ValueError(
            f"ASA size '{asa_size}' not found. "
            f"Available options: {available_sizes}"
        )

    chain_data = result.iloc[0].to_dict()

    numeric_columns = [
        "pitch_P_mm",
        "inner_width_E_mm",
        "roller_diameter_R_mm",
        "plate_height_H_mm",
        "pin_diameter_G_mm",
        "overall_width_L_mm",
        "plate_thickness_T_mm",
        "breaking_load_kgf",
        "weight_kg_per_m",
    ]

    for column in numeric_columns:
        chain_data[column] = to_float(chain_data[column])

    # Compatibility aliases for the current calculation and plotting functions
    chain_data["pitch_mm"] = chain_data["pitch_P_mm"]
    chain_data["roller_diameter_mm"] = chain_data["roller_diameter_R_mm"]
    chain_data["pin_diameter_mm"] = chain_data["pin_diameter_G_mm"]

    return chain_data


def format_catalog_value(value, unit: str = "", decimals: int = 2) -> str:
    """
    Format a catalog value for display.
    """
    if value is None:
        return "-"

    try:
        numeric_value = to_float(value)
        return f"{numeric_value:.{decimals}f} {unit}".strip()
    except (ValueError, TypeError):
        return str(value)


def build_result_table_rows(result: dict) -> list[list[str]]:
    """
    Build organized rows for the final result table.

    The table is divided into:
        - input data;
        - calculated drive geometry;
        - selected chain dimensions.
    """
    chain_data = result["chain_data"]
    inputs = result["inputs"]
    pitch_diameters = result["pitch_diameters"]
    chain_links = result["chain_links"]
    corrected_geometry = result["corrected_geometry"]

    actual_chain_length_m = chain_links["actual_chain_length_mm"] / 1000
    weight_kg_per_m = chain_data["weight_kg_per_m"]
    total_chain_weight_kg = actual_chain_length_m * weight_kg_per_m

    rows = [
        ["INPUT DATA", ""],
        ["ASA size", f"ASA {chain_data.get('asa_size', '-')}"] ,
        ["Small sprocket teeth", str(inputs["small_sprocket_teeth"])],
        ["Large sprocket teeth", str(inputs["large_sprocket_teeth"])],
        [
            "Desired center distance",
            f"{inputs['desired_center_distance_mm']:.2f} mm",
        ],

        ["CALCULATED DRIVE GEOMETRY", ""],
        [
            "Small sprocket pitch diameter",
            f"{pitch_diameters['small_pitch_diameter_mm']:.2f} mm",
        ],
        [
            "Large sprocket pitch diameter",
            f"{pitch_diameters['large_pitch_diameter_mm']:.2f} mm",
        ],
        [
            "Theoretical link count",
            f"{chain_links['theoretical_link_count']:.2f}",
        ],
        [
            "Selected link count",
            str(chain_links["selected_link_count"]),
        ],
        [
            "Actual chain length",
            f"{chain_links['actual_chain_length_mm']:.2f} mm",
        ],
        [
            "Corrected center distance",
            f"{corrected_geometry['corrected_center_distance_mm']:.2f} mm",
        ],
        [
            "Center distance correction",
            f"{corrected_geometry['center_distance_correction_mm']:.2f} mm",
        ],
        [
            "Requires offset link",
            str(chain_links["requires_offset_link"]),
        ],

        ["CHAIN DIMENSIONS", ""],
        [
            "Pitch P",
            format_catalog_value(chain_data.get("pitch_P_mm"), "mm"),
        ],
        [
            "Pitch P",
            str(chain_data.get("pitch_P_in_text", "-")),
        ],
        [
            "Inner width E",
            format_catalog_value(chain_data.get("inner_width_E_mm"), "mm"),
        ],
        [
            "Roller diameter R",
            format_catalog_value(chain_data.get("roller_diameter_R_mm"), "mm"),
        ],
        [
            "Plate height H",
            format_catalog_value(chain_data.get("plate_height_H_mm"), "mm"),
        ],
        [
            "Pin diameter G",
            format_catalog_value(chain_data.get("pin_diameter_G_mm"), "mm"),
        ],
        [
            "Overall width L",
            format_catalog_value(chain_data.get("overall_width_L_mm"), "mm"),
        ],
        [
            "Plate thickness T",
            format_catalog_value(chain_data.get("plate_thickness_T_mm"), "mm"),
        ],
        [
            "Breaking load",
            format_catalog_value(
                chain_data.get("breaking_load_kgf"),
                "kgf",
                decimals=0,
            ),
        ],
        [
            "Weight per meter",
            format_catalog_value(chain_data.get("weight_kg_per_m"), "kg/m"),
        ],
        [
            "Total chain weight",
            f"{total_chain_weight_kg:.2f} kg",
        ],
    ]

    return rows


def style_result_table(table, section_titles: list[str]) -> None:
    """
    Apply basic formatting to section rows in a Matplotlib table.
    """
    for (row_index, column_index), cell in table.get_celld().items():
        cell.set_linewidth(0.5)

        # Header row created by colLabels
        if row_index == 0:
            cell.set_text_props(weight="bold")
            cell.set_height(0.055)

        # Data rows start at row_index = 1 because of colLabels
        if row_index > 0:
            cell_text = table[(row_index, 0)].get_text().get_text()

            if cell_text in section_titles:
                cell.set_text_props(weight="bold")
                cell.set_height(0.055)

                if column_index == 1:
                    cell.get_text().set_text("")
            else:
                cell.set_height(0.047)


def round_to_nearest_integer(value: float) -> int:
    """
    Round a positive number to the nearest integer.

    This avoids Python's banker's rounding behavior in exact .5 cases.
    """
    return floor(value + 0.5)


def calculate_pitch_diameter(pitch_mm: float, teeth: int) -> float:
    """
    Calculate the pitch diameter of a sprocket.

    Formula:
        Dp = p / sin(pi / z)
    """
    if teeth <= 0:
        raise ValueError("The number of teeth must be positive.")

    return pitch_mm / sin(pi / teeth)


def calculate_chain_path_length(
    center_distance_mm: float,
    small_pitch_radius_mm: float,
    large_pitch_radius_mm: float,
) -> float:
    """
    Calculate the continuous geometric chain path length.

    Formula:
        C(a) = pi(r1 + r2)
             + 2*dr*asin(dr/a)
             + 2*sqrt(a² - dr²)

    where:
        dr = r2 - r1
    """
    radius_difference_mm = large_pitch_radius_mm - small_pitch_radius_mm

    if center_distance_mm <= abs(radius_difference_mm):
        raise ValueError(
            "The center distance must be greater than the radius difference."
        )

    return (
        pi * (small_pitch_radius_mm + large_pitch_radius_mm)
        + 2 * radius_difference_mm * asin(radius_difference_mm / center_distance_mm)
        + 2 * sqrt(center_distance_mm**2 - radius_difference_mm**2)
    )


def solve_bisection(
    function,
    lower_limit: float,
    upper_limit: float,
    tolerance: float = 1e-9,
    max_iterations: int = 200,
) -> float:
    """
    Solve f(x)=0 using the bisection method.
    """
    f_lower = function(lower_limit)
    f_upper = function(upper_limit)

    if f_lower == 0:
        return lower_limit

    if f_upper == 0:
        return upper_limit

    if f_lower * f_upper > 0:
        raise ValueError(
            "Invalid bisection interval: the function does not change sign."
        )

    for _ in range(max_iterations):
        midpoint = (lower_limit + upper_limit) / 2
        f_midpoint = function(midpoint)

        if abs(f_midpoint) < tolerance:
            return midpoint

        if f_lower * f_midpoint < 0:
            upper_limit = midpoint
            f_upper = f_midpoint
        else:
            lower_limit = midpoint
            f_lower = f_midpoint

    return (lower_limit + upper_limit) / 2


def calculate_chain_drive_geometry(
    chain_data: dict,
    small_sprocket_teeth: int,
    large_sprocket_teeth: int,
    desired_center_distance_mm: float,
) -> dict:
    """
    Calculate the geometry of an open roller chain drive.
    """
    pitch_mm = chain_data["pitch_mm"]

    if pitch_mm <= 0:
        raise ValueError("The chain pitch must be positive.")

    if desired_center_distance_mm <= 0:
        raise ValueError("The desired center distance must be positive.")

    if small_sprocket_teeth > large_sprocket_teeth:
        raise ValueError(
            "small_sprocket_teeth must be less than or equal to large_sprocket_teeth."
        )

    small_pitch_diameter_mm = calculate_pitch_diameter(
        pitch_mm=pitch_mm,
        teeth=small_sprocket_teeth,
    )

    large_pitch_diameter_mm = calculate_pitch_diameter(
        pitch_mm=pitch_mm,
        teeth=large_sprocket_teeth,
    )

    small_pitch_radius_mm = small_pitch_diameter_mm / 2
    large_pitch_radius_mm = large_pitch_diameter_mm / 2
    radius_difference_mm = large_pitch_radius_mm - small_pitch_radius_mm

    if desired_center_distance_mm <= abs(radius_difference_mm):
        raise ValueError(
            "The desired center distance must be greater than the radius difference."
        )

    initial_sine = radius_difference_mm / desired_center_distance_mm
    initial_angle_rad = asin(initial_sine)
    initial_straight_length_mm = sqrt(
        desired_center_distance_mm**2 - radius_difference_mm**2
    )

    initial_small_wrap_angle_rad = pi - 2 * initial_angle_rad
    initial_large_wrap_angle_rad = pi + 2 * initial_angle_rad

    initial_small_arc_length_mm = (
        small_pitch_radius_mm * initial_small_wrap_angle_rad
    )
    initial_large_arc_length_mm = (
        large_pitch_radius_mm * initial_large_wrap_angle_rad
    )

    initial_chain_path_length_mm = (
        initial_small_arc_length_mm
        + initial_large_arc_length_mm
        + 2 * initial_straight_length_mm
    )

    theoretical_link_count = initial_chain_path_length_mm / pitch_mm
    selected_link_count = round_to_nearest_integer(theoretical_link_count)

    actual_chain_length_mm = selected_link_count * pitch_mm
    chain_length_error_mm = actual_chain_length_mm - initial_chain_path_length_mm

    requires_offset_link = selected_link_count % 2 != 0

    def center_distance_error(center_distance_mm: float) -> float:
        return (
            calculate_chain_path_length(
                center_distance_mm=center_distance_mm,
                small_pitch_radius_mm=small_pitch_radius_mm,
                large_pitch_radius_mm=large_pitch_radius_mm,
            )
            - actual_chain_length_mm
        )

    lower_limit = abs(radius_difference_mm) + 1e-6
    upper_limit = max(
        desired_center_distance_mm,
        actual_chain_length_mm,
        abs(radius_difference_mm) + 1,
    )

    while center_distance_error(upper_limit) < 0:
        upper_limit *= 2

    corrected_center_distance_mm = solve_bisection(
        function=center_distance_error,
        lower_limit=lower_limit,
        upper_limit=upper_limit,
    )

    center_distance_correction_mm = (
        corrected_center_distance_mm - desired_center_distance_mm
    )

    corrected_sine = radius_difference_mm / corrected_center_distance_mm
    corrected_cosine = (
        sqrt(corrected_center_distance_mm**2 - radius_difference_mm**2)
        / corrected_center_distance_mm
    )
    corrected_angle_rad = asin(corrected_sine)
    corrected_straight_length_mm = sqrt(
        corrected_center_distance_mm**2 - radius_difference_mm**2
    )

    corrected_small_wrap_angle_rad = pi - 2 * corrected_angle_rad
    corrected_large_wrap_angle_rad = pi + 2 * corrected_angle_rad

    corrected_small_arc_length_mm = (
        small_pitch_radius_mm * corrected_small_wrap_angle_rad
    )
    corrected_large_arc_length_mm = (
        large_pitch_radius_mm * corrected_large_wrap_angle_rad
    )

    point_a = (0.0, 0.0)
    point_b = (corrected_center_distance_mm, 0.0)

    point_c = (
        -small_pitch_radius_mm * corrected_sine,
        small_pitch_radius_mm * corrected_cosine,
    )

    point_d = (
        -small_pitch_radius_mm * corrected_sine,
        -small_pitch_radius_mm * corrected_cosine,
    )

    point_f = (
        corrected_center_distance_mm - large_pitch_radius_mm * corrected_sine,
        large_pitch_radius_mm * corrected_cosine,
    )

    point_e = (
        corrected_center_distance_mm - large_pitch_radius_mm * corrected_sine,
        -large_pitch_radius_mm * corrected_cosine,
    )

    checked_chain_length_mm = (
        corrected_small_arc_length_mm
        + corrected_large_arc_length_mm
        + corrected_straight_length_mm
        + corrected_straight_length_mm
    )

    final_error_mm = checked_chain_length_mm - actual_chain_length_mm

    return {
        "chain_data": chain_data,
        "inputs": {
            "pitch_mm": pitch_mm,
            "small_sprocket_teeth": small_sprocket_teeth,
            "large_sprocket_teeth": large_sprocket_teeth,
            "desired_center_distance_mm": desired_center_distance_mm,
        },
        "pitch_diameters": {
            "small_pitch_diameter_mm": small_pitch_diameter_mm,
            "large_pitch_diameter_mm": large_pitch_diameter_mm,
        },
        "pitch_radii": {
            "small_pitch_radius_mm": small_pitch_radius_mm,
            "large_pitch_radius_mm": large_pitch_radius_mm,
            "radius_difference_mm": radius_difference_mm,
        },
        "initial_geometry": {
            "initial_straight_length_mm": initial_straight_length_mm,
            "initial_small_arc_length_mm": initial_small_arc_length_mm,
            "initial_large_arc_length_mm": initial_large_arc_length_mm,
            "initial_chain_path_length_mm": initial_chain_path_length_mm,
        },
        "chain_links": {
            "theoretical_link_count": theoretical_link_count,
            "selected_link_count": selected_link_count,
            "actual_chain_length_mm": actual_chain_length_mm,
            "chain_length_error_mm": chain_length_error_mm,
            "requires_offset_link": requires_offset_link,
        },
        "corrected_geometry": {
            "corrected_center_distance_mm": corrected_center_distance_mm,
            "center_distance_correction_mm": center_distance_correction_mm,
            "corrected_straight_length_mm": corrected_straight_length_mm,
            "corrected_small_arc_length_mm": corrected_small_arc_length_mm,
            "corrected_large_arc_length_mm": corrected_large_arc_length_mm,
            "checked_chain_length_mm": checked_chain_length_mm,
            "final_error_mm": final_error_mm,
        },
        "tangent_points": {
            "A": point_a,
            "B": point_b,
            "C": point_c,
            "D": point_d,
            "F": point_f,
            "E": point_e,
        },
    }


def generate_arc_points(
    center: tuple[float, float],
    radius: float,
    start_point: tuple[float, float],
    end_point: tuple[float, float],
    point_count: int = 120,
) -> list[tuple[float, float]]:
    """
    Generate points along a circular arc in counterclockwise direction.
    """
    center_x, center_y = center
    start_x, start_y = start_point
    end_x, end_y = end_point

    start_angle = atan2(start_y - center_y, start_x - center_x)
    end_angle = atan2(end_y - center_y, end_x - center_x)

    if end_angle < start_angle:
        end_angle += 2 * pi

    points = []

    for index in range(point_count):
        t = index / (point_count - 1)
        angle = start_angle + t * (end_angle - start_angle)

        x = center_x + radius * cos(angle)
        y = center_y + radius * sin(angle)

        points.append((x, y))

    return points


def generate_line_points(
    start_point: tuple[float, float],
    end_point: tuple[float, float],
    point_count: int = 80,
) -> list[tuple[float, float]]:
    """
    Generate points along a straight line.
    """
    start_x, start_y = start_point
    end_x, end_y = end_point

    points = []

    for index in range(point_count):
        t = index / (point_count - 1)

        x = start_x + t * (end_x - start_x)
        y = start_y + t * (end_y - start_y)

        points.append((x, y))

    return points


def build_chain_path_points(result: dict) -> list[tuple[float, float]]:
    """
    Build the closed chain pitch path.

    Path order:
        C -> small arc -> D
        D -> lower tangent -> E
        E -> large arc -> F
        F -> upper tangent -> C
    """
    pitch_radii = result["pitch_radii"]
    tangent_points = result["tangent_points"]

    small_pitch_radius_mm = pitch_radii["small_pitch_radius_mm"]
    large_pitch_radius_mm = pitch_radii["large_pitch_radius_mm"]

    point_a = tangent_points["A"]
    point_b = tangent_points["B"]

    point_c = tangent_points["C"]
    point_d = tangent_points["D"]
    point_f = tangent_points["F"]
    point_e = tangent_points["E"]

    small_arc_points = generate_arc_points(
        center=point_a,
        radius=small_pitch_radius_mm,
        start_point=point_c,
        end_point=point_d,
    )

    lower_tangent_points = generate_line_points(
        start_point=point_d,
        end_point=point_e,
    )

    large_arc_points = generate_arc_points(
        center=point_b,
        radius=large_pitch_radius_mm,
        start_point=point_e,
        end_point=point_f,
    )

    upper_tangent_points = generate_line_points(
        start_point=point_f,
        end_point=point_c,
    )

    chain_path_points = []
    chain_path_points.extend(small_arc_points)
    chain_path_points.extend(lower_tangent_points[1:])
    chain_path_points.extend(large_arc_points[1:])
    chain_path_points.extend(upper_tangent_points[1:])

    return chain_path_points


def interpolate_points_along_path(
    path_points: list[tuple[float, float]],
    spacing_mm: float,
    point_count: int,
) -> list[tuple[float, float]]:
    """
    Interpolate equally spaced points along a closed path.
    """
    cumulative_distances = [0.0]

    for index in range(1, len(path_points)):
        x0, y0 = path_points[index - 1]
        x1, y1 = path_points[index]

        segment_length = sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
        cumulative_distances.append(cumulative_distances[-1] + segment_length)

    interpolated_points = []

    for point_index in range(point_count):
        target_distance = point_index * spacing_mm

        for segment_index in range(1, len(cumulative_distances)):
            previous_distance = cumulative_distances[segment_index - 1]
            current_distance = cumulative_distances[segment_index]

            if previous_distance <= target_distance <= current_distance:
                segment_length = current_distance - previous_distance

                if segment_length == 0:
                    interpolated_points.append(path_points[segment_index])
                    break

                t = (target_distance - previous_distance) / segment_length

                x0, y0 = path_points[segment_index - 1]
                x1, y1 = path_points[segment_index]

                x = x0 + t * (x1 - x0)
                y = y0 + t * (y1 - y0)

                interpolated_points.append((x, y))
                break

    return interpolated_points


def build_chain_drive_figure(result: dict):
    """
    Build and return the corrected chain drive geometry figure.

    This figure includes:
        - chain pitch line;
        - sprocket pitch circles;
        - sprocket centers;
        - roller circles along the pitch path;
        - selected chain dimensions table;
        - ASA dimensions reference image.
    """
    chain_data = result["chain_data"]
    pitch_radii = result["pitch_radii"]
    tangent_points = result["tangent_points"]
    chain_links = result["chain_links"]
    corrected_geometry = result["corrected_geometry"]
    inputs = result["inputs"]

    pitch_mm = inputs["pitch_mm"]
    selected_link_count = chain_links["selected_link_count"]

    roller_diameter_mm = to_float(chain_data["roller_diameter_mm"])
    roller_radius_mm = roller_diameter_mm / 2

    small_pitch_radius_mm = pitch_radii["small_pitch_radius_mm"]
    large_pitch_radius_mm = pitch_radii["large_pitch_radius_mm"]

    point_a = tangent_points["A"]
    point_b = tangent_points["B"]

    chain_path_points = build_chain_path_points(result)

    roller_centers = interpolate_points_along_path(
        path_points=chain_path_points,
        spacing_mm=pitch_mm,
        point_count=selected_link_count,
    )

    x_values = [point[0] for point in chain_path_points]
    y_values = [point[1] for point in chain_path_points]

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

    # Main chain pitch path
    ax_geometry.plot(
        x_values,
        y_values,
        linewidth=2,
        label="Chain pitch line",
    )

    # Sprocket pitch circles
    small_pitch_circle = Circle(
        point_a,
        small_pitch_radius_mm,
        fill=False,
        linestyle="--",
        linewidth=1,
    )

    large_pitch_circle = Circle(
        point_b,
        large_pitch_radius_mm,
        fill=False,
        linestyle="--",
        linewidth=1,
    )

    ax_geometry.add_patch(small_pitch_circle)
    ax_geometry.add_patch(large_pitch_circle)

    # Roller circles along the pitch path
    for roller_center in roller_centers:
        roller = Circle(
            roller_center,
            roller_radius_mm,
            fill=False,
            linewidth=1,
        )
        ax_geometry.add_patch(roller)

    # Sprocket centers
    ax_geometry.scatter(
        point_a[0],
        point_a[1],
        s=60,
        label="Small sprocket center",
    )

    ax_geometry.scatter(
        point_b[0],
        point_b[1],
        s=60,
        label="Large sprocket center",
    )

    # Corrected center distance line
    ax_geometry.plot(
        [point_a[0], point_b[0]],
        [point_a[1], point_b[1]],
        linestyle="--",
        linewidth=1,
        label="Corrected center distance",
    )

    center_label_x = (point_a[0] + point_b[0]) / 2
    center_label_y = (point_a[1] + point_b[1]) / 2

    ax_geometry.text(
        center_label_x,
        center_label_y,
        f"{corrected_geometry['corrected_center_distance_mm']:.2f} mm",
        ha="center",
        va="bottom",
    )

    ax_geometry.text(point_a[0], point_a[1], "  A", va="bottom")
    ax_geometry.text(point_b[0], point_b[1], "  B", va="bottom")

    ax_geometry.set_aspect("equal", adjustable="box")
    ax_geometry.grid(True)

    ax_geometry.set_xlabel("x [mm]")
    ax_geometry.set_ylabel("y [mm]")

    ax_geometry.set_title(
        f"ASA {chain_data['asa_size']} chain drive | "
        f"P = {pitch_mm:.2f} mm | "
        f"{selected_link_count} links | "
        f"Corrected center = "
        f"{corrected_geometry['corrected_center_distance_mm']:.2f} mm"
    )

    # Technical dimensions table
    ax_table.axis("off")

    table_rows = build_result_table_rows(result)

    table = ax_table.table(
        cellText=table_rows,
        colLabels=["Parameter", "Value"],
        loc="center",
        cellLoc="left",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.0, 1.25)

    style_result_table(
        table=table,
        section_titles=[
            "INPUT DATA",
            "CALCULATED DRIVE GEOMETRY",
            "CHAIN DIMENSIONS",
        ],
    )

    # ASA dimensions reference image
    ax_image.axis("off")

    reference_image_path = find_reference_image(
        data_dir=DATA_DIR,
        image_stem=ASA_DIMENSIONS_IMAGE_STEM,
    )

    if reference_image_path is not None:
        reference_image = mpimg.imread(reference_image_path)
        ax_image.imshow(reference_image)
    else:
        ax_image.text(
            0.5,
            0.5,
            "Reference image not found:\n"
            f"{DATA_DIR / ASA_DIMENSIONS_IMAGE_STEM}",
            ha="center",
            va="center",
        )

    fig.tight_layout()

    return fig


def result_to_dataframe(result: dict) -> pd.DataFrame:
    """
    Convert result rows to a DataFrame for Streamlit display.
    """
    return pd.DataFrame(
        build_result_table_rows(result),
        columns=["Parameter", "Value"],
    )


def calculate_total_chain_weight_kg(result: dict) -> float:
    """
    Calculate total chain weight from actual chain length and catalog weight per meter.
    """
    chain_data = result["chain_data"]
    chain_links = result["chain_links"]

    actual_chain_length_m = chain_links["actual_chain_length_mm"] / 1000
    weight_kg_per_m = chain_data["weight_kg_per_m"]

    return actual_chain_length_m * weight_kg_per_m


def run_streamlit_app() -> None:
    """
    Run the Streamlit web interface.
    """
    st.set_page_config(
        page_title="ASA Roller Chain Drive Calculator",
        page_icon="⚙️",
        layout="wide",
    )

    st.title("ASA Roller Chain Drive Calculator")

    st.markdown(
        """
        Calculate the geometry of an open ASA roller chain drive using ENCO catalog data.
        The app estimates sprocket pitch diameters, selected number of links, corrected
        center distance, actual chain length, and total chain weight.
        """
    )

    try:
        catalog = load_chain_catalog_cached(str(CSV_PATH))
    except FileNotFoundError as error:
        st.error(str(error))
        st.stop()
    except ValueError as error:
        st.error(str(error))
        st.stop()

    available_sizes = catalog["asa_size"].astype(str).str.strip().tolist()

    default_index = 0
    if "80" in available_sizes:
        default_index = available_sizes.index("80")

    with st.sidebar:
        st.header("Input data")

        selected_asa_size = st.selectbox(
            "ASA chain size",
            options=available_sizes,
            index=default_index,
            format_func=lambda size: f"ASA {size}",
        )

        small_sprocket_teeth = st.number_input(
            "Small sprocket teeth",
            min_value=1,
            value=15,
            step=1,
        )

        large_sprocket_teeth = st.number_input(
            "Large sprocket teeth",
            min_value=1,
            value=30,
            step=1,
        )

        desired_center_distance_mm = st.number_input(
            "Desired center distance [mm]",
            min_value=1.0,
            value=500.0,
            step=1.0,
        )

        calculate_button = st.button("Calculate", type="primary")

    st.subheader("Calculation")

    if not calculate_button:
        st.info("Set the input data in the sidebar and click Calculate.")
        st.stop()

    try:
        chain_data = get_chain_data(catalog, selected_asa_size)

        result = calculate_chain_drive_geometry(
            chain_data=chain_data,
            small_sprocket_teeth=int(small_sprocket_teeth),
            large_sprocket_teeth=int(large_sprocket_teeth),
            desired_center_distance_mm=float(desired_center_distance_mm),
        )

    except ValueError as error:
        st.error(str(error))
        st.stop()

    chain_links = result["chain_links"]
    corrected_geometry = result["corrected_geometry"]
    total_chain_weight_kg = calculate_total_chain_weight_kg(result)

    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)

    metric_col_1.metric(
        "Selected links",
        f"{chain_links['selected_link_count']}",
    )

    metric_col_2.metric(
        "Corrected center",
        f"{corrected_geometry['corrected_center_distance_mm']:.2f} mm",
    )

    metric_col_3.metric(
        "Actual chain length",
        f"{chain_links['actual_chain_length_mm']:.2f} mm",
    )

    metric_col_4.metric(
        "Total chain weight",
        f"{total_chain_weight_kg:.2f} kg",
    )

    if chain_links["requires_offset_link"]:
        st.warning(
            "The selected number of links is odd. This configuration requires an offset link."
        )
    else:
        st.success(
            "The selected number of links is even. No offset link is required."
        )

    st.subheader("Geometry and catalog data")

    fig = build_chain_drive_figure(result)
    st.pyplot(fig)
    plt.close(fig)

    st.subheader("Result table")
    result_table = result_to_dataframe(result)
    st.dataframe(result_table, use_container_width=True, hide_index=True)

    with st.expander("Selected chain catalog data"):
        selected_chain_table = pd.DataFrame([result["chain_data"]])
        st.dataframe(selected_chain_table, use_container_width=True, hide_index=True)

    with st.expander("Notes"):
        st.markdown(
            """
            - The corrected center distance is solved using a custom bisection method.
            - No SciPy dependency is required.
            - The total chain weight is estimated from the actual chain length and the catalog weight per meter.
            - The plot represents the pitch path and roller positions schematically.
            """
        )


if __name__ == "__main__":
    run_streamlit_app()
