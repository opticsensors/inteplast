FROM node:22-bookworm-slim AS cover-converter
WORKDIR /build
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY frontend/src/components/Features/cadCover.ts frontend/src/components/Features/coverFaceRanges.ts frontend/src/components/Features/prepareCoverGeometry.ts frontend/src/components/Features/
COPY backend/scripts/cover-glb.mjs backend/scripts/
RUN ./node_modules/.bin/esbuild backend/scripts/cover-glb.mjs --bundle --platform=node --format=cjs --external:occt-import-js --outfile=/opt/inteplast-cad/cover.cjs \
    && mkdir -p /opt/inteplast-cad/node_modules/occt-import-js \
    && cp -r node_modules/occt-import-js/dist node_modules/occt-import-js/package.json /opt/inteplast-cad/node_modules/occt-import-js/

FROM python:3.10

ENV PYTHONUNBUFFERED=1
ENV UPLOADS_DIR=/app/uploads

# OCP/VTK wheels link OpenGL even though tessellation runs without a display.
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libxrender1 libsm6 tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

WORKDIR /app/

# Place executables in the environment at the front of the path
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/.venv/bin:$PATH"

# Install dependencies
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-workspace --package app

COPY ./backend/scripts /app/backend/scripts

COPY ./backend/pyproject.toml ./backend/alembic.ini /app/backend/

COPY ./backend/app /app/backend/app

# Sync the project
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --package app

WORKDIR /app/backend/

COPY --from=cover-converter /usr/local/bin/node /usr/local/bin/node
COPY --from=cover-converter /opt/inteplast-cad /opt/inteplast-cad

CMD ["fastapi", "run", "--workers", "4", "app/main.py"]
