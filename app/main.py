"""FastAPI application exposing HTDP as a web service."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .htdp_runner import (
    HTDPExecution,
    TransformationRequest,
    list_frames,
    run_transformation,
)

app = FastAPI(
    title="HTDP Web Service",
    description="Simple wrapper exposing the NOAA HTDP tool via a REST API",
)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Return a basic readiness indicator."""

    return {"status": "ok"}


@app.get("/frames")
def frames() -> list[dict[str, str | int]]:
    """List the available reference frame options from the HTDP menu."""

    return [
        {"index": index, "label": label}
        for index, label in list_frames()
    ]


@app.post("/transform", response_model=HTDPExecution)
def transform(request: TransformationRequest) -> HTDPExecution:
    """Run the HTDP binary against the supplied request payload."""

    try:
        return run_transformation(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        detail: dict[str, str] = {"message": str(exc)}
        if len(exc.args) > 1:
            detail["stdout"] = str(exc.args[1])
        if len(exc.args) > 2:
            detail["stderr"] = str(exc.args[2])
        raise HTTPException(status_code=500, detail=detail) from exc


@app.get("/")
def root() -> dict[str, str]:
    """Provide a quick pointer to the interactive documentation."""

    return {"docs": "/docs"}
