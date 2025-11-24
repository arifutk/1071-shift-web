
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, Time, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time as time_type

DATABASE_URL = "sqlite:///./shifts.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    hourly_rate = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

    shifts = relationship("Shift", back_populates="employee")
    time_off_requests = relationship("TimeOffRequest", back_populates="employee")


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    start_time = Column(Time)
    end_time = Column(Time)
    position = Column(String, nullable=False)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    employee = relationship("Employee", back_populates="shifts")


class TimeOffRequest(Base):
    __tablename__ = "time_off_requests"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    reason = Column(String, nullable=True)
    status = Column(String, default="pending")

    employee_id = Column(Integer, ForeignKey("employees.id"))
    employee = relationship("Employee", back_populates="time_off_requests")


# ----- Pydantic şemalar ----- #

class EmployeeBase(BaseModel):
    full_name: str
    role: str
    phone: Optional[str] = None
    hourly_rate: Optional[int] = None
    is_active: bool = True


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeOut(EmployeeBase):
    id: int

    class Config:
        orm_mode = True


class ShiftBase(BaseModel):
    date: date
    start_time: time_type
    end_time: time_type
    position: str
    employee_id: Optional[int] = None


class ShiftCreate(ShiftBase):
    pass


class ShiftOut(ShiftBase):
    id: int
    employee: Optional[EmployeeOut] = None

    class Config:
        orm_mode = True


class TimeOffRequestBase(BaseModel):
    date: date
    reason: Optional[str] = None


class TimeOffRequestCreate(TimeOffRequestBase):
    employee_id: int


class TimeOffRequestOut(TimeOffRequestBase):
    id: int
    status: str
    employee: EmployeeOut

    class Config:
        orm_mode = True


# ----- DB session dependency ----- #

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----- FastAPI app ----- #

Base.metadata.create_all(bind=engine)

app = FastAPI(title="1071 Coffee Lounge Shift App")

# Static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


# ---- Employee endpoints ---- #

@app.post("/api/employees/", response_model=EmployeeOut)
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    db_employee = Employee(**employee.dict())
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee


@app.get("/api/employees/", response_model=List[EmployeeOut])
def list_employees(only_active: bool = True, db: Session = Depends(get_db)):
    q = db.query(Employee)
    if only_active:
        q = q.filter(Employee.is_active == True)
    return q.order_by(Employee.full_name).all()


@app.get("/api/employees/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


# ---- Shift endpoints ---- #

@app.post("/api/shifts/", response_model=ShiftOut)
def create_shift(shift: ShiftCreate, db: Session = Depends(get_db)):
    if shift.employee_id:
        emp = db.query(Employee).filter(
            Employee.id == shift.employee_id,
            Employee.is_active == True
        ).first()
        if not emp:
            raise HTTPException(status_code=400, detail="Invalid employee_id")
    db_shift = Shift(**shift.dict())
    db.add(db_shift)
    db.commit()
    db.refresh(db_shift)
    return db_shift


@app.get("/api/shifts/", response_model=List[ShiftOut])
def list_shifts(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Shift)

    if start_date:
        q = q.filter(Shift.date >= start_date)
    if end_date:
        q = q.filter(Shift.date <= end_date)
    if employee_id:
        q = q.filter(Shift.employee_id == employee_id)

    return q.order_by(Shift.date, Shift.start_time).all()


@app.get("/api/schedule/week/", response_model=List[ShiftOut])
def get_week_schedule(any_date_in_week: date, db: Session = Depends(get_db)):
    weekday = any_date_in_week.weekday()  # 0 = Monday
    monday = any_date_in_week.fromordinal(any_date_in_week.toordinal() - weekday)
    sunday = any_date_in_week.fromordinal(monday.toordinal() + 6)

    q = db.query(Shift).filter(
        Shift.date >= monday,
        Shift.date <= sunday,
    )
    return q.order_by(Shift.date, Shift.start_time).all()


# ---- Time off endpoints ---- #

@app.post("/api/timeoff/", response_model=TimeOffRequestOut)
def create_timeoff(req: TimeOffRequestCreate, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == req.employee_id).first()
    if not emp:
        raise HTTPException(status_code=400, detail="Invalid employee_id")

    db_req = TimeOffRequest(
        employee_id=req.employee_id,
        date=req.date,
        reason=req.reason,
        status="pending",
    )
    db.add(db_req)
    db.commit()
    db.refresh(db_req)
    return db_req


@app.get("/api/timeoff/", response_model=List[TimeOffRequestOut])
def list_timeoff(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(TimeOffRequest)
    if status:
        q = q.filter(TimeOffRequest.status == status)
    return q.order_by(TimeOffRequest.date).all()


@app.post("/api/timeoff/{request_id}/approve", response_model=TimeOffRequestOut)
def approve_timeoff(request_id: int, db: Session = Depends(get_db)):
    req = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = "approved"
    db.commit()
    db.refresh(req)
    return req


@app.post("/api/timeoff/{request_id}/reject", response_model=TimeOffRequestOut)
def reject_timeoff(request_id: int, db: Session = Depends(get_db)):
    req = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = "rejected"
    db.commit()
    db.refresh(req)
    return req
