import { Request, Response } from 'express';
import { prisma } from '../lib/prisma.js';

export async function listMovies(_req: Request, res: Response) {
  const movies = await prisma.movie.findMany({
    include: {
      shows: {
        select: {
          id: true,
          startTime: true,
          endTime: true,
          screen: {
            select: {
              name: true,
              theater: { select: { name: true, city: true } },
            },
          },
        },
      },
    },
  });

  res.json({ data: movies });
}

export async function getMovieById(req: Request, res: Response) {
  const id = req.params.id as string;
  const movie = await prisma.movie.findUnique({
    where: { id },
    include: {
      shows: {
        include: {
          screen: {
            include: { theater: true },
          },
        },
      },
    },
  });

  if (!movie) {
    res.status(404).json({ error: 'Movie not found' });
    return;
  }

  res.json({ data: movie });
}
