# Dockerfile

FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy everything from your project root into the container
COPY . .

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libgobject-2.0-0 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PORT=1000

# Expose the port Render expects
EXPOSE 1000

# Start the app with gunicorn (better for production)
CMD ["gunicorn", "--bind", "0.0.0.0:1000", "run:app"]
