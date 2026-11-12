from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import connect_db, close_db
from routes.market import router as market_router
from routes.predict import router as predict_router
from routes.chat import router as chat_router
from routes.weather import router as weather_router
from routes.crop_health import router as crop_health_router
from routes.farmer_advisory import router as farmer_advisory_router
from data_ingestion.agmarknet_scraper import scraper
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import logging

scheduler = AsyncIOScheduler()
logger = logging.getLogger("Main")

def run_agmarknet_scraper():
    """Background task to run the scraper."""
    logger.info("Starting background scraper job...")
    try:
        # We can fetch multiple pages to populate the cache
        records = scraper.scrape_latest_prices(max_pages=5)
        logger.info(f"Background scraper finished. Fetched {len(records)} records.")
    except Exception as e:
        logger.error(f"Background scraper failed: {e}")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    await connect_db()
    
    # Start APScheduler
    scheduler.add_job(run_agmarknet_scraper, 'interval', hours=6, id='agmarknet_scraper_job')
    scheduler.start()
    logger.info("APScheduler started.")
    
    # Preload legacy commodity-level models & warm up
    from ensemble.model_manager import model_manager
    logger.info("Preloading ML models (LRU cache)...")
    await asyncio.to_thread(model_manager.preload_models)
    await asyncio.to_thread(model_manager.warmup_models)
    logger.info("ML model preload complete.")
    
    yield
    
    scheduler.shutdown()
    await close_db()


app = FastAPI(
    title="KisanMitra AI",
    description="Live agricultural market intelligence API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — only allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(market_router, prefix="/api/market", tags=["market"])
app.include_router(predict_router, prefix="/api", tags=["predict"])
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(weather_router, prefix="/api", tags=["weather"])
app.include_router(crop_health_router, prefix="/api", tags=["crop-health"])
app.include_router(farmer_advisory_router, prefix="/api", tags=["farmer-advisory"])


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/admin/run-scraper")
async def trigger_scraper():
    """Manual endpoint to trigger scraper on demand."""
    # Run in background to avoid blocking request
    asyncio.create_task(asyncio.to_thread(run_agmarknet_scraper))
    return {"status": "Scraper job triggered in background"}
