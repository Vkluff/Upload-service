# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# The commands for the 'api' and 'worker' services are defined in docker-compose.yml
# No CMD or ENTRYPOINT is needed here as they are overridden by the docker-compose file
