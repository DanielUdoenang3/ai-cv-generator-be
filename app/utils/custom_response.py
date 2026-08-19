from typing import Optional
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException


def success_response(status_code: int, message: str, data: Optional[dict] = None):
    """Returns a structured response for success responses"""

    response_data = {
        "status": "success",
        "status_code": status_code,
        "message": message,
        "data": data if data is not None else {}
    }

    return response_data


def error_response(status_code: int, message: str, data: Optional[dict] = None):
    """Raises an HTTPException for error responses"""

    response_data = {
        "status": "failure",
        "status_code": status_code,
        "message": message,
        "data": data or {}  # Ensure data is always a dictionary
    }

    raise HTTPException(status_code=status_code, detail=response_data)


# Legacy functions for backward compatibility (if needed)
def success_json_response(status_code: int, message: str, data: Optional[dict] = None):
    """Returns a JSON response for success responses (legacy)"""

    response_data = {
        "status": "success",
        "status_code": status_code,
        "message": message,
        "data": data if data is not None else {}
    }

    return JSONResponse(status_code=status_code, content=jsonable_encoder(response_data))


def error_json_response(status_code: int, message: str, data: Optional[dict] = None):
    """Returns a JSON response for failure responses (legacy)"""

    response_data = {
        "status": "failure",
        "status_code": status_code,
        "message": message,
        "data": data or {}  # Ensure data is always a dictionary
    }

    return JSONResponse(status_code=status_code, content=jsonable_encoder(response_data))