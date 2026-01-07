from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError

from app.db.sessions import get_db
from app.db.models import Repository
from app.schemas.repository import (
    RepositoryCreateRequest,
    RepositoryCreateResponse,
)
from app.services.github_service import get_repository_data

router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"],
)

@router.post(
    "",
    response_model=RepositoryCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_repository(
    payload: RepositoryCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    repo_data = await get_repository_data(payload.repo_url)

    repository = Repository(**repo_data)

    db.add(repository)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository already exists",
        )

    await db.refresh(repository)
    return repository


@router.get(
    "/{repository_id}",
    response_model=RepositoryCreateResponse,
)
async def get_repository(
    repository_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    return repository

@router.put(
    "/{repository_id}",
    response_model=RepositoryCreateResponse,
)
async def refresh_repository(
    repository_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    repo_url = f"https://github.com/{repository.full_name}"
    updated_data = await get_repository_data(repo_url)

    for key, value in updated_data.items():
        setattr(repository, key, value)

    await db.commit()
    await db.refresh(repository)

    return repository


@router.delete(
    "/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_repository(
    repository_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    await db.execute(
        delete(Repository).where(Repository.id == repository_id)
    )
    await db.commit()
