FROM python:3.13-slim

# Install OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole project (excluding files in .dockerignore)
COPY . .

# Install Node.js for Three.js build
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    cd frontend/threejs_digital_twin && npm install && npm run build && cd ../..

# Expose Streamlit default port
EXPOSE 8501

# Set Streamlit to run in headless mode
ENV STREAMLIT_SERVER_HEADLESS=true

# Run the app
CMD ["sh", "-c", "python -m streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"]
