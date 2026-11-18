import { Router } from 'express';
import {
  createBookingNaive,
  createBookingOptimistic,
  getBookingById,
  listUserBookings,
} from '../controllers/booking.controller.js';

export const bookingRoutes = Router();

bookingRoutes.post('/', createBookingNaive);
bookingRoutes.post('/optimistic', createBookingOptimistic);
bookingRoutes.get('/', listUserBookings);
bookingRoutes.get('/:id', getBookingById);
