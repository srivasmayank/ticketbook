import dotenv from 'dotenv';
dotenv.config();

import { app } from './app.js';

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`🚀 Ticket Booking Engine listening at http://localhost:${PORT}`);
  console.log(`👉 Health check: http://localhost:${PORT}/health`);
  console.log(`🎬 Movies endpoint: http://localhost:${PORT}/api/movies`);
  console.log(`🎟️ Shows endpoint: http://localhost:${PORT}/api/shows`);
});
