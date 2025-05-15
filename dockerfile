FROM python:3.12

# Define build arguments
ARG API_HOST=0.0.0.0
ARG API_PORT=8000
ARG PGSQL_HOST=localhost
ARG PGSQL_PORT=5432
ARG PGSQL_USER=postgres
ARG PGSQL_PASSWORD=password
ARG PGSQL_NAME=postgres
ARG LOG_LEVEL=INFO

# Set environment variables
ENV API_HOST=${API_HOST}
ENV API_PORT=${API_PORT}
ENV DB_HOST=${PGSQL_HOST}
ENV DB_PORT=${PGSQL_PORT}
ENV DB_USER=${PGSQL_USER}
ENV DB_PASSWORD=${PGSQL_PASSWORD}
ENV DB_NAME=${PGSQL_NAME}
ENV LOG_LEVEL=${LOG_LEVEL}

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