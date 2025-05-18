# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code into the container at /app
# This includes app.py, the static/ folder, templates/ folder, and aggregated_results.pkl
COPY . .

# Ensure the static/card_images directory exists (though COPY . . should handle it)
RUN mkdir -p static/card_images

# Expose the port Gunicorn will run on (Cloud Run expects 8080 by default)
EXPOSE 8080

# Define environment variable for the port (used by Cloud Run)
ENV PORT 8080
ENV FLASK_APP app.py

# Run app.py when the container launches using Gunicorn
# app:app means "look in app.py for an instance named app"
# Change the CMD to use Flask's built-in server instead of Gunicorn
CMD ["python", "app.py"]
