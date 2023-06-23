from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from teledash.channel_messages import tg_client, search_all_channels
import base64


app = FastAPI(
    title="TeleDash",
    description="Extract useful info from Telegram channels and groups",
    version="0.0.1",
    contact={
        "name": "Giosue",
        "email": "giosue.ruscica@gmail.com",
    },
    license_info={
        "name": "MIT",
    },
    default_response_class=ORJSONResponse
)
app.mount("/static", StaticFiles(directory="teledash/static"), name="static")
templates = Jinja2Templates(directory="teledash/templates")
tg_client.start()


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request):
    data = {"request": request}
    return templates.TemplateResponse(
        "index.html",
        data
    )


@app.get("/api/search_channels")
async def read_search_channel(
    search, limit: int=100, offset_channel: int=0, offset_id: int=0):
    async with tg_client:  
        response = await search_all_channels(
            tg_client, search, limit, offset_channel, offset_id)
    return JSONResponse(content=jsonable_encoder(
        response, custom_encoder={
        bytes: lambda v: base64.b64encode(v).decode('utf-8')}))
