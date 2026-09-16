FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_URL=/api
RUN npm run build

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    FRONTEND_DIST_DIR=/app/frontend/dist

WORKDIR /app
COPY backend/ /app/backend/
RUN pip install --no-cache-dir /app/backend
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && fitness-seed && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
