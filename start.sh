#!/bin/bash

echo "Starting Selenium..."
java -jar /opt/selenium/selenium-server.jar standalone --host 0.0.0.0 &

SELENIUM_URL="http://0.0.0.0:4444/status"

echo "Waiting for Selenium to be ready..."
while ! curl -sSf $SELENIUM_URL > /dev/null; do
    echo "Selenium is not ready yet, retrying..."
    sleep 2
done

echo "Selenium is ready! Starting Streamlit app..."
exec streamlit run UI.py --server.port=8080 --server.enableCORS=false --server.enableXsrfProtection=false --browser.serverAddress=0.0.0.0
