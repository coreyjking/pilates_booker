# Use Selenium Standalone Chrome as the base image
FROM selenium/standalone-chrome:latest

# Switch to root to perform installations and file operations
USER root

WORKDIR /app

# Copy the application code into the container
COPY . .

# Copy the startup script
COPY start.sh /app/start.sh
COPY setup.sh /app/setup.sh

# Change permissions for the entire /app folder so that all files become executable
RUN chmod -R +x /app

# Remove the Ubuntu sources.list file
RUN rm -f /etc/apt/sources.list.d/ubuntu.sources

# Ensure apt directories exist and have correct permissions
RUN mkdir -p /var/lib/apt/lists/partial && chmod -R 777 /var/lib/apt/lists

# Install system dependencies required for Python and apt updates
RUN apt-get update --allow-releaseinfo-change && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip curl wget unzip jq libnss3 libx11-xcb1 && \
    rm -rf /var/lib/apt/lists/*

# Create and activate a Python virtual environment,
# then install dependencies inside it.
RUN python3 -m venv /app/venv \
    && /app/venv/bin/pip install --upgrade pip \
    && /app/venv/bin/pip install --no-cache-dir -r requirements.txt

#RUN /app/setup.sh

# Change ownership of /app so that the non-root user can write to it
#RUN chown -R 1200:1200 /app

# Switch back to the non-root user (default in Selenium image)
USER 1200

# Set environment variables for Chrome & Selenium
ENV SELENIUM_REMOTE_URL=http://localhost:4444/status
ENV DISPLAY=:99

# Ensure the Python virtual environment is used globally
ENV PATH="/app/venv/bin:$PATH"

# Create the .streamlit directory
RUN mkdir -p ~/.streamlit

# Copy Streamlit configuration files
COPY .streamlit/config.toml ~/.streamlit/
COPY .streamlit/credentials.toml ~/.streamlit/

# Expose the port for Streamlit
EXPOSE 8080

# Start the Streamlit application using the script
CMD ["/app/start.sh"]
