import { prisma } from '../src/lib/prisma.js';

async function runConcurrencyFixTest() {
  console.log('==================================================================');
  console.log('🛡️ CONCURRENCY LAB (PHASE 3): Testing Optimistic Locking Fix (TS)');
  console.log('==================================================================\n');

  // 1. Fetch Alice and Bob
  const alice = await prisma.user.findUnique({ where: { email: 'alice@example.com' } });
  const bob = await prisma.user.findUnique({ where: { email: 'bob@example.com' } });

  if (!alice || !bob) {
    throw new Error('Seed users not found. Run npm run prisma:seed first.');
  }

  // 2. Fetch the show and find Seat A1
  const show = await prisma.show.findFirst({
    include: {
      showSeats: {
        include: { seat: true },
        where: { seat: { row: 'A', number: 1 } },
      },
    },
  });

  if (!show || show.showSeats.length === 0) {
    throw new Error('Show or Seat A1 not found.');
  }

  const targetSeat = show.showSeats[0];
  console.log(`🎯 Target Seat: Row ${targetSeat.seat.row}, Number ${targetSeat.seat.number}`);
  console.log(`📍 ShowSeat ID: ${targetSeat.id}`);
  console.log(`🎬 Show ID:     ${show.id}\n`);

  // Reset target seat to AVAILABLE before test
  await prisma.bookingItem.deleteMany({ where: { showSeatId: targetSeat.id } });
  await prisma.showSeat.update({
    where: { id: targetSeat.id },
    data: { status: 'AVAILABLE', version: 1 },
  });
  console.log('🔄 Target seat reset to status: AVAILABLE (version: 1)\n');

  console.log('⚡ Firing 2 simultaneous requests to /api/bookings/optimistic...');
  console.log('   Request 1: Alice Johnson');
  console.log('   Request 2: Bob Smith\n');

  const payloadAlice = {
    userId: alice.id,
    showId: show.id,
    showSeatIds: [targetSeat.id],
  };

  const payloadBob = {
    userId: bob.id,
    showId: show.id,
    showSeatIds: [targetSeat.id],
  };

  const url = 'http://localhost:3000/api/bookings/optimistic';

  const startTime = Date.now();
  const [resAlice, resBob] = await Promise.all([
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payloadAlice),
    }),
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payloadBob),
    }),
  ]);
  const duration = Date.now() - startTime;

  const bodyAlice = await resAlice.json();
  const bodyBob = await resBob.json();

  console.log(`⏱️ Both requests completed in ${duration}ms\n`);
  console.log(`👩 Alice Response: HTTP ${resAlice.status}`);
  console.log(`   Body: ${JSON.stringify(bodyAlice)}`);
  console.log(`👨 Bob Response:   HTTP ${resBob.status}`);
  console.log(`   Body: ${JSON.stringify(bodyBob)}\n`);

  // Query Database to inspect actual state
  const bookingItems = await prisma.bookingItem.findMany({
    where: { showSeatId: targetSeat.id },
    include: {
      booking: {
        include: { user: true },
      },
    },
  });

  const seatInDb = await prisma.showSeat.findUnique({ where: { id: targetSeat.id } });

  console.log('------------------------------------------------------------------');
  console.log('📊 DATABASE REALITY CHECK:');
  console.log(`   Total booking records created for Seat A1: ${bookingItems.length}`);
  bookingItems.forEach((item, index) => {
    console.log(`   [Winner ${index + 1}]: User "${item.booking.user.name}" (ID: ${item.bookingId})`);
  });
  console.log(`   Final Seat Version in DB: ${seatInDb?.version}`);
  console.log('------------------------------------------------------------------\n');

  if (bookingItems.length === 1) {
    const winner = bookingItems[0].booking.user.name;
    const loser = winner === 'Alice Johnson' ? 'Bob' : 'Alice';
    console.log('🎉 SUCCESS! CONCURRENCY TEST PASSED!');
    console.log(`   1. ${winner} successfully booked Seat A1 (HTTP 201).`);
    console.log(`   2. ${loser} was safely rejected with HTTP 409 Conflict.`);
    console.log('   3. Exactly ONE ticket exists in the database. Double booking is IMPOSSIBLE!\n');
  } else if (bookingItems.length > 1) {
    console.log('🚨 DISASTER! DOUBLE BOOKING STILL OCCURRED!\n');
  }

  await prisma.$disconnect();
}

runConcurrencyFixTest().catch(console.error);
