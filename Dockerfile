FROM python:3.9-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Expose the port the app runs on
EXPOSE 10000

# Command to run the application
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]