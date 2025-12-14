import { exportErrorsAsJSON } from "@/lib/actions";

export async function GET() {
    const json = await exportErrorsAsJSON();

    return new Response(json, {
        headers: {
            'Content-Type': 'application/json',
            'Content-Disposition': 'attachment; filename="errors.json"',
        },
    });
}
