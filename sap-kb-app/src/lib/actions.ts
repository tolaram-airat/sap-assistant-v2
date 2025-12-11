"use server";

import fs from "fs/promises";
import path from "path";

const DATA_FILE = path.join(process.cwd(), "errors.json");

export async function getApprovedErrors() {
    try {
        const data = await fs.readFile(DATA_FILE, "utf-8");
        return JSON.parse(data);
    } catch (error) {
        return [];
    }
}

export async function saveApprovedError(entry: any) {
    const errors = await getApprovedErrors();
    errors.push(entry);
    await fs.writeFile(DATA_FILE, JSON.stringify(errors, null, 2));
    return { success: true };
}
