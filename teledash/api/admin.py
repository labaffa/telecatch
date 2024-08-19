from fastapi import APIRouter, Depends, HTTPException
import fastapi
import os
from  teledash import config
from pathlib import Path
# try:
#     from typing import Annotated
# except Exception:
#     from typing_extensions import Annotated


admin_router = APIRouter()


@admin_router.get(
    '/get_from_downloadables',
    response_class=fastapi.responses.FileResponse
)
async def get_file_from_downloadable_folder(
    path_rel_to_downloadable_folder="teledash.db"
):
    
    file_path = Path(config.DATA_FOLDER).joinpath('downloadables', path_rel_to_downloadable_folder)
    if not file_path.is_file():
        raise HTTPException(
            status_code=400, detail=f"File {file_path} does not exist or is not a file")
    return fastapi.responses.FileResponse(file_path)
    