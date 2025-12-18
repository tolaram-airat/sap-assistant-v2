require('dotenv').config();
const { db } = require('@vercel/postgres');
const bcrypt = require('bcrypt');

async function main() {
  const client = await db.connect();

  try {
    // 1. Create Users Table
    await client.sql`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL DEFAULT 'USER',
        name VARCHAR(255)
      );
    `;
    console.log('Created "users" table');

    // 2. Create KB Errors Table
    await client.sql`
      CREATE TABLE IF NOT EXISTS kb_errors (
        id SERIAL PRIMARY KEY,
        error_code VARCHAR(50),
        error_description TEXT,
        module VARCHAR(100),
        solution_type VARCHAR(100),
        steps_to_resolve TEXT,
        expert_comment TEXT,
        status VARCHAR(20) DEFAULT 'PENDING',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(255),
        approved_at TIMESTAMP WITH TIME ZONE,
        approved_by VARCHAR(255)
      );
    `;
    console.log('Created "kb_errors" table');

    // 3. Seed Users
    const users = [
      { email: 'airat.aroyewun@tolaram.com', name: 'Airat Aroyewun', role: 'ADMIN' }, // Entry + Approval
      { email: 'aroyewun.airat@tolaram.com', name: 'Airat Aroyewun', role: 'ADMIN' }, // Alternate format
      { email: 'Sadhwika.Peri@tolaram.com', name: 'Sadhwika Peri', role: 'USER' }, // Entry only
      { email: 'Balaji.Mohandas@tolaram.com', name: 'Balaji Mohandas', role: 'USER' }, // Entry only
      { email: 'sreenivas@tolaram.com', name: 'Sreenivas', role: 'ADMIN' }, // Entry + Approval
      { email: 'benedicta.olorungbade@tolaram.com', name: 'Benedicta Olorungbade', role: 'ADMIN' }, // Entry + Approval
      { email: 'Sureshkumar.Mahadevu@tolaram.com', name: 'Sureshkumar Mahadevu', role: 'ADMIN' }, // Entry + Approval
    ];

    for (const user of users) {
      // Default password for everyone (should be changed later) -> "password123"
      const hashedPassword = await bcrypt.hash('password123', 10);

      const normalizedEmail = user.email.toLowerCase();
      await client.sql`
        INSERT INTO users (email, password, role, name)
        VALUES (${normalizedEmail}, ${hashedPassword}, ${user.role}, ${user.name})
        ON CONFLICT (email) DO UPDATE 
        SET role = ${user.role}, name = ${user.name};
      `; // Upsert to update roles if they change
      console.log(`Seeded user: ${normalizedEmail}`);
    }

  } catch (error) {
    console.error('Error seeding database:', error);
  } finally {
    // client.end(); // @vercel/postgres clients are pooled, usually don't need manual close in script unless standalone
  }
}

main().catch(console.error);
