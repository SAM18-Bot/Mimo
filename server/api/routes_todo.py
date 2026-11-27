from datetime import date, datetime, timezone
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import AfterValidator, BaseModel, StringConstraints
from sqlalchemy.orm import Session

from server.api.websocket import push_event
from server.db.database import get_db
from server.db.models import User, Todo
from server.api.routes_auth import current_user

router = APIRouter(prefix="/todos", tags=["todos"])

def _utc_storage(value: datetime) -> datetime:
    # Legacy clients supplied server-local wall time. New clients provide an offset.
    return value.astimezone(timezone.utc).replace(tzinfo=None)


ReminderTime = Annotated[datetime, AfterValidator(_utc_storage)]
TodoTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]

class TodoCreate(BaseModel):
    title: TodoTitle
    due_date: date | None = None
    remind_at: ReminderTime | None = None

class TodoOut(BaseModel):
    id: int
    title: str
    due_date: date | None
    remind_at: Annotated[datetime, AfterValidator(lambda value: value.replace(tzinfo=timezone.utc))] | None
    status: str
    delivered: bool

class TodoUpdate(BaseModel):
    status: Literal["pending", "done"] | None = None
    title: TodoTitle | None = None
    remind_at: ReminderTime | None = None
    due_date: date | None = None

@router.get("", response_model=list[TodoOut])
def get_todos(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.query(Todo).filter(Todo.user_id == user.id).order_by(Todo.created_at.desc()).all()

@router.post("", response_model=TodoOut, status_code=201)
def create_todo(payload: TodoCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    todo = Todo(
        user_id=user.id,
        title=payload.title,
        due_date=payload.due_date,
        remind_at=payload.remind_at,
        status="pending",
        delivered=False,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    push_event({
        "type": "todo_added",
        "user_id": user.id,
        "todo": TodoOut.model_validate(todo, from_attributes=True).model_dump(mode="json")
    })
    return todo

@router.patch("/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: int, payload: TodoUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    if payload.status is not None:
        todo.status = payload.status
    if payload.title is not None:
        todo.title = payload.title
    if "remind_at" in payload.model_fields_set:
        todo.remind_at = payload.remind_at
        todo.delivered = False # Reset delivery status on update
    if "due_date" in payload.model_fields_set:
        todo.due_date = payload.due_date

    db.commit()
    db.refresh(todo)
    
    push_event({
        "type": "todo_updated",
        "user_id": user.id,
        "todo": TodoOut.model_validate(todo, from_attributes=True).model_dump(mode="json")
    })
    return todo

@router.delete("/{todo_id}", status_code=204)
def delete_todo(todo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    db.delete(todo)
    db.commit()
    
    push_event({
        "type": "todo_deleted",
        "user_id": user.id,
        "todo_id": todo_id
    })
    return None
