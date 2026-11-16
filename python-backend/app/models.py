import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

# 🎓 Node.js vs Python Enum:
# In Prisma:
#   enum SeatStatus { AVAILABLE, LOCKED, BOOKED }
# In Python:
#   Use Python's standard `enum.Enum` combined with SQLAlchemy's `Enum` type.

class Role(str, PyEnum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"

class SeatType(str, PyEnum):
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    VIP = "VIP"

class SeatStatus(str, PyEnum):
    AVAILABLE = "AVAILABLE"
    LOCKED = "LOCKED"
    BOOKED = "BOOKED"

class BookingStatus(str, PyEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

def generate_uuid() -> str:
    return str(uuid.uuid4())

# ==========================================
# 1. PHYSICAL ASSET TIER (Permanent Master Data)
# ==========================================

class Theater(Base):
    __tablename__ = "theaters"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    screens = relationship("Screen", back_populates="theater", cascade="all, delete-orphan")

class Screen(Base):
    __tablename__ = "screens"

    id = Column(String, primary_key=True, default=generate_uuid)
    theater_id = Column(String, ForeignKey("theaters.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    theater = relationship("Theater", back_populates="screens")
    seats = relationship("Seat", back_populates="screen", cascade="all, delete-orphan")
    shows = relationship("Show", back_populates="screen")

class Seat(Base):
    __tablename__ = "seats"

    id = Column(String, primary_key=True, default=generate_uuid)
    screen_id = Column(String, ForeignKey("screens.id", ondelete="CASCADE"), nullable=False)
    row = Column(String, nullable=False)         # e.g. "A", "B"
    number = Column(Integer, nullable=False)      # e.g. 1, 2, 3
    type = Column(Enum(SeatType), default=SeatType.STANDARD, nullable=False)

    screen = relationship("Screen", back_populates="seats")
    show_seats = relationship("ShowSeat", back_populates="seat")

    __table_args__ = (
        UniqueConstraint("screen_id", "row", "number", name="uq_screen_row_number"),
    )

# ==========================================
# 2. SCHEDULING TIER (Events & Showtimes)
# ==========================================

class Movie(Base):
    __tablename__ = "movies"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    shows = relationship("Show", back_populates="movie")

class Show(Base):
    __tablename__ = "shows"

    id = Column(String, primary_key=True, default=generate_uuid)
    movie_id = Column(String, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    screen_id = Column(String, ForeignKey("screens.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    movie = relationship("Movie", back_populates="shows")
    screen = relationship("Screen", back_populates="shows")
    show_seats = relationship("ShowSeat", back_populates="show", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="show")

# ==========================================
# 3. DYNAMIC INVENTORY TIER (Seat status per show)
# ==========================================

class ShowSeat(Base):
    __tablename__ = "show_seats"

    id = Column(String, primary_key=True, default=generate_uuid)
    show_id = Column(String, ForeignKey("shows.id", ondelete="CASCADE"), nullable=False)
    seat_id = Column(String, ForeignKey("seats.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(SeatStatus), default=SeatStatus.AVAILABLE, nullable=False)
    price = Column(Float, default=250.0, nullable=False)
    version = Column(Integer, default=1, nullable=False)  # For optimistic locking
    locked_until = Column(DateTime, nullable=True)

    show = relationship("Show", back_populates="show_seats")
    seat = relationship("Seat", back_populates="show_seats")
    booking_items = relationship("BookingItem", back_populates="show_seat")

    __table_args__ = (
        UniqueConstraint("show_id", "seat_id", name="uq_show_seat"),
    )

# ==========================================
# 4. USERS & BOOKINGS TIER
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(Enum(Role), default=Role.CUSTOMER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    bookings = relationship("Booking", back_populates="user")

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    show_id = Column(String, ForeignKey("shows.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    show = relationship("Show", back_populates="bookings")
    items = relationship("BookingItem", back_populates="booking", cascade="all, delete-orphan")

class BookingItem(Base):
    __tablename__ = "booking_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    booking_id = Column(String, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    show_seat_id = Column(String, ForeignKey("show_seats.id", ondelete="CASCADE"), nullable=False)
    price = Column(Float, nullable=False)

    booking = relationship("Booking", back_populates="items")
    show_seat = relationship("ShowSeat", back_populates="booking_items")

    __table_args__ = (
        UniqueConstraint("booking_id", "show_seat_id", name="uq_booking_show_seat"),
    )
