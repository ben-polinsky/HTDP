# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

# Install build dependencies for the Fortran code.
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends build-essential gfortran make \ 
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first to leverage Docker layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the remainder of the repository and build the HTDP binary.
COPY . .
RUN make FC=gfortran \ 
    && chmod +x htdp

# Final image.
FROM python:3.11-slim

RUN apt-get update \ 
    && apt-get install -y --no-install-recommends libgfortran5 \ 
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

EXPOSE 8080

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
