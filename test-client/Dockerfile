FROM python:3.12-slim

WORKDIR /app

# Install dependencies from pyproject.toml
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

EXPOSE 3000

CMD ["fastapi", "run", "app.py", "--port", "3000"]
