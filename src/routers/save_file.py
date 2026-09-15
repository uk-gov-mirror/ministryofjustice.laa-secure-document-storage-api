from typing import Optional

import structlog
from fastapi import APIRouter, UploadFile, Depends, Request, HTTPException
from fastapi.responses import JSONResponse

from src.middleware.client_config_middleware import client_config_middleware
from src.validation.json_validator import validate_optional_body_json
from src.models.client_config import ClientConfig
from src.models.file_upload import FileUpload
from src.utils.request_types import RequestType
from src.handlers.file_upload_handler import handle_file_upload_logic


router = APIRouter()
logger = structlog.get_logger()


@router.post("/save_file")
async def save_file(
    request: Request,
    file: Optional[UploadFile] = None,
    body: FileUpload = Depends(validate_optional_body_json(FileUpload)),
    client_config: ClientConfig = Depends(client_config_middleware),
):
    """
    Saves a new file, ensuring no existing files are overwritten.
    Files are automatically scanned for viruses, and pre-configured validators are run.

    When file successfully saved, response json includes:

    * `checksum` - sha256 checksum
    * `version_id` - file's version ID if versioning enabled, otherwise get "Versioning not enabled" message
    * `file_already_existed` - Boolean string indicating if this was an existing file. Should always be "false"
                               as this endpoint does not allow file updates.

    See also /save_or_update_file for saving a file and allowing overwrites.

    * 201 CREATED on successful save
    * 409 CONFLICT if file already exists

    Replacement Filename

    An optional `replacement_filename` parameter can be specified in the request body. When set, the file
    will be saved using this name rather than the file's original name. If saved successfully, this
    replacement name must be used in all subsequent file operations.

    For this to work:
    - A file with the replacement name must not already exist. Othewise get a 409 error, like above.
    - The replacement name cannot be the same as the file's original name.

    * 201 CREATED on successful save
    * 400 BAD REQUEST if replacement name matches original name
    * 409 CONFLICT if file already exists

    Virus Scan results
    The following codes may be returned from the automatic virus scan:
    * 411 If file content length is not present
    * 400 If a virus is detected
    * 500 Virus scan gave non-standard result

    Any code other than 201 CREATED means the file has not been saved.
    """
    if file is None:
        file = UploadFile(file=None, filename="")

    if body.replacement_filename:
        if body.replacement_filename == file.filename:
            message = "Replacement filename can't be the same as original filename."
            logger.info(message)
            raise HTTPException(status_code=400, detail=message)
        file.filename = body.replacement_filename

    response = await handle_file_upload_logic(
        request=request,
        file=file,
        body=body,
        client_config=client_config,
        request_type=RequestType.POST
    )

    return JSONResponse(status_code=201, content=response.model_dump())
