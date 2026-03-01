# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install ffmpeg (required for Whisper) and other necessary build tools
RUN apt-get update && apt-get install -y ffmpeg build-essential

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend directory contents into the container
COPY . .

# Expose the port Gunicorn will run on
EXPOSE 5000

# Command to run the application using Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "--timeout", "480", "app:app"]