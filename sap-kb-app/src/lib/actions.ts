"use server";

import { db } from "./db";
import { KBError } from "./types";
import { revalidatePath } from "next/cache";

// --- GETTERS ---

export async function getApprovedErrors(): Promise<KBError[]> {
    try {
        const { rows } = await db.sql`SELECT * FROM kb_errors WHERE status = 'APPROVED' ORDER BY id DESC`; // Use raw SQL
        // simple casting as we don't have an ORM
        return rows as unknown as KBError[];
    } catch (error) {
        console.error("Failed to fetch approved errors:", error);
        return [];
    }
}

export async function getPendingErrors(): Promise<KBError[]> {
    try {
        const { rows } = await db.sql`SELECT * FROM kb_errors WHERE status = 'PENDING' ORDER BY id DESC`;
        return rows as unknown as KBError[];
    } catch (error) {
        console.error("Failed to fetch pending errors:", error);
        return [];
    }
}

export async function getPendingCount(): Promise<number> {
    try {
        const { rows } = await db.sql`SELECT COUNT(*) FROM kb_errors WHERE status = 'PENDING'`;
        return parseInt(rows[0].count);
    } catch (error) {
        return 0;
    }
}


// --- ACTIONS ---

export async function savePendingError(entry: Omit<KBError, 'id' | 'status'>) {
    try {
        await db.sql`
      INSERT INTO kb_errors (
        error_code, error_description, module, solution_type, 
        steps_to_resolve, expert_comment, status
      ) VALUES (
        ${entry.error_code}, ${entry.error_description}, ${entry.module}, ${entry.solution_type},
        ${entry.steps_to_resolve}, ${entry.expert_comment || ''}, 'PENDING'
      )
    `;
        revalidatePath("/approval");
        revalidatePath("/"); // Update dashboard count
        return { success: true };
    } catch (error) {
        console.error("Failed to save error:", error);
        throw new Error("Failed to save error to database");
    }
}

export async function approveError(id: number, approvedBy: string) {
    try {
        await db.sql`
            UPDATE kb_errors 
            SET status = 'APPROVED', approved_by = ${approvedBy}, approved_at = NOW()
            WHERE id = ${id}
        `;
        revalidatePath("/approval");
        revalidatePath("/");
        revalidatePath("/preview");
        return { success: true };
    } catch (error) {
        console.error("Failed to approve error:", error);
        return { success: false, error: "Database error" };
    }
}

export async function rejectError(id: number) {
    try {
        await db.sql`DELETE FROM kb_errors WHERE id = ${id}`;
        revalidatePath("/approval");
        return { success: true };
    } catch (error) {
        return { success: false, error: "Database error" };
    }
}

// --- EXPORT ---

export async function exportErrorsAsJSON() {
    const errors = await getApprovedErrors();

    const transformedErrors = errors.map(error => {
        // defined regex to extract [Category: 123, Sub: 456]
        const categoryMatch = error.expert_comment?.match(/\[Category: (\d+), Sub: (.*?)\]/);
        const logcategory = categoryMatch ? parseInt(categoryMatch[1]) : null;
        const logsubcategory = categoryMatch && categoryMatch[2] !== 'None' ? parseInt(categoryMatch[2]) : null;

        // Remove the category tag from the notes/expert_comment if desired, 
        // or keep it. User didn't specify, but usually cleaner to remove or keep as is.
        // Let's keep it as is in 'notes' for now to be safe, or just map expert_comment to notes.

        return {
            id: error.id,
            module: error.module,
            issuename: error.error_code,
            issuedescription: error.error_description,
            solutiontype: error.solution_type,
            stepbystep: error.steps_to_resolve,
            logcategory: logcategory,
            logsubcategory: logsubcategory,
            notes: error.expert_comment,
            status: "approved", // User requested 'n' implies 'approved'? Or just generic. Database says APPROVED.
            createdAt: error.created_at,
            comments: [], // User requested empty array
            approvedAt: error.approved_at
        };
    });

    return JSON.stringify(transformedErrors, null, 2);
}

