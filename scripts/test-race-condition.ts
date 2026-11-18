import { prisma } from '../src/lib/prisma.js';

async function runRaceConditionTest() {
  console.log('===============================================================');
  console.log('🧪 CONCURRENCY LAB: Testing the Naive "Check-Then-Act" Booking');
  console.log('===============================================================\n');

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
    data: { status: 'AVAILABLE' },
  });
  console.log('🔄 Target seat reset to status: AVAILABLE\n');

  console.log('⚡ Firing 2 simultaneous booking requests for Seat A1...');
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

  const url = 'http://localhost:3000/api/bookings';

  // Fire both requests concurrently using Promise.all
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
  console.log(`   Booking ID: ${bodyAlice.data?.id || 'None'} | Message: ${bodyAlice.error || bodyAlice.message}`);
  console.log(`👨 Bob Response:   HTTP ${resBob.status}`);
  console.log(`   Booking ID: ${bodyBob.data?.id || 'None'} | Message: ${bodyBob.error || bodyBob.message}\n`);

  // Query Database to inspect actual state
  const bookingItems = await prisma.bookingItem.findMany({
    where: { showSeatId: targetSeat.id },
    include: {
      booking: {
        include: { user: true },
      },
    },
  });

  console.log('---------------------------------------------------------------');
  console.log('📊 DATABASE REALITY CHECK:');
  console.log(`   Total booking records created for Seat A1: ${bookingItems.length}`);
  bookingItems.forEach((item, index) => {
    console.log(`   [Booking ${index + 1}]: User "${item.booking.user.name}" (ID: ${item.bookingId})`);
  });
  console.log('---------------------------------------------------------------\n');

  if (bookingItems.length > 1) {
    console.log('🚨 DISASTER! DOUBLE BOOKING CONFIRMED!');
    console.log('   The naive Check-Then-Act pattern failed completely under concurrent load.');
    console.log('   Both Alice and Bob were charged and both were issued tickets for Seat A1.');
    console.log('   👉 This is why Phase 3 (Database-Level Locking) is mandatory!\n');
  } else if (bookingItems.length === 1) {
    console.log('✅ Only 1 booking created (concurrency race was won by one thread).');
  } else {
    console.log('❓ Unexpected state: 0 bookings created.');
  }

  await prisma.$disconnect();
}

runRaceConditionTest().catch(console.error);
