import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.database import get_db
from backend.models import BodyPart, BodyRecord, TrainingGoal, User, UserBodyPart
from backend.schemas import (
    BodyRecordCreate,
    BodyRecordRead,
    BodyRecordUpdate,
    OnboardingCreate,
    UserProfileRead,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["users"])
SessionDep = Annotated[Session, Depends(get_db)]


def _get_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.scalar(
        select(User)
        .options(
            joinedload(User.training_goal),
            selectinload(User.preferred_body_parts).joinedload(UserBodyPart.body_part),
        )
        .where(User.user_id == user_id)
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User profile not found")
    return user


def _profile_response(db: Session, user: User) -> UserProfileRead:
    latest_weight = db.scalar(
        select(BodyRecord.weight_kg)
        .where(BodyRecord.user_id == user.user_id)
        .order_by(BodyRecord.recorded_on.desc())
        .limit(1)
    )
    if latest_weight is None:
        raise HTTPException(status_code=409, detail="Profile has no body weight record")
    return UserProfileRead(
        user_id=user.user_id,
        name=user.name,
        gender=user.gender,
        age=user.age,
        height_cm=user.height_cm,
        training_experience=user.training_experience,
        training_goal=user.training_goal,
        training_days_per_week=user.training_days_per_week,
        training_duration_minutes=user.training_duration_minutes,
        preferred_body_parts=[item.body_part for item in user.preferred_body_parts],
        latest_weight_kg=latest_weight,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _validate_references(db: Session, training_goal_id: int, body_part_ids: list[int]) -> None:
    if db.get(TrainingGoal, training_goal_id) is None:
        raise HTTPException(status_code=422, detail="Invalid training goal")
    active_ids = set(
        db.scalars(
            select(BodyPart.body_part_id).where(
                BodyPart.body_part_id.in_(body_part_ids), BodyPart.is_active.is_(True)
            )
        ).all()
    )
    if active_ids != set(body_part_ids):
        raise HTTPException(status_code=422, detail="One or more body parts are invalid")


@router.post("", response_model=UserProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(payload: OnboardingCreate, db: SessionDep) -> UserProfileRead:
    _validate_references(db, payload.training_goal_id, payload.preferred_body_part_ids)
    user = User(
        name=payload.name,
        gender=payload.gender,
        age=payload.age,
        height_cm=payload.height_cm,
        training_experience=payload.training_experience,
        training_goal_id=payload.training_goal_id,
        training_days_per_week=payload.training_days_per_week,
        training_duration_minutes=payload.training_duration_minutes,
    )
    db.add(user)
    db.flush()
    db.add(
        BodyRecord(
            user_id=user.user_id,
            recorded_on=date.today(),
            weight_kg=payload.weight_kg,
        )
    )
    db.add_all(
        [
            UserBodyPart(user_id=user.user_id, body_part_id=body_part_id)
            for body_part_id in payload.preferred_body_part_ids
        ]
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _profile_response(db, _get_user(db, user.user_id))


@router.get("/{user_id}", response_model=UserProfileRead)
def get_profile(user_id: uuid.UUID, db: SessionDep) -> UserProfileRead:
    return _profile_response(db, _get_user(db, user_id))


@router.patch("/{user_id}", response_model=UserProfileRead)
def update_profile(user_id: uuid.UUID, payload: UserUpdate, db: SessionDep) -> UserProfileRead:
    user = _get_user(db, user_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"preferred_body_part_ids"})
    body_part_ids = payload.preferred_body_part_ids
    goal_id = changes.get("training_goal_id", user.training_goal_id)
    if body_part_ids is not None:
        _validate_references(db, goal_id, body_part_ids)
    elif "training_goal_id" in changes and db.get(TrainingGoal, goal_id) is None:
        raise HTTPException(status_code=422, detail="Invalid training goal")

    for key, value in changes.items():
        if key == "name" and isinstance(value, str):
            value = value.strip()
        setattr(user, key, value)

    if body_part_ids is not None:
        db.execute(delete(UserBodyPart).where(UserBodyPart.user_id == user.user_id))
        db.add_all(
            [
                UserBodyPart(user_id=user.user_id, body_part_id=body_part_id)
                for body_part_id in body_part_ids
            ]
        )
    db.commit()
    db.expire_all()
    return _profile_response(db, _get_user(db, user_id))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(user_id: uuid.UUID, db: SessionDep) -> Response:
    user = _get_user(db, user_id)
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{user_id}/body-records", response_model=list[BodyRecordRead])
def list_body_records(user_id: uuid.UUID, db: SessionDep) -> list[BodyRecord]:
    _get_user(db, user_id)
    return list(
        db.scalars(
            select(BodyRecord).where(BodyRecord.user_id == user_id).order_by(BodyRecord.recorded_on)
        ).all()
    )


@router.post(
    "/{user_id}/body-records",
    response_model=BodyRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_body_record(user_id: uuid.UUID, payload: BodyRecordCreate, db: SessionDep) -> BodyRecord:
    _get_user(db, user_id)
    record = BodyRecord(user_id=user_id, **payload.model_dump())
    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A weight record already exists for this day"
        ) from exc
    db.refresh(record)
    return record


@router.patch("/{user_id}/body-records/{record_id}", response_model=BodyRecordRead)
def update_body_record(
    user_id: uuid.UUID,
    record_id: int,
    payload: BodyRecordUpdate,
    db: SessionDep,
) -> BodyRecord:
    record = db.scalar(
        select(BodyRecord).where(
            BodyRecord.body_record_id == record_id, BodyRecord.user_id == user_id
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Weight record not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A weight record already exists for this day"
        ) from exc
    db.refresh(record)
    return record


@router.delete("/{user_id}/body-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_body_record(user_id: uuid.UUID, record_id: int, db: SessionDep) -> Response:
    record = db.scalar(
        select(BodyRecord).where(
            BodyRecord.body_record_id == record_id, BodyRecord.user_id == user_id
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Weight record not found")
    count = (
        db.scalar(select(func.count()).select_from(BodyRecord).where(BodyRecord.user_id == user_id))
        or 0
    )
    if count <= 1:
        raise HTTPException(
            status_code=409, detail="A profile must keep at least one weight record"
        )
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
