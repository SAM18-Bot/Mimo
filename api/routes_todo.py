from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.websocket import push_event
from db.database import get_db
from db.models import User, Todo
from api.routes_auth import current_user

router = APIRouter(prefix="/todos", tags=["todos"])

class TodoCreate(BaseModel):
    title: str
    due_date: date | None = None
    remind_at: datetime | None = None

class TodoOut(BaseModel):
    id: int
    title: str
    due_date: date | None
    remind_at: datetime | None
    status: str
    delivered: bool

class TodoUpdate(BaseModel):
    status: str | None = None
    title: str | None = None
    remind_at: datetime | None = None
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
        "todo": {
            "id": todo.id,
            "title": todo.title,
            "status": todo.status,
            "due_date": str(todo.due_date) if todo.due_date else None,
            "remind_at": str(todo.remind_at) if todo.remind_at else None,
        }
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
    if payload.remind_at is not None:
        todo.remind_at = payload.remind_at
        todo.delivered = False # Reset delivery status on update
    if payload.due_date is not None:
        todo.due_date = payload.due_date

    db.commit()
    db.refresh(todo)
    
    push_event({
        "type": "todo_updated",
        "user_id": user.id,
        "todo": {
            "id": todo.id,
            "title": todo.title,
            "status": todo.status,
            "due_date": str(todo.due_date) if todo.due_date else None,
            "remind_at": str(todo.remind_at) if todo.remind_at else None,
        }
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
