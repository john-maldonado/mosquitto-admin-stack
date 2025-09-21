FROM eclipse-mosquitto:2

# Copy watcher script into the image
COPY watcher.sh /usr/local/bin/watcher.sh

# Make watcher executable
RUN chmod +x /usr/local/bin/watcher.sh

# Use the watcher script as the entrypoint
ENTRYPOINT ["/usr/local/bin/watcher.sh"]