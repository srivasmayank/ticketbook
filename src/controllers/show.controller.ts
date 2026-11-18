import { Request, Response } from 'express';
import { prisma } from '../lib/prisma.js';

export async function listShows(req: Request, res: Response) {
  const movieId = req.query.movieId as string | undefined;

  const shows = await prisma.show.findMany({
    where: movieId ? { movieId } : undefined,
    include: {
      movie: { select: { title: true, durationMinutes: true } },
      screen: {
        select: {
          name: true,
          theater: { select: { name: true, city: true } },
        },
      },
    },
    orderBy: { startTime: 'asc' },
  });

  res.json({ data: shows });
}

export async function getShowSeatMap(req: Request, res: Response) {
  const showId = req.params.id as string;

  const show = await prisma.show.findUnique({
    where: { id: showId },
    include: {
      movie: true,
      screen: { include: { theater: true } },
      showSeats: {
        include: {
          seat: true,
        },
      },
    },
  });

  if (!show) {
    res.status(404).json({ error: 'Show not found' });
    return;
  }

  // Sort seats in memory by row and seat number
  const sortedShowSeats = [...show.showSeats].sort((a, b) => {
    if (a.seat.row === b.seat.row) {
      return a.seat.number - b.seat.number;
    }
    return a.seat.row.localeCompare(b.seat.row);
  });

  const seatMap = sortedShowSeats.map((ss) => ({
    showSeatId: ss.id,
    seatId: ss.seatId,
    row: ss.seat.row,
    number: ss.seat.number,
    type: ss.seat.type,
    price: Number(ss.price),
    status: ss.status,
  }));

  res.json({
    data: {
      showId: show.id,
      movie: show.movie.title,
      screen: show.screen.name,
      theater: show.screen.theater.name,
      startTime: show.startTime,
      totalSeats: seatMap.length,
      availableSeats: seatMap.filter((s) => s.status === 'AVAILABLE').length,
      seats: seatMap,
    },
  });
}
