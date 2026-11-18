import { Request, Response } from 'express';
import { prisma } from '../lib/prisma.js';
import { BookingStatus, SeatStatus } from '@prisma/client';

/**
 * 🎓 PEDAGOGICAL LESSON: The "Naive" Booking Controller
 * 
 * Notice what this function does:
 * 1. Read: checks if the requested seats are currently AVAILABLE.
 * 2. Delay: simulates network / processing latency (100ms).
 * 3. Write: marks seats as BOOKED and creates the booking record.
 * 
 * ⚠️ THE SENIOR SDE WARNING:
 * This is the classic "Check-Then-Act" race condition (Time-of-check to time-of-use - TOCTOU).
 * If two requests arrive at roughly the same time, BOTH requests will execute Step 1,
 * BOTH will see the seats as AVAILABLE, and BOTH will proceed to Step 3.
 * Result: Two users receive confirmation for the EXACT SAME physical seat!
 */
export async function createBookingNaive(req: Request, res: Response) {
  const { userId, showId, showSeatIds } = req.body;

  if (!userId || !showId || !Array.isArray(showSeatIds) || showSeatIds.length === 0) {
    res.status(400).json({ error: 'userId, showId, and a non-empty array of showSeatIds are required' });
    return;
  }

  // Step 1: Check availability (BEGINNER CHECK)
  const seats = await prisma.showSeat.findMany({
    where: {
      id: { in: showSeatIds },
      showId,
    },
    include: { seat: true },
  });

  if (seats.length !== showSeatIds.length) {
    res.status(404).json({ error: 'One or more selected seats do not exist for this show' });
    return;
  }

  // Check if any seat is already booked or locked
  const unavailableSeats = seats.filter((s) => s.status !== SeatStatus.AVAILABLE);
  if (unavailableSeats.length > 0) {
    const seatLabels = unavailableSeats.map((s) => `${s.seat.row}${s.seat.number}`).join(', ');
    res.status(409).json({
      error: `Seats [${seatLabels}] are no longer available`,
    });
    return;
  }

  // Step 2: Artificial latency (Simulating payment tokenization, fraud checks, or network wait)
  // In the real world, database latency or async operations create this exact time window.
  await new Promise((resolve) => setTimeout(resolve, 100));

  // Step 3: Act (Update seats & create booking)
  // 💥 BUG: We did not lock these rows! Another concurrent request could have already booked them!
  const totalAmount = seats.reduce((sum, s) => sum + Number(s.price), 0);

  // Mark seats as BOOKED
  await prisma.showSeat.updateMany({
    where: {
      id: { in: showSeatIds },
    },
    data: {
      status: SeatStatus.BOOKED,
    },
  });

  // Create booking record
  const booking = await prisma.booking.create({
    data: {
      userId,
      showId,
      status: BookingStatus.CONFIRMED,
      totalAmount,
      items: {
        create: seats.map((s) => ({
          showSeatId: s.id,
          price: s.price,
        })),
      },
    },
    include: {
      items: {
        include: {
          showSeat: {
            include: { seat: true },
          },
        },
      },
      show: {
        include: { movie: true },
      },
      user: true,
    },
  });

  res.status(201).json({
    message: 'Booking created successfully (Naive Mode)',
    data: booking,
  });
}

export async function getBookingById(req: Request, res: Response) {
  const id = req.params.id as string;

  const booking = await prisma.booking.findUnique({
    where: { id },
    include: {
      user: { select: { id: true, name: true, email: true } },
      show: {
        include: {
          movie: true,
          screen: { include: { theater: true } },
        },
      },
      items: {
        include: {
          showSeat: {
            include: { seat: true },
          },
        },
      },
    },
  });

  if (!booking) {
    res.status(404).json({ error: 'Booking not found' });
    return;
  }

  res.json({ data: booking });
}

export async function listUserBookings(req: Request, res: Response) {
  const { userId } = req.query;

  if (!userId) {
    res.status(400).json({ error: 'userId query parameter is required' });
    return;
  }

  const bookings = await prisma.booking.findMany({
    where: { userId: String(userId) },
    include: {
      show: {
        include: {
          movie: true,
          screen: { include: { theater: true } },
        },
      },
      items: {
        include: {
          showSeat: {
            include: { seat: true },
          },
        },
      },
    },
    orderBy: { createdAt: 'desc' },
  });

  res.json({ data: bookings });
}
