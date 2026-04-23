FROM python:3.13-slim

# Install dependencies (only boto3 for this example)
RUN pip install --no-cache-dir boto3

# Set the working directory
WORKDIR /app

# Copy the application code
COPY app.py .

# Run the script
CMD ["python", "app.py"]
