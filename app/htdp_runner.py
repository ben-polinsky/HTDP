"""Utilities for executing the HTDP binary in batch mode."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from pydantic import BaseModel, Field, validator

REPO_ROOT = Path(__file__).resolve().parent.parent
HTDP_BINARY = REPO_ROOT / "htdp"

# Mapping of menu indices to their human readable labels from MENU1 in htdp.f.
FRAME_MENU: Dict[int, str] = {
    1: "NAD_83(2011/CORS96/2007)",
    2: "NAD_83(PA11/PACP00)",
    3: "NAD_83(MA11/MARP00)",
    4: "WGS72",
    5: "WGS84 original (Transit)",
    6: "WGS84(G730)",
    7: "WGS84(G873)",
    8: "WGS84(G1150)",
    9: "WGS84(G1674)",
    10: "WGS84(G1762)",
    11: "WGS84(G2139)",
    12: "WGS84(G2296)",
    13: "ITRF88",
    14: "ITRF89",
    15: "ITRF90",
    16: "ITRF91",
    17: "ITRF92",
    18: "ITRF93",
    19: "ITRF94",
    20: "ITRF96",
    21: "ITRF97",
    22: "ITRF2000 or IGS00/IGb00",
    23: "ITRF2005 or IGS05",
    24: "ITRF2008 or IGS08/IGb08",
    25: "ITRF2014 or IGS14/IGb14",
    26: "ITRF2020 or IGS20/IGb20",
}


def _normalise_label(value: str) -> str:
    """Return a normalised representation of a frame label."""

    return re.sub(r"[^a-z0-9]", "", value.lower())


# Pre-compute lookup for user friendly aliases.
_frame_aliases: Dict[str, int] = {}
for idx, label in FRAME_MENU.items():
    _frame_aliases[_normalise_label(label)] = idx
    # Provide a couple of short aliases.
    short_label = label.split()[0]
    _frame_aliases.setdefault(_normalise_label(short_label), idx)
    if "(" in label:
        before_paren = label.split("(")[0]
        _frame_aliases.setdefault(_normalise_label(before_paren), idx)


class TransformationPoint(BaseModel):
    """A single geodetic point to be transformed by HTDP."""

    name: str = Field(..., max_length=24, description="Descriptive label for the point")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees (positive north)")
    longitude: float = Field(..., ge=-360.0, le=360.0, description="Longitude in decimal degrees (positive east)")
    ellipsoid_height: float = Field(0.0, description="Ellipsoid height in metres")

    @validator("name")
    def _strip_name(cls, value: str) -> str:
        return value.strip()


class TransformationRequest(BaseModel):
    """Input payload for a position transformation."""

    input_frame: str | int
    output_frame: str | int
    input_epoch: float = Field(..., description="Decimal year for the input coordinates (>= 1906)")
    output_epoch: float = Field(..., description="Decimal year for the output coordinates (>= 1906)")
    points: List[TransformationPoint]

    @validator("input_frame", "output_frame")
    def _validate_frame(cls, value):  # type: ignore[override]
        try:
            return resolve_frame(value)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(str(exc)) from exc

    @validator("input_epoch", "output_epoch")
    def _validate_epoch(cls, value: float) -> float:
        if value < 1906.0:
            raise ValueError("Epoch must be 1906.0 or later (HTDP model validity constraint)")
        return value

    @validator("points")
    def _require_points(cls, value: List[TransformationPoint]) -> List[TransformationPoint]:
        if not value:
            raise ValueError("At least one point is required")
        return value


class TransformationResult(BaseModel):
    """Output from HTDP for a transformed point."""

    name: str
    latitude: float = Field(..., description="Latitude in decimal degrees (positive north)")
    longitude: float = Field(..., description="Longitude in decimal degrees (positive east)")
    ellipsoid_height: float = Field(..., description="Ellipsoid height in metres")


class HTDPExecution(BaseModel):
    """Container for the raw execution artefacts returned by HTDP."""

    stdout: str
    stderr: str
    results: List[TransformationResult]


def resolve_frame(value: str | int) -> int:
    """Resolve a frame label or index to the numeric menu option expected by HTDP."""

    if isinstance(value, int):
        if value in FRAME_MENU:
            return value
        raise ValueError(f"Unknown reference frame index: {value}")

    text = value.strip()
    if not text:
        raise ValueError("Reference frame cannot be empty")

    if text.isdigit():
        return resolve_frame(int(text))

    key = _normalise_label(text)
    if key in _frame_aliases:
        return _frame_aliases[key]

    raise ValueError(
        f"Unrecognised reference frame '{value}'. Use one of: {', '.join(FRAME_MENU.values())}"
    )


def ensure_binary_exists() -> None:
    """Ensure the compiled HTDP binary is present."""

    if not HTDP_BINARY.exists():
        raise FileNotFoundError(
            f"HTDP binary not found at {HTDP_BINARY}. Compile the project with `make` before running the service."
        )

    if not os.access(HTDP_BINARY, os.X_OK):
        raise PermissionError(f"HTDP binary at {HTDP_BINARY} is not executable")


def build_stdin_script(
    output_path: Path,
    input_frame: int,
    output_frame: int,
    input_epoch: float,
    output_epoch: float,
    input_file: Path,
) -> str:
    """Construct the newline separated command script fed to the HTDP interactive binary."""

    lines = [
        "4",  # main menu: transform positions between reference frames and/or dates
        str(output_path),
        str(input_frame),
        str(output_frame),
        "2",  # input epoch as decimal year
        f"{input_epoch}",
        "2",  # output epoch as decimal year
        f"{output_epoch}",
        "3",  # supply positions via LAT,LON,EHT,TEXT file
        str(input_file),
        "0",  # return to main menu once processing is complete
    ]
    # Exit the program cleanly when control returns to the main menu
    lines.append("0")
    return "\n".join(lines) + "\n"


def write_input_file(points: Iterable[TransformationPoint], path: Path) -> None:
    """Write a delimited point file understood by HTDP option 3."""

    with path.open("w", encoding="utf-8") as handle:
        for point in points:
            lon_west = -point.longitude
            handle.write(f"{point.latitude:.12f},{lon_west:.12f},{point.ellipsoid_height:.4f},{point.name}\n")


def parse_output_file(path: Path) -> List[TransformationResult]:
    """Extract transformed coordinates from the HTDP output file."""

    results: List[TransformationResult] = []
    if not path.exists():
        raise FileNotFoundError(f"HTDP output file was not created: {path}")

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("TRANSFORMING") or stripped.startswith("***"):
                continue
            parts = stripped.split()
            if len(parts) < 4:
                continue
            try:
                latitude = float(parts[0])
                longitude_west = float(parts[1])
                height = float(parts[2])
            except ValueError:
                continue
            name = " ".join(parts[3:])
            results.append(
                TransformationResult(
                    name=name,
                    latitude=latitude,
                    longitude=-longitude_west,
                    ellipsoid_height=height,
                )
            )
    return results


def run_transformation(payload: TransformationRequest, timeout: int = 60) -> HTDPExecution:
    """Execute HTDP with the provided transformation request."""

    ensure_binary_exists()

    with tempfile.TemporaryDirectory(prefix="htdp_") as tmpdir:
        tmp_path = Path(tmpdir)
        input_file = tmp_path / "points.txt"
        output_file = tmp_path / "results.txt"

        write_input_file(payload.points, input_file)
        stdin_script = build_stdin_script(
            output_path=output_file,
            input_frame=payload.input_frame,
            output_frame=payload.output_frame,
            input_epoch=payload.input_epoch,
            output_epoch=payload.output_epoch,
            input_file=input_file,
        )

        completed = subprocess.run(
            [str(HTDP_BINARY)],
            input=stdin_script,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
            timeout=timeout,
            check=False,
        )

        if completed.returncode != 0:
            raise RuntimeError(
                "HTDP execution failed",
                completed.stdout,
                completed.stderr,
            )

        results = parse_output_file(output_file)

    return HTDPExecution(stdout=completed.stdout, stderr=completed.stderr, results=results)


def list_frames() -> List[Tuple[int, str]]:
    """Return the available reference frame options sorted by menu index."""

    return sorted(FRAME_MENU.items(), key=lambda item: item[0])
