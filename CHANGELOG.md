# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-11

### Added
- **Predictive Engine**: Integrated weighted ML ensemble (XGBoost 50%, LSTM 30%, SARIMA 20%) for precise 7-day to 30-day commodity price forecasting.
- **Crop Health Monitoring**: Integrated Google Earth Engine (Sentinel-2) to extract live NDVI metrics for farm regions.
- **Climate Integration**: Added NASA POWER API fetcher to integrate real-time temperature, rainfall, and humidity into the ML pipeline.
- **Multilingual Advisory**: Deployed AI-powered farmer advisory with direct translation support for English and Hindi.
- **Automated Alerts**: Push notifications and alert banners for significant anticipated price drops or spikes.
- **Market Data**: Synchronous ingestion of historical and daily pricing data.
- **API Documentation**: Interactive Swagger UI available at /docs.
- **Deployment Assets**: Production-ready Dockerfiles (Dockerfile.backend, Dockerfile.frontend) and docker-compose.yml.
- **Caching Layer**: Added in-memory LRU model caching and MongoDB fallbacks, reducing API latency to <50ms.

### Changed
- Replaced legacy ml_pipeline with highly optimized 	rain_per_market.py and 	rain_all_models.py scripts.
- Consolidated UI components into a single, high-performance Landing.jsx file using modern Bento-box layouts and Framer Motion animations.
- Refactored start.sh and start.bat for robust cross-platform initialization.
- Secured .env structure by enforcing strict separation between frontend and backend secrets.

### Removed
- Deprecated data/ and models/ root folders, enforcing modular encapsulation inside ackend/.
- Purged all debug, experimental, and temporary testing scripts from the repository.
- Removed unused and untracked rontend/dist/, ackend/mlruns/, and __pycache__ artifacts to maintain a pristine Git history.

### Security
- Excluded all .env files and *.pkl/*.h5 models from Git tracking.
- Added strict Pydantic schema validation for all API inputs.
- Configured proper CORS handling for frontend origins.
