# Use a slim Python image for the Streamlit-based admin GUI.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Need openssl for cert generation (plus tini/procps/ca-certs)
RUN apt-get update && apt-get install -y --no-install-recommends \
      procps tini ca-certificates openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Streamlit config from repo root
COPY .streamlit /etc/streamlit
ENV STREAMLIT_CONFIG=/etc/streamlit/config.toml

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Entry script (repo root: bin/entrypoint.sh -> /app/bin/entrypoint.sh)
RUN chmod +x /app/bin/entrypoint.sh

EXPOSE 8088

# tini handles signals; entrypoint ensures certs then execs Streamlit
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/bin/entrypoint.sh"]
