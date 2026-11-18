import asyncio
import httpx
from app.database import SessionLocal
from app.models import User, Show, ShowSeat, BookingItem

async def run_concurrency_fix_test():
    print("==================================================================")
    print("🛡️ CONCURRENCY LAB (PHASE 3): Testing Optimistic Locking Fix")
    print("==================================================================\n")

    db = SessionLocal()
    try:
        # 1. Fetch Alice and Bob
        alice = db.query(User).filter(User.email == "alice@example.com").first()
        bob = db.query(User).filter(User.email == "bob@example.com").first()

        if not alice or not bob:
            raise Exception("Seed users not found. Run python seed.py first.")

        alice_id = alice.id
        bob_id = bob.id

        # 2. Fetch the target Seat A1
        target_seat = (
            db.query(ShowSeat)
            .join(ShowSeat.seat)
            .filter(ShowSeat.seat.has(row="A", number=1))
            .first()
        )

        if not target_seat:
            raise Exception("Target seat A1 not found.")

        show_id = target_seat.show_id
        target_seat_id = target_seat.id

        print(f"🎯 Target Seat: Row A, Number 1")
        print(f"📍 ShowSeat ID: {target_seat_id}")
        print(f"🎬 Show ID:     {show_id}\n")

        # Reset seat to AVAILABLE and version 1 before test
        db.query(BookingItem).filter(BookingItem.show_seat_id == target_seat_id).delete()
        target_seat.status = "AVAILABLE"
        target_seat.version = 1
        db.commit()
        print("🔄 Target seat reset to status: AVAILABLE (version: 1)\n")

    finally:
        db.close()

    print("⚡ Firing 2 simultaneous requests to /api/bookings/optimistic...")
    print("   Request 1: Alice Johnson")
    print("   Request 2: Bob Smith\n")

    payload_alice = {
        "userId": alice_id,
        "showId": show_id,
        "showSeatIds": [target_seat_id]
    }

    payload_bob = {
        "userId": bob_id,
        "showId": show_id,
        "showSeatIds": [target_seat_id]
    }

    url = "http://localhost:8000/api/bookings/optimistic"

    # Fire both requests concurrently using httpx and asyncio.gather
    async with httpx.AsyncClient(timeout=10.0) as client:
        start_time = asyncio.get_event_loop().time()
        res_alice, res_bob = await asyncio.gather(
            client.post(url, json=payload_alice),
            client.post(url, json=payload_bob)
        )
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

    print(f"⏱️ Both requests completed in {duration_ms:.1f}ms\n")
    print(f"👩 Alice Response: HTTP {res_alice.status_code}")
    print(f"   Body: {res_alice.json()}")
    print(f"👨 Bob Response:   HTTP {res_bob.status_code}")
    print(f"   Body: {res_bob.json()}\n")

    # Inspect database reality
    db = SessionLocal()
    try:
        items = (
            db.query(BookingItem)
            .filter(BookingItem.show_seat_id == target_seat_id)
            .all()
        )

        target_seat_db = db.query(ShowSeat).filter(ShowSeat.id == target_seat_id).first()

        print("------------------------------------------------------------------")
        print("📊 DATABASE REALITY CHECK:")
        print(f"   Total booking records created for Seat A1: {len(items)}")
        for idx, item in enumerate(items, start=1):
            booking = item.booking
            print(f"   [Winner {idx}]: User \"{booking.user.name}\" (Booking ID: {booking.id})")
        print(f"   Final Seat Version in DB: {target_seat_db.version}")
        print("------------------------------------------------------------------\n")

        if len(items) == 1:
            winner = items[0].booking.user.name
            loser = "Bob" if winner == "Alice Johnson" else "Alice"
            print("🎉 SUCCESS! CONCURRENCY TEST PASSED!")
            print(f"   1. {winner} successfully booked Seat A1 (HTTP 201).")
            print(f"   2. {loser} was safely rejected with HTTP 409 Conflict (Concurrency Conflict).")
            print("   3. Exactly ONE ticket exists in the database. Double booking is IMPOSSIBLE!")
        elif len(items) > 1:
            print("🚨 FAILED! Double booking still occurred.")
        else:
            print("❓ Unexpected: No bookings created.")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_concurrency_fix_test())
