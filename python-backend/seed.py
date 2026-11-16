import sys
from datetime import datetime, timedelta
from app.database import engine, Base, SessionLocal
from app.models import (
    User, Movie, Theater, Screen, Seat, Show, ShowSeat, Booking, BookingItem,
    Role, SeatType, SeatStatus
)

def seed():
    print("🌱 Starting Python database seeding...")

    # 1. Create tables if they do not exist
    # Equivalent to `npx prisma db push`
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 2. Users
        alice = User(name="Alice Johnson", email="alice@example.com", role=Role.CUSTOMER)
        bob = User(name="Bob Smith", email="bob@example.com", role=Role.CUSTOMER)
        admin = User(name="Admin Master", email="admin@ticketbook.com", role=Role.ADMIN)

        db.add_all([alice, bob, admin])
        db.commit()
        db.refresh(alice)
        db.refresh(bob)
        print("✅ Created users: Alice, Bob, Admin")

        # 3. Movie
        movie = Movie(
            title="Interstellar",
            description="A team of explorers travel through a wormhole in space in an attempt to ensure humanity survival.",
            duration_minutes=169
        )
        db.add(movie)
        db.commit()
        db.refresh(movie)
        print(f"✅ Created movie: {movie.title}")

        # 4. Theater & Screen
        theater = Theater(name="PVR IMAX Koramangala", city="Bangalore")
        db.add(theater)
        db.commit()
        db.refresh(theater)

        screen = Screen(name="Screen 1 (IMAX 4K Laser)", theater_id=theater.id)
        db.add(screen)
        db.commit()
        db.refresh(screen)
        print(f"✅ Created theater: {theater.name} -> {screen.name}")

        # 5. Seats (Row A VIP, Row B Premium, Row C Standard - 10 seats each)
        row_configs = [
            ("A", SeatType.VIP, 500.0),
            ("B", SeatType.PREMIUM, 350.0),
            ("C", SeatType.STANDARD, 200.0),
        ]

        created_seats = []
        for row_letter, seat_type, price in row_configs:
            for num in range(1, 11):
                seat = Seat(
                    screen_id=screen.id,
                    row=row_letter,
                    number=num,
                    type=seat_type
                )
                db.add(seat)
                created_seats.append((seat, price))

        db.commit()
        for seat, _ in created_seats:
            db.refresh(seat)
        print(f"✅ Created {len(created_seats)} physical seats across 3 rows")

        # 6. Show (7:00 PM today)
        now = datetime.utcnow()
        start_time = now.replace(hour=19, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=movie.duration_minutes)

        show = Show(
            movie_id=movie.id,
            screen_id=screen.id,
            start_time=start_time,
            end_time=end_time
        )
        db.add(show)
        db.commit()
        db.refresh(show)
        print(f"✅ Created show: {movie.title} (Show ID: {show.id})")

        # 7. Generate dynamic ShowSeats
        for seat, price in created_seats:
            show_seat = ShowSeat(
                show_id=show.id,
                seat_id=seat.id,
                status=SeatStatus.AVAILABLE,
                price=price
            )
            db.add(show_seat)

        db.commit()
        print(f"✅ Generated {len(created_seats)} available ShowSeats for show {show.id}")
        print("🎉 Seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during seeding: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed()
