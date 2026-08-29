from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import asyncio
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

import scraper

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CACHE_TTL = timedelta(hours=24)
# Limit concurrent Playwright product fetches to keep the site happy & memory sane.
_fetch_sem = asyncio.Semaphore(4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await scraper.start_browser()
    except Exception as e:  # noqa: BLE001
        # Don't crash the API if the browser can't launch yet; it will be
        # (re)installed and launched on demand on the first request.
        logger.error("Browser startup failed (will retry on demand): %s", e)
    try:
        await db.games.create_index("url", unique=True)
        await db.searches.create_index("query")
    except Exception as e:  # noqa: BLE001
        logger.warning("index creation: %s", e)
    yield
    await scraper.stop_browser()
    client.close()


app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")


def now():
    return datetime.now(timezone.utc)


# ---------- Models ----------
class GameRow(BaseModel):
    url: str
    title: str
    image: Optional[str] = None
    nuovo: Optional[float] = None
    usato: Optional[float] = None
    buyback: Optional[float] = None
    priced: bool = False  # True once prices have been fetched
    is_game: bool = True  # False for accessories (amiibo, custodie, gadget…)


class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[GameRow]


class ProductResponse(BaseModel):
    url: str
    title: Optional[str] = None
    image: Optional[str] = None
    nuovo: Optional[float] = None
    usato: Optional[float] = None
    buyback: Optional[float] = None
    ok: bool = False


class HistoryItem(BaseModel):
    url: str
    title: str
    image: Optional[str] = None
    nuovo: Optional[float] = None
    usato: Optional[float] = None
    buyback: Optional[float] = None
    viewed_at: datetime


# ---------- Helpers ----------
async def _cached_game(url: str):
    doc = await db.games.find_one({"url": url})
    if not doc:
        return None
    fetched = doc.get("fetched_at")
    if isinstance(fetched, datetime):
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        if now() - fetched < CACHE_TTL and doc.get("priced"):
            return doc
    return doc if doc.get("priced") else None


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"message": "GameLife Valutazioni API"}


@api_router.get("/search", response_model=SearchResponse)
async def search(q: str = Query(..., min_length=1)):
    query = q.strip()
    try:
        items = await scraper.search_games(query, limit=20)
    except Exception as e:  # noqa: BLE001
        logger.exception("search failed")
        raise HTTPException(status_code=502, detail=f"Ricerca non riuscita: {e}")

    # Record the search event
    await db.searches.insert_one({"query": query, "timestamp": now(), "count": len(items)})

    results: List[GameRow] = []
    for it in items:
        row = GameRow(url=it["url"], title=it["title"] or "Senza titolo", image=it.get("image"),
                      is_game=it.get("is_game", True))
        cached = await db.games.find_one({"url": it["url"]})
        if cached and cached.get("priced"):
            row.nuovo = cached.get("nuovo")
            row.usato = cached.get("usato")
            row.buyback = cached.get("buyback")
            if not row.image:
                row.image = cached.get("image")
            row.priced = True
        results.append(row)

    return SearchResponse(query=query, count=len(results), results=results)


@api_router.get("/product", response_model=ProductResponse)
async def product(url: str = Query(...), title: Optional[str] = None, image: Optional[str] = None):
    if not url.startswith(scraper.BASE):
        raise HTTPException(status_code=400, detail="URL non valido")

    # Serve from cache when fresh
    cached = await _cached_game(url)
    if cached:
        await db.games.update_one({"url": url}, {"$set": {"viewed_at": now()}, "$unset": {"deleted_at": ""}})
        return ProductResponse(
            url=url, title=cached.get("title") or title, image=cached.get("image") or image,
            nuovo=cached.get("nuovo"), usato=cached.get("usato"),
            buyback=cached.get("buyback"), ok=True,
        )

    async with _fetch_sem:
        # Re-check cache after acquiring the semaphore (another request may have filled it)
        cached = await _cached_game(url)
        if cached:
            return ProductResponse(
                url=url, title=cached.get("title") or title, image=cached.get("image") or image,
                nuovo=cached.get("nuovo"), usato=cached.get("usato"),
                buyback=cached.get("buyback"), ok=True,
            )
        try:
            data = await scraper.fetch_product(url)
        except Exception as e:  # noqa: BLE001
            logger.exception("product fetch failed")
            raise HTTPException(status_code=502, detail=f"Recupero prezzi non riuscito: {e}")

    if not data:
        raise HTTPException(status_code=400, detail="URL non valido")

    final_title = data.get("title") or title or "Senza titolo"
    final_image = image or data.get("image")
    priced = data.get("nuovo") is not None or data.get("buyback") is not None or data.get("usato") is not None

    if priced:
        await db.games.update_one(
            {"url": url},
            {"$set": {
                "url": url, "title": final_title, "image": final_image,
                "nuovo": data.get("nuovo"), "usato": data.get("usato"),
                "buyback": data.get("buyback"), "priced": True,
                "fetched_at": now(), "viewed_at": now(),
            }, "$unset": {"deleted_at": ""}},
            upsert=True,
        )

    return ProductResponse(
        url=url, title=final_title, image=final_image,
        nuovo=data.get("nuovo"), usato=data.get("usato"),
        buyback=data.get("buyback"), ok=bool(data.get("ok")),
    )


@api_router.get("/history", response_model=List[HistoryItem])
async def history(limit: int = 60):
    cursor = db.games.find(
        {"priced": True, "deleted_at": {"$exists": False}}
    ).sort("viewed_at", -1).limit(limit)
    out = []
    async for d in cursor:
        out.append(HistoryItem(
            url=d["url"], title=d.get("title") or "Senza titolo", image=d.get("image"),
            nuovo=d.get("nuovo"), usato=d.get("usato"), buyback=d.get("buyback"),
            viewed_at=d.get("viewed_at") or d.get("fetched_at") or now(),
        ))
    return out


@api_router.delete("/history")
async def clear_history():
    res = await db.games.update_many(
        {"deleted_at": {"$exists": False}}, {"$set": {"deleted_at": now()}}
    )
    return {"cleared": res.modified_count}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
