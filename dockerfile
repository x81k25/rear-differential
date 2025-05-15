FROM python:3.12

# Define build arguments
ARG API_HOST
ARG API_PORT
ARG PGSQL_HOST
ARG PGSQL_PORT
ARG PGSQL_USER
ARG PGSQL_PASSWORD
ARG PGSQL_NAME
ARG LOG_LEVEL

# Set environment variables
ENV API_HOST=${API_HOST}
ENV API_PORT=${API_PORT}
ENV PGSQL_HOST=${PGSQL_HOST}
ENV PGSQL_PORT=${PGSQL_PORT}
ENV PGSQL_USER=${PGSQL_USER}
ENV PGSQL_PASSWORD=${PGSQL_PASSWORD}
ENV PGSQL_NAME=${PGSQL_NAME}
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