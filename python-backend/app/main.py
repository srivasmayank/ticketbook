import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from .database import get_db, engine, Base
from .models import (
    Movie, Show, ShowSeat, Seat, Screen, Theater, Booking, BookingItem, User,
    SeatStatus, BookingStatus
)
from .schemas import BookingCreateRequest, SeatMapResponse, SeatMapItem

# In Node.js:
#   const app = express();
# In Python:
#   app = FastAPI();
app = FastAPI(
    title="Ticket Booking Engine (Python / FastAPI)",
    description="Demonstrating Phase 1: Naive CRUD & Concurrency Pitfalls",
    version="1.0.0"
)

# -------------------------------------------------------------
# 1. HEALTH & METRICS
# -------------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok", "runtime": "Python 3.11 / FastAPI", "timestamp": datetime.utcnow().isoformat()}

# -------------------------------------------------------------
# 2. MOVIES ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/movies")
def list_movies(db: Session = Depends(get_db)):
    movies = db.query(Movie).options(
        joinedload(Movie.shows).joinedload(Show.screen)
    ).all()

    return {
        "data": [
            {
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "durationMinutes": m.duration_minutes,
                "showsCount": len(m.shows)
            }
            for m in movies
        ]
    }

# -------------------------------------------------------------
# 3. SHOWS & SEAT MAP ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/shows")
def list_shows(movieId: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Show).options(
        joinedload(Show.movie),
        joinedload(Show.screen)
    )
    if movieId:
        query = query.filter(Show.movie_id == movieId)

    shows = query.all()
    return {
        "data": [
            {
                "id": s.id,
                "movieId": s.movie_id,
                "movieTitle": s.movie.title,
                "screenId": s.screen_id,
                "screenName": s.screen.name,
                "startTime": s.start_time,
                "endTime": s.end_time
            }
            for s in shows
        ]
    }

@app.get("/api/shows/{show_id}/seats")
def get_show_seat_map(show_id: str, db: Session = Depends(get_db)):
    show = db.query(Show).options(
        joinedload(Show.movie),
        joinedload(Show.screen).joinedload(Screen.theater),
        joinedload(Show.show_seats).joinedload(ShowSeat.seat)
    ).filter(Show.id == show_id).first()

    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    # Sort seats in memory by row and seat number
    sorted_show_seats = sorted(
        show.show_seats,
        key=lambda ss: (ss.seat.row, ss.seat.number)
    )

    seat_items = [
        SeatMapItem(
            showSeatId=ss.id,
            seatId=ss.seat_id,
            row=ss.seat.row,
            number=ss.seat.number,
            type=ss.seat.type.value,
            price=ss.price,
            status=ss.status.value
        )
        for ss in sorted_show_seats
    ]

    available_count = sum(1 for s in seat_items if s.status == "AVAILABLE")

    return {
        "data": {
            "showId": show.id,
            "movie": show.movie.title,
            "screen": show.screen.name,
            "theater": show.screen.theater.name if show.screen.theater else "Cinema",
            "startTime": show.start_time,
            "totalSeats": len(seat_items),
            "availableSeats": available_count,
            "seats": seat_items
        }
    }

# -------------------------------------------------------------
# 4. BOOKINGS: NAIVE IMPLEMENTATION (Beginner Pattern)
# -------------------------------------------------------------
@app.post("/api/bookings", status_code=status.HTTP_201_CREATED)
async def create_booking_naive(req: BookingCreateRequest, db: Session = Depends(get_db)):
    """
    🎓 THE NAIVE / BEGINNER BOOKING PATTERN:
    1. Check: Are seats AVAILABLE?
    2. Sleep: 100ms async latency (simulating payment tokenization or network delay)
    3. Act: Mark seats as BOOKED and create Booking record.

    💥 THE SENIOR SDE WARNING:
    In Python's asyncio event loop, `await asyncio.sleep(0.1)` yields control.
    Another concurrent request executes Step 1 before this request executes Step 3.
    Both requests see `AVAILABLE` and both create bookings for the exact same seat!
    """
    # Step 1: Check availability (Naive Read)
    seats = (
        db.query(ShowSeat)
        .options(joinedload(ShowSeat.seat))
        .filter(ShowSeat.id.in_(req.showSeatIds), ShowSeat.show_id == req.showId)
        .all()
    )

    if len(seats) != len(req.showSeatIds):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more selected seats do not exist for this show"
        )

    # Check if any seat is already booked or locked
    unavailable = [s for s in seats if s.status != SeatStatus.AVAILABLE]
    if unavailable:
        seat_labels = ", ".join([f"{s.seat.row}{s.seat.number}" for s in unavailable])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Seats [{seat_labels}] are no longer available"
        )

    # Step 2: Artificial latency window (simulates network / payment tokenization)
    await asyncio.sleep(0.1)

    # Step 3: Act (Update seats & create booking without locks)
    total_amount = sum(s.price for s in seats)

    # Mark as BOOKED
    for s in seats:
        s.status = SeatStatus.BOOKED

    booking = Booking(
        user_id=req.userId,
        show_id=req.showId,
        status=BookingStatus.CONFIRMED,
        total_amount=total_amount
    )
    db.add(booking)
    db.flush()  # Generates booking.id

    for s in seats:
        item = BookingItem(
            booking_id=booking.id,
            show_seat_id=s.id,
            price=s.price
        )
        db.add(item)

    db.commit()
    db.refresh(booking)

    return {
        "message": "Booking created successfully (Naive Mode)",
        "data": {
            "id": booking.id,
            "userId": booking.user_id,
            "showId": booking.show_id,
            "status": booking.status.value,
            "totalAmount": booking.total_amount,
            "createdAt": booking.created_at.isoformat()
        }
    }

# -------------------------------------------------------------
# 5. PHASE 3: OPTIMISTIC LOCKING (Version-Check Pattern)
# -------------------------------------------------------------
@app.post("/api/bookings/optimistic", status_code=status.HTTP_201_CREATED)
async def create_booking_optimistic(req: BookingCreateRequest, db: Session = Depends(get_db)):
    """
    🛡️ PHASE 3: OPTIMISTIC LOCKING PATTERN
    
    How it works:
    1. Read the seats and capture their CURRENT `version` numbers.
    2. Sleep 100ms (simulate network / payment latency).
    3. ATOMIC WRITE: Update each seat ONLY IF its status is still AVAILABLE AND its version has NOT changed.
       SQL generated:
       UPDATE show_seats
       SET status = 'BOOKED', version = version + 1
       WHERE id = :id AND status = 'AVAILABLE' AND version = :captured_version;
    4. If another transaction modified the seat in the meantime, version will mismatch,
       and rows_updated will be 0!
    5. Detect the conflict, rollback, and reject with HTTP 409 Conflict.
    """
    # Step 1: Read seats and their current versions
    seats = (
        db.query(ShowSeat)
        .options(joinedload(ShowSeat.seat))
        .filter(ShowSeat.id.in_(req.showSeatIds), ShowSeat.show_id == req.showId)
        .all()
    )

    if len(seats) != len(req.showSeatIds):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more selected seats do not exist for this show"
        )

    # Initial availability check
    unavailable = [s for s in seats if s.status != SeatStatus.AVAILABLE]
    if unavailable:
        seat_labels = ", ".join([f"{s.seat.row}{s.seat.number}" for s in unavailable])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Seats [{seat_labels}] are already taken"
        )

    # Capture the versions at read-time
    seat_versions = {s.id: s.version for s in seats}

    # Step 2: Artificial latency window (simulates network / payment tokenization)
    await asyncio.sleep(0.1)

    # Step 3: Atomic write with version check
    updated_count = 0
    for s in seats:
        count = (
            db.query(ShowSeat)
            .filter(
                ShowSeat.id == s.id,
                ShowSeat.status == SeatStatus.AVAILABLE,
                ShowSeat.version == seat_versions[s.id]
            )
            .update(
                {
                    ShowSeat.status: SeatStatus.BOOKED,
                    ShowSeat.version: seat_versions[s.id] + 1
                },
                synchronize_session=False
            )
        )
        updated_count += count

    # Step 4: Verify whether ALL requested seats were successfully claimed
    if updated_count != len(seats):
        # 💥 Race detected! Another concurrent request took the seat first!
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Concurrency Conflict: Seat was just booked by another user! Transaction aborted."
        )

    # Step 5: Safely create booking record
    total_amount = sum(s.price for s in seats)
    booking = Booking(
        user_id=req.userId,
        show_id=req.showId,
        status=BookingStatus.CONFIRMED,
        total_amount=total_amount
    )
    db.add(booking)
    db.flush()

    for s in seats:
        item = BookingItem(
            booking_id=booking.id,
            show_seat_id=s.id,
            price=s.price
        )
        db.add(item)

    db.commit()
    db.refresh(booking)

    return {
        "message": "Booking created successfully (Optimistic Locking Mode)",
        "data": {
            "id": booking.id,
            "userId": booking.user_id,
            "showId": booking.show_id,
            "status": booking.status.value,
            "totalAmount": booking.total_amount,
            "createdAt": booking.created_at.isoformat()
        }
    }

# -------------------------------------------------------------
# 6. PHASE 3: PESSIMISTIC LOCKING (Row Lock Pattern)
# -------------------------------------------------------------
@app.post("/api/bookings/pessimistic", status_code=status.HTTP_201_CREATED)
async def create_booking_pessimistic(req: BookingCreateRequest, db: Session = Depends(get_db)):
    """
    🛡️ PHASE 3: PESSIMISTIC ROW-LOCKING PATTERN
    
    How it works:
    1. Query seats using `.with_for_update()`.
       In PostgreSQL, this executes `SELECT ... FOR UPDATE`, placing an exclusive row-level lock.
    2. Concurrent transactions trying to read these rows are paused by the database engine.
    3. We check availability: if already booked, we abort with 409.
    4. We update to BOOKED and commit.
    5. Locks are automatically released when the transaction commits.
    """
    try:
        # Step 1: Query seats with exclusive row locks (FOR UPDATE)
        # Note: with_for_update() locks rows in PostgreSQL/MySQL
        seats = (
            db.query(ShowSeat)
            .filter(ShowSeat.id.in_(req.showSeatIds), ShowSeat.show_id == req.showId)
            .with_for_update()
            .all()
        )

        if len(seats) != len(req.showSeatIds):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more selected seats do not exist for this show"
            )

        unavailable = [s for s in seats if s.status != SeatStatus.AVAILABLE]
        if unavailable:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Seat is already taken"
            )

        # Artificial latency window while lock is held
        await asyncio.sleep(0.1)

        # Step 2: Update seats
        total_amount = sum(s.price for s in seats)
        for s in seats:
            s.status = SeatStatus.BOOKED

        booking = Booking(
            user_id=req.userId,
            show_id=req.showId,
            status=BookingStatus.CONFIRMED,
            total_amount=total_amount
        )
        db.add(booking)
        db.flush()

        for s in seats:
            item = BookingItem(
                booking_id=booking.id,
                show_seat_id=s.id,
                price=s.price
            )
            db.add(item)

        db.commit()
        db.refresh(booking)

        return {
            "message": "Booking created successfully (Pessimistic Locking Mode)",
            "data": {
                "id": booking.id,
                "userId": booking.user_id,
                "showId": booking.show_id,
                "status": booking.status.value,
                "totalAmount": booking.total_amount,
                "createdAt": booking.created_at.isoformat()
            }
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bookings/{booking_id}")
def get_booking(booking_id: str, db: Session = Depends(get_db)):
    booking = db.query(Booking).options(
        joinedload(Booking.user),
        joinedload(Booking.show).joinedload(Show.movie),
        joinedload(Booking.items).joinedload(BookingItem.show_seat).joinedload(ShowSeat.seat)
    ).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    return {
        "data": {
            "id": booking.id,
            "user": {"id": booking.user.id, "name": booking.user.name, "email": booking.user.email},
            "movie": booking.show.movie.title,
            "totalAmount": booking.total_amount,
            "status": booking.status.value,
            "seats": [
                {
                    "row": item.show_seat.seat.row,
                    "number": item.show_seat.seat.number,
                    "price": item.price
                }
                for item in booking.items
            ]
        }
    }
