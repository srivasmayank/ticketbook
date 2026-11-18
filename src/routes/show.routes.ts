import { Router } from 'express';
import { listShows, getShowSeatMap } from '../controllers/show.controller.js';

export const showRoutes = Router();

showRoutes.get('/', listShows);
showRoutes.get('/:id/seats', getShowSeatMap);
