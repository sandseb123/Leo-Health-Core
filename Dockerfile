FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 10001 leo

# Copy project files
COPY pyproject.toml .
COPY leo_health/ ./leo_health/
COPY import_data.py .

# Install package
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -e .

# Create data and imports directories with correct ownership
RUN mkdir -p /data /imports && chown -R leo:leo /data /imports

# Switch to non-root user
USER leo

# Expose dashboard port
EXPOSE 5380

# Default command
CMD ["leo-dash"]
