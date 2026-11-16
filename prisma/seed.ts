import { PrismaClient, Role, SeatType, SeatStatus } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Starting database seeding...');

  // 1. Clean existing records in reverse dependency order
  await prisma.bookingItem.deleteMany();
  await prisma.booking.deleteMany();
  await prisma.showSeat.deleteMany();
  await prisma.show.deleteMany();
  await prisma.seat.deleteMany();
  await prisma.screen.deleteMany();
  await prisma.theater.deleteMany();
  await prisma.movie.deleteMany();
  await prisma.user.deleteMany();

  // 2. Users
  const alice = await prisma.user.create({
    data: {
      name: 'Alice Johnson',
      email: 'alice@example.com',
      role: Role.CUSTOMER,
    },
  });

  const bob = await prisma.user.create({
    data: {
      name: 'Bob Smith',
      email: 'bob@example.com',
      role: Role.CUSTOMER,
    },
  });

  const admin = await prisma.user.create({
    data: {
      name: 'Admin Master',
      email: 'admin@ticketbook.com',
      role: Role.ADMIN,
    },
  });

  console.log('✅ Created users: Alice, Bob, Admin');

  // 3. Movie
  const movie = await prisma.movie.create({
    data: {
      title: 'Interstellar',
      description: 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity survival.',
      durationMinutes: 169,
    },
  });
  console.log(`✅ Created movie: ${movie.title}`);

  // 4. Theater & Screen
  const theater = await prisma.theater.create({
    data: {
      name: 'PVR IMAX Koramangala',
      city: 'Bangalore',
    },
  });

  const screen = await prisma.screen.create({
    data: {
      name: 'Screen 1 (IMAX 4K Laser)',
      theaterId: theater.id,
    },
  });
  console.log(`✅ Created theater: ${theater.name} -> ${screen.name}`);

  // 5. Seats (Row A VIP, Row B Premium, Row C Standard - 10 seats each)
  const rows: { row: string; type: SeatType; price: number }[] = [
    { row: 'A', type: SeatType.VIP, price: 500 },
    { row: 'B', type: SeatType.PREMIUM, price: 350 },
    { row: 'C', type: SeatType.STANDARD, price: 200 },
  ];

  const createdSeats = [];
  for (const { row, type } of rows) {
    for (let num = 1; num <= 10; num++) {
      const seat = await prisma.seat.create({
        data: {
          screenId: screen.id,
          row,
          number: num,
          type,
        },
      });
      createdSeats.push(seat);
    }
  }
  console.log(`✅ Created ${createdSeats.length} physical seats across 3 rows`);

  // 6. Show (Starting at 7:00 PM today)
  const startTime = new Date();
  startTime.setHours(19, 0, 0, 0);
  const endTime = new Date(startTime.getTime() + movie.durationMinutes * 60 * 1000);

  const show = await prisma.show.create({
    data: {
      movieId: movie.id,
      screenId: screen.id,
      startTime,
      endTime,
    },
  });
  console.log(`✅ Created show: ${movie.title} @ ${startTime.toLocaleTimeString()}`);

  // 7. Initialize ShowSeats (Dynamic Inventory)
  for (const seat of createdSeats) {
    const rowConfig = rows.find((r) => r.row === seat.row);
    await prisma.showSeat.create({
      data: {
        showId: show.id,
        seatId: seat.id,
        status: SeatStatus.AVAILABLE,
        price: rowConfig?.price ?? 250,
      },
    });
  }
  console.log(`✅ Generated ${createdSeats.length} available ShowSeats for show ${show.id}`);
  console.log('🎉 Seeding completed successfully!');
}

main()
  .catch((e) => {
    console.error('❌ Error during seeding:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
