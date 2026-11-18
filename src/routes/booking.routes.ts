import { Router } from 'express';
import { createBookingNaive, getBookingById, listUserBookings } from '../controllers/booking.controller.js';

export const bookingRoutes = Router();

bookingRoutes.post('/', createBookingNaive);
bookingRoutes.get('/', listUserBookings);
bookingRoutes.get('/:id', getBookingById);
