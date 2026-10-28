from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import generate, health, library, query, uploads
from app.startup import lifespan

app = FastAPI(title="DocMind API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router)
app.include_router(uploads.router)
app.include_router(query.router)
app.include_router(generate.router)
app.include_router(library.router)
