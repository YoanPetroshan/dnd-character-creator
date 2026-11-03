# UNTESTED: Docker is not installed on the development machine, so this file has never been built or run.
# Build:  docker build -t dnd-builder .      Run:  docker run -p 8000:8000 dnd-builder
FROM node:22-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim
WORKDIR /app
COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt
COPY server/ server/
COPY chargen/ chargen/
# app.py serves <repo>/frontend/dist (parent of server/)
COPY --from=frontend /build/frontend/dist frontend/dist
ENV HOST=0.0.0.0 PORT=8000 THREADS=4
EXPOSE 8000
WORKDIR /app/server
CMD ["sh", "-c", "exec waitress-serve --listen=${HOST}:${PORT} --threads=${THREADS} app:app"]
