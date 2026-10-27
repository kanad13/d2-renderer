# ========================================================
# Stage 1: Extract official D2 binary
# ========================================================
FROM d2lang/d2:latest AS d2-source

# ========================================================
# Stage 2: Runtime environment
# ========================================================
FROM python:3.12-slim

# Install font libraries required by D2 for accurate text measurement and SVG layout,
# plus curl for the container health check.
RUN apt-get update && apt-get install -y --no-install-recommends \
    fontconfig \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy D2 CLI binary from official image
COPY --from=d2-source /usr/local/bin/d2 /usr/local/bin/d2

# Verify installation in build stage
RUN d2 --version

# Set up dedicated non-root user for security
RUN useradd -u 1000 -m -s /bin/bash appuser

WORKDIR /app
COPY server.py .
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python3", "server.py"]
