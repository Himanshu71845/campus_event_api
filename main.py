from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlmodel import Session, select, func

from database import engine, create_db_and_tables
from models import (
    Event,
    EventCreate,
    EventUpdate,
    Reservation,
    ReservationCreate
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Campus Event Seat Reservation API",
    lifespan=lifespan
)


# ---------------------------------------------------
# EVENT APIs
# ---------------------------------------------------

# 1. POST /events
@app.post("/events", response_model=Event)
def create_event(event: EventCreate):

    if event.capacity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Event capacity must be greater than 0"
        )

    if event.status not in ["Open", "Closed"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be Open or Closed"
        )

    if not event.title.strip():
        raise HTTPException(
            status_code=400,
            detail="Event title must not be empty"
        )

    db_event = Event.model_validate(event)

    with Session(engine) as session:
        session.add(db_event)
        session.commit()
        session.refresh(db_event)

        return db_event


# 2. GET /events
@app.get("/events", response_model=list[Event])
def get_events():

    with Session(engine) as session:
        events = session.exec(
            select(Event)
        ).all()

        return events


# 3. GET /events/{event_id}
@app.get("/events/{event_id}", response_model=Event)
def get_event(event_id: int):

    with Session(engine) as session:
        event = session.get(Event, event_id)

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )

        return event


# 4. PUT /events/{event_id}
@app.put("/events/{event_id}", response_model=Event)
def update_event(
    event_id: int,
    event_update: EventUpdate
):

    with Session(engine) as session:

        event = session.get(Event, event_id)

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )

        # Check capacity
        if event_update.capacity is not None:

            if event_update.capacity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Event capacity must be greater than 0"
                )

            booked = session.exec(
                select(func.count(Reservation.id))
                .where(Reservation.event_id == event_id)
            ).one()

            if event_update.capacity < booked:
                raise HTTPException(
                    status_code=400,
                    detail=f"Capacity cannot be less than existing reservations ({booked})"
                )

        # Check status
        if event_update.status is not None:

            if event_update.status not in ["Open", "Closed"]:
                raise HTTPException(
                    status_code=400,
                    detail="Status must be Open or Closed"
                )

        # Check title
        if event_update.title is not None:

            if not event_update.title.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Event title must not be empty"
                )

        update_data = event_update.model_dump(
            exclude_unset=True
        )

        for key, value in update_data.items():
            setattr(event, key, value)

        session.add(event)
        session.commit()
        session.refresh(event)

        return event


# 5. DELETE /events/{event_id}
@app.delete("/events/{event_id}")
def delete_event(event_id: int):

    with Session(engine) as session:

        event = session.get(Event, event_id)

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )

        # Delete associated reservations first
        reservations = session.exec(
            select(Reservation)
            .where(Reservation.event_id == event_id)
        ).all()

        for reservation in reservations:
            session.delete(reservation)

        session.delete(event)
        session.commit()

        return {
            "message": "Event deleted successfully"
        }


# ---------------------------------------------------
# RESERVATION APIs
# ---------------------------------------------------

# 6. POST /events/{event_id}/reserve
@app.post(
    "/events/{event_id}/reserve",
    response_model=Reservation
)
def create_reservation(
    event_id: int,
    reservation_data: ReservationCreate
):

    if not reservation_data.student_name.strip():
        raise HTTPException(
            status_code=400,
            detail="Student name must not be empty"
        )

    with Session(engine) as session:

        # Check event
        event = session.get(Event, event_id)

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )

        # Check status
        if event.status != "Open":
            raise HTTPException(
                status_code=400,
                detail="Reservations are closed for this event"
            )

        # Count reservations
        booked = session.exec(
            select(func.count(Reservation.id))
            .where(Reservation.event_id == event_id)
        ).one()

        # Check capacity
        if booked >= event.capacity:
            raise HTTPException(
                status_code=400,
                detail="Event is full. No seats available"
            )

        reservation = Reservation(
            event_id=event_id,
            student_name=reservation_data.student_name,
            roll_number=reservation_data.roll_number,
            email=reservation_data.email
        )

        session.add(reservation)
        session.commit()
        session.refresh(reservation)

        return reservation


# 7. GET /events/{event_id}/reservations
@app.get(
    "/events/{event_id}/reservations",
    response_model=list[Reservation]
)
def get_reservations(event_id: int):

    with Session(engine) as session:

        event = session.get(Event, event_id)

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )

        reservations = session.exec(
            select(Reservation)
            .where(Reservation.event_id == event_id)
        ).all()

        return reservations


# 8. DELETE /reservations/{reservation_id}
@app.delete("/reservations/{reservation_id}")
def cancel_reservation(reservation_id: int):

    with Session(engine) as session:

        reservation = session.get(
            Reservation,
            reservation_id
        )

        if not reservation:
            raise HTTPException(
                status_code=404,
                detail="Reservation not found"
            )

        session.delete(reservation)
        session.commit()

        return {
            "message": "Reservation cancelled successfully"
        }


# 9. GET /events/{event_id}/availability
@app.get("/events/{event_id}/availability")
def get_availability(event_id: int):

    with Session(engine) as session:

        event = session.get(Event, event_id)

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )

        booked = session.exec(
            select(func.count(Reservation.id))
            .where(Reservation.event_id == event_id)
        ).one()

        remaining = event.capacity - booked

        return {
            "capacity": event.capacity,
            "booked": booked,
            "remaining": remaining
        }