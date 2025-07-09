# Dockerfile

FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy everything from your project root into the container
COPY . .

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PORT=8080

# Expose the port Fly.io expects
EXPOSE 8080

# Start the app
CMD ["flask", "run", "--port=8080"]
