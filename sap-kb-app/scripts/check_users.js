const { db } = require('@vercel/postgres');
require('dotenv').config(); // Load env vars

async function main() {
    const client = await db.connect();
    try {
        const res = await client.sql`SELECT id, email, role, password FROM users`;
        console.log("Current Users in DB:");
        console.log(res.rows);
    } catch (err) {
        console.error("Error querying users:", err.message);
    }
}

main();
