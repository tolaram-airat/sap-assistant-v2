import NextAuth from 'next-auth';
import { authConfig } from './auth.config';
import Credentials from 'next-auth/providers/credentials';
import { z } from 'zod';
import { db } from './lib/db';
import bcrypt from 'bcrypt';
import { User } from './lib/types';

async function getUser(email: string): Promise<User | undefined> {
    try {
        const user = await db.sql`SELECT * FROM users WHERE email=${email}`;
        return user.rows[0] as unknown as User;
    } catch (error) {
        console.error('Failed to fetch user:', error);
        throw new Error('Failed to fetch user.');
    }
}

console.log("Checking Env Vars:");
console.log("POSTGRES_URL exists?", !!process.env.POSTGRES_URL);
console.log("AUTH_SECRET exists?", !!process.env.AUTH_SECRET);

export const { handlers, auth, signIn, signOut } = NextAuth({
    ...authConfig,
    secret: process.env.AUTH_SECRET,
    providers: [
        Credentials({
            async authorize(credentials) {
                const parsedCredentials = z
                    .object({ email: z.string().email(), password: z.string().min(6) })
                    .safeParse(credentials);

                if (parsedCredentials.success) {
                    const { email, password } = parsedCredentials.data;
                    const user = await getUser(email);

                    if (!user) return null;

                    // In a real app we would use bcrypt.compare(password, user.password)
                    // But since I salted only 'password123' in the seed script, let's allow that.
                    // IMPORTANT: If you want to use the hashed password from the DB:
                    // const passwordsMatch = await bcrypt.compare(password, user.password as any); 
                    // (Assuming user object has password field which my 'User' type hides, but 'select *' returns it)

                    // Let's do it properly by fetching password too.
                    const userWithPassword = (await db.sql`SELECT * FROM users WHERE email=${email}`).rows[0];
                    const passwordsMatch = await bcrypt.compare(password, userWithPassword.password);

                    if (passwordsMatch) {
                        return {
                            ...user,
                            id: user.id.toString(), // NextAuth expects ID to be a string
                        };
                    }
                }

                console.log('Invalid credentials');
                return null;
            },
        }),
    ],
});
