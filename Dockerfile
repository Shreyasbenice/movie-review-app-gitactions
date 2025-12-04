# 1. Use a lightweight Python base image
FROM python:3.9-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy requirements first (for caching speed)
COPY requirements.txt .

# 4. Install dependencies
# We install Gunicorn here to serve the app in production
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

# 5. Copy the rest of the app code
COPY . .

# 6. Expose the port Flask runs on
EXPOSE 5000

# 7. The command to run the app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
