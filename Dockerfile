# Use official Python image as base image 
# This image includes Python and pip pre-installed, and is based on a slim Debian image
# for smaller size.
FROM python:3.12-slim

# Create and set working directory for the application
WORKDIR /app

# Create non-root user early so we can own /app and avoid permission issues later
# Create a new Linux user named 'appuser' with a home directory, and change ownership 
# of /app to this user. Typically: /home/appuser. This ensures that when we switch to 
# 'appuser', they have the necessary permissions to read/write in /app.

# && is used to chain commands together, so if useradd fails, the build will stop and 
# not proceed to chown.

# chown changes the ownership of the /app directory to appuser, ensuring that when we 
# switch to this user later in the Dockerfile, they have the necessary permissions to 
# read/write in that directory. This is important for security and proper functioning 
# of the application.

# The following command creates a new user named 'appuser' with a home directory and then
# changes the ownership of the /app directory to 'appuser'. This allows us to switch to
# 'appuser' later in the Dockerfile and ensures that they have the necessary permissions to
# read/write in the /app directory, which is important for security and proper functioning
# of the application.

# Two directories are created for the user: 
#     the home directory (e.g., /home/appuser) and the /app
RUN useradd --create-home appuser && chown appuser:appuser /app

# Install uv (fast Python package manager)
RUN pip install uv

# Copy dependency files first (Docker layer caching)
# This allows Docker to cache the layer with installed dependencies, so if we change application
# code but not dependencies, Docker can reuse the cached layer and speed up builds.

# Copy pyproject.toml and uv.lock (if it exists) to the working directory. These files define the
# project's dependencies. The --chown flag ensures that the copied files are owned by 'appuser', 
# which is important for permissions when we switch to that user later in the Dockerfile.
COPY --chown=appuser:appuser pyproject.toml .
COPY --chown=appuser:appuser uv.lock* .

# Switch to non-root user before installing deps (so .venv is owned by appuser)
# This is a security best practice to avoid running the application as root, which can reduce the
# impact of potential vulnerabilities in the application. By switching to 'appuser' before installing
# dependencies, we ensure that the virtual environment (.venv) is owned by 'appuser', maintaining 
# proper permissions.
USER appuser

# Install dependencies (production only)
# The --frozen flag ensures that the exact versions specified in uv.lock are installed, which promotes
# reproducibility. The --no-dev flag tells uv to skip installing development dependencies, which are
# not needed in the production environment and can reduce the attack surface and image size. This
# helps ensure a consistent and secure production environment.

# The following command installs the production dependencies for the application using uv. 
# uv sync is used to synchronize the virtual environment with the dependencies specified in 
# pyproject.toml and uv.lock. 
RUN uv sync --frozen --no-dev

# Copy application code
# The --chown flag ensures that the copied application code is owned by 'appuser', which is important
# for permissions when we switch to that user later in the Dockerfile. This allows 'appuser' to 
# read/write the application files as needed, which is essential for the proper functioning of the 
# application.
COPY --chown=appuser:appuser app/ app/

# Expose port
# This tells Docker that the container will listen on port 8000 at runtime. This is important for
# documentation and for tools that automatically detect exposed ports, but it does not actually 
# publish the port. To publish the port, you would use the -p flag with docker run (e.g., -p 8000:8000) 
# to map the container port to a host port.
# Without -p, the container's port 8000 will not be accessible from the host machine, but it can still be 
# used for inter-container communication if needed.
EXPOSE 8000

# Health check
# Once the container is running, Docker will periodically execute the specified command to check if the
# application is healthy. In this case, it will send an HTTP request to http://localhost:8000/health 
# every 30 seconds. If the request fails (e.g., if the application is not responding or returns an error), 
# Docker will consider the container unhealthy. After 3 consecutive failures, Docker can take action based 
# on the container's restart policy (e.g., restart the container). This helps ensure that the application 
# is running properly and can automatically recover from certain issues.

# --timeout=10s means that if the health check command takes longer than 10 seconds to respond, it will 
# be considered a failure.

# --retries=3 means that if the health check command fails 3 consecutive times, Docker will consider the
# container unhealthy. This allows for transient issues without immediately marking the container as unhealthy.

# -f flag in curl means "fail silently" on server errors (4xx and 5xx), which causes the command to exit with 
# a non-zero status if the health check endpoint returns an error, allowing Docker to detect the failure properly.
# If successful, the command will exit with a status of 0, indicating that the container is healthy.
# Docker determines health based on exist code: 0 = healthy, non-zero = unhealthy.

# The below command will return 1 when the command fails (e.g., if the application is not responding or returns 
# an error), which tells Docker that the container is unhealthy. 
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
# This command starts the application using uvicorn, which is an ASGI server for Python. The command specifies
# the application module (app.main:app) and configures the server to listen on all interfaces (0.0.0.0) on 
# port 8000.

# Start the Uvicorn web server using uv, serve the FastAPI application found in app/main.py (entry point is app), 
# and listen on all network interfaces (0.0.0.0) on port 8000.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]