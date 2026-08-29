# ---------------------------------------------------------------------------
# GameLife Valutazioni — self-contained image for a VPS (backend + web UI).
#
# Stage 1 builds the Expo web bundle (static files).
# Stage 2 is the Playwright Python runtime (Chromium already installed) that
# runs the FastAPI backend AND serves the web UI from the same origin.
# ---------------------------------------------------------------------------

# ---------- Stage 1: build the web interface ----------
FROM node:20-bookworm AS webbuild
WORKDIR /web
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY frontend/ ./
# Same-origin API: leave EXPO_PUBLIC_BACKEND_URL empty so the web app calls /api/*
ENV EXPO_PUBLIC_BACKEND_URL=""
RUN npx expo export --platform web --output-dir dist

# ---------- Stage 2: runtime (Python + Playwright + Chromium) ----------
FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy AS runtime
WORKDIR /app

# Playwright browsers are already installed in this image at /ms-playwright.
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
# The built web UI is served by FastAPI (see server.py: mounts ./webdist at /).
COPY --from=webbuild /web/dist ./webdist

EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
