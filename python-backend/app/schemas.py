from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# 🎓 Node.js vs Python Request/Response Validation:
# In Node.js / TypeScript:
#   const BookingCreateSchema = z.object({
#     userId: z.string(),
#     showId: z.string(),
#     showSeatIds: z.array(z.string()).min(1)
#   });
#
# In Python / FastAPI:
#   Pydantic's `BaseModel` handles both TypeScript-like type checking AND Zod-like runtime validation!

class BookingCreateRequest(BaseModel):
    userId: str = Field(..., description="ID of the user creating the booking")
    showId: str = Field(..., description="ID of the show being booked")
    showSeatIds: List[str] = Field(..., min_length=1, description="List of ShowSeat IDs to book")

class SeatMapItem(BaseModel):
    showSeatId: str
    seatId: str
    row: str
    number: int
    type: str
    price: float
    status: str

class SeatMapResponse(BaseModel):
    showId: str
    movie: str
    screen: str
    theater: str
    startTime: datetime
    totalSeats: int
    availableSeats: int
    seats: List[SeatMapItem]
