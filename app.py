from contextlib import asynccontextmanager

from fastapi import FastAPI

import db
from routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Task Management API", lifespan=lifespan)
app.include_router(router)
