from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, Request
from jose import JWTError as PyJWTError
from sqlalchemy.orm import Session
from app.utils.token import decode_access_token
from app.models.enums import AdminRole
from app.models.admins import Admin
from app.utils.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        if payload is None:
            raise credentials_exception

        admin_email = payload.get("email")
        if admin_email is None:
            raise credentials_exception

        admin = db.query(Admin).filter(
            Admin.email == admin_email,
            Admin.is_active == True,
        ).first()
        if admin is None:
            raise credentials_exception

        return admin

    except PyJWTError as e:
        print(e)
        raise credentials_exception

async def get_current_super_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        if payload is None:
            raise credentials_exception

        admin_email = payload.get("email")
        if admin_email is None:
            raise credentials_exception

        super_admin = db.query(Admin).filter(
            Admin.email == admin_email,
            Admin.is_active == True,
            Admin.role == AdminRole.SUPER_ADMIN.value,
        ).first()
        if super_admin is None:
            raise credentials_exception

        return super_admin

    except PyJWTError as e:
        print(e)
        raise credentials_exception

async def get_current_sub_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        if payload is None:
            raise credentials_exception

        admin_email = payload.get("email")
        if admin_email is None:
            raise credentials_exception

        sub_admin = db.query(Admin).filter(
            Admin.email == admin_email,
            Admin.is_active == True,
            Admin.role == AdminRole.SUB_ADMIN.value,
        ).first()
        if sub_admin is None:
            raise credentials_exception

        return sub_admin

    except PyJWTError as e:
        print(e)
        raise credentials_exception