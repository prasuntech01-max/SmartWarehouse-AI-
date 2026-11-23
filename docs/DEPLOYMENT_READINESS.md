# SmartWarehouse AI — Deployment Readiness Document

**Project:** SmartWarehouse AI  
**Deployment Target:** Standalone Server / Docker Container / Local Workstation  
**Author:** Release Engineering & QA Lead  
**Date:** November 23, 2026  
**Status:** Validated & Deployment-Ready

---

## 1. System Requirements

### Hardware:
- **Processor:** Dual-core 2.0 GHz or higher (x86_64 / ARM64)
- **RAM:** Minimum 4 GB (8 GB recommended for concurrent 3D WebGL client rendering)
- **GPU:** WebGL 2.0 capable graphics card or integrated GPU

### Software & Runtimes:
- **Operating System:** Windows 10/11, Ubuntu 22.04 LTS / Debian 12, or macOS 13+
- **Python:** 3.10 – 3.13 (tested on Python 3.13.7)
- **Node.js:** v18.x or v20.x (tested on v20.x with npm 10.x)

---

## 2. Dependencies & Build Artifacts

- **Python Dependencies:** Listed in [requirements.txt](file:///C:/Users/Prasun/SmartWarehouse-AI.2/requirements.txt).
  Install via:
  ```powershell
  pip install -r requirements.txt
  ```
- **Frontend Assets:** Three.js production bundle in `frontend/threejs_digital_twin/dist/`:
  - `bundle.js`: 578 KiB minified JavaScript bundle.
  - `index.html`: 23 KiB minified HTML shell.
  Build via:
  ```powershell
  cd frontend/threejs_digital_twin
  npm run build
  cd ../..
  ```

---

## 3. Environment Variables Configuration

Copy `.env.example` to `.env` to configure deployment settings:

```ini
# Database Persistence Path
SMARTWAREHOUSE_DB_PATH=data/smartwarehouse.db

# Application Server
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Logging & Diagnostic
LOG_LEVEL=INFO

# Optional MQTT IoT Gateway
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
```

---

## 4. Launch Commands

### Standard Local / Server Launch:
```powershell
python -m streamlit run app.py --server.port 8501 --server.headless true
```
Access the application at `http://localhost:8501` (or your server's public IP).

### Docker Container Deployment:
Build the image:
```bash
docker build -t smartwarehouse-ai:latest .
```
Run the container:
```bash
docker run -d -p 8501:8501 --name smartwarehouse smartwarehouse-ai:latest
```

---

## 5. Security & Safety Checklist

- [x] **Zero Hardcoded Passwords:** SQLite credentials use bcrypt hashes.
- [x] **Zero Exposed API Keys:** No cloud API secrets or tokens hardcoded in repository.
- [x] **CSV Injection Sanitization:** Exported CSVs escape formula prefixes (`=`, `+`, `-`, `@`).
- [x] **Git Hygiene:** Local databases (`*.db`), caches (`__pycache__`), environment files (`.env`), and node_modules are ignored via `.gitignore`.
- [x] **Simulation Isolation:** Runs safely in sandboxed simulation mode without commanding physical actuators.

---

## 6. Pre-Flight Verification Checklist

Before taking the application live:
1. `python -m pytest -q` -> 206 passed.
2. `python -m compileall -q .` -> 0 errors.
3. `cd frontend/threejs_digital_twin; npm run build; cd ../..` -> Clean build.
4. Open browser at `http://localhost:8501`, confirm all 5 robots are visible and moving.
