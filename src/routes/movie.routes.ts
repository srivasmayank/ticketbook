import { Router } from 'express';
import { listMovies, getMovieById } from '../controllers/movie.controller.js';

export const movieRoutes = Router();

movieRoutes.get('/', listMovies);
movieRoutes.get('/:id', getMovieById);
