FROM python:3.12

# Define build arguments
ARG API_HOST
ARG API_PORT
ARG REAR_DIFF_PGSQL_HOST
ARG REAR_DIFF_PGSQL_PORT
ARG REAR_DIFF_PGSQL_USERNAME
ARG REAR_DIFF_PGSQL_PASSWORD
ARG REAR_DIFF_PGSQL_DATABASE
ARG LOG_LEVEL

# Set environment variables
ENV API_HOST=${API_HOST}
ENV API_PORT=${API_PORT}
ENV LOG_LEVEL=${LOG_LEVEL}
ENV REAR_DIFF_PGSQL_HOST=${REAR_DIFF_PGSQL_HOST}
ENV REAR_DIFF_PGSQL_PORT=${REAR_DIFF_PGSQL_PORT}
ENV REAR_DIFF_PGSQL_USERNAME=${REAR_DIFF_PGSQL_USERNAME}
ENV REAR_DIFF_PGSQL_PASSWORD=${REAR_DIFF_PGSQL_PASSWORD}
ENV REAR_DIFF_PGSQL_DATABASE=${REAR_DIFF_PGSQL_DATABASE}

WORKDIR /rear-differential

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app/ ./app

# Expose the port
EXPOSE ${API_PORT}

# Run the application with reload enabled (in dev only)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]