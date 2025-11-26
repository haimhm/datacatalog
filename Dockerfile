FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy requirements and install dependencies using uv
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]

