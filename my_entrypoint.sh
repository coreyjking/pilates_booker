#!/bin/bash

# Convert the script to use Unix line endings if necessary
sed -i 's/\r$//' "$0"

echo "🚀 Starting Selenium..."
/opt/bin/entry_point.sh &  # Start Selenium in the background

echo "🔄 Waiting for Selenium to be ready..."
until curl -sSf "$SELENIUM_URL/status" > /dev/null; do
  echo "❌ Selenium not ready yet, retrying..."
  sleep 2
done

echo "✅ Selenium is ready! Starting Streamlit app..."
exec streamlit run UI.py --server.port=8080 --server.enableCORS=false --server.enableXsrfProtection=false --browser.serverAddress=0.0.0.0
