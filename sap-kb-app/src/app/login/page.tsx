'use client';

import { authenticate } from '@/lib/auth-actions';
import { useActionState } from 'react';
import { useFormStatus } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle } from 'lucide-react';

export default function LoginPage() {
    const [errorMessage, dispatch] = useActionState(authenticate, undefined);

    return (
        <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-900">
            <Card className="w-full max-w-sm">
                <CardHeader>
                    <CardTitle className="text-2xl">Login</CardTitle>
                    <CardDescription>
                        Enter your credentials to access the SAP KB App.
                    </CardDescription>
                </CardHeader>
                <form action={dispatch}>
                    <CardContent className="grid gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                name="email"
                                placeholder="m@example.com"
                                required
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="password">Password</Label>
                            <Input id="password" type="password" name="password" required />
                        </div>
                        <div className="flex items-end space-x-1" aria-live="polite" aria-atomic="true">
                            {errorMessage && (
                                <>
                                    <AlertCircle className="h-5 w-5 text-red-500" />
                                    <p className="text-sm text-red-500">{errorMessage}</p>
                                </>
                            )}
                        </div>
                    </CardContent>
                    <CardFooter>
                        <LoginButton />
                    </CardFooter>
                </form>
            </Card>
        </div>
    );
}

function LoginButton() {
    const { pending } = useFormStatus();

    return (
        <Button className="w-full" aria-disabled={pending}>
            {pending ? 'Logging in...' : 'Sign in'}
        </Button>
    );
}
