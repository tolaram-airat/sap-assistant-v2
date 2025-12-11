"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { UploadCloud, FileSpreadsheet, Trash2 } from "lucide-react";
import Papa from "papaparse";

const MOCK_PARSED_DATA = Array.from({ length: 5 }).map((_, i) => ({
    module: "MM",
    issueName: `Bulk Imported Issue #${i + 1}`,
    issueDescription: "This issue was imported via bulk upload.",
    solutionType: "User Guidance",
    stepByStep: "Check the transaction logs.",
    logCategory: 2703,
    logSubcategory: 3476,
    notes: "Imported from Excel",
}));

export default function BulkUploadPage() {
    const [file, setFile] = useState<File | null>(null);
    const [parsedData, setParsedData] = useState<any[]>([]);
    const router = useRouter();

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            setFile(selectedFile);
            setParsedData([]); // Reset

            const toastId = toast.loading("Parsing CSV file...");

            Papa.parse(selectedFile, {
                header: true,
                skipEmptyLines: true,
                complete: (results) => {
                    // Filter out non-fatal errors like delimiter guessing issues if data exists
                    const meaningfulErrors = results.errors.filter(
                        (err) => err.code !== "UndetectableDelimiter" && err.code !== "TooFewFields"
                    );

                    if (meaningfulErrors.length > 0 && results.data.length === 0) {
                        console.error("CSV Parse Errors:", results.errors);
                        toast.error(`Error parsing file: ${meaningfulErrors[0].message}`);
                        toast.dismiss(toastId);
                        return;
                    }

                    if (results.data.length === 0) {
                        toast.error("File appears to be empty.");
                        toast.dismiss(toastId);
                        return;
                    }

                    // Map CSV columns to our schema
                    const validData = results.data.map((row: any) => ({
                        module: row.module || "N/A",
                        issuename: row.issuename || row.issueName || "Untitled Issue",
                        issuedescription: row.issuedescription || row.issueDescription || "No description",
                        solutiontype: row.solutiontype || row.solutionType || "User Guidance",
                        stepbystep: row.stepbystep || row.stepByStep || "No steps provided",
                        logcategory: parseInt(row.logcategory || row.logCategory) || 2703, // Default if missing
                        logsubcategory: parseInt(row.logsubcategory || row.logSubcategory) || null,
                        notes: row.notes || ""
                    }));

                    setParsedData(validData);
                    toast.dismiss(toastId);
                    toast.success(`Successfully parsed ${validData.length} entries.`);
                },
                error: (error) => {
                    toast.dismiss(toastId);
                    toast.error(`Failed to parse file: ${error.message}`);
                }
            });
        }
    };

    const handleClear = () => {
        setFile(null);
        setParsedData([]);
        const input = document.getElementById('file-upload') as HTMLInputElement;
        if (input) input.value = '';
    };

    const handleUpload = () => {
        if (parsedData.length === 0) return;

        // Add ID and timestamps
        const entries = parsedData.map(d => ({
            id: crypto.randomUUID(),
            ...d,
            status: "pending",
            createdAt: new Date().toISOString(),
            comments: []
        }));

        const existing = JSON.parse(localStorage.getItem("sap-kb-pending") || "[]");
        localStorage.setItem("sap-kb-pending", JSON.stringify([...existing, ...entries]));

        toast.success(`${entries.length} errors queued for approval.`);
        router.push("/approval");
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Bulk Upload</h1>
                <p className="text-muted-foreground">Upload a CSV or Excel file with multiple errors</p>
            </div>

            <Card>
                <CardContent className="pt-6">
                    <div className="border-2 border-dashed rounded-lg p-10 flex flex-col items-center justify-center text-center hover:bg-muted/50 transition-colors">
                        <UploadCloud className="h-12 w-12 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-semibold mb-1">Select File</h3>
                        <p className="text-sm text-muted-foreground mb-4">Expected columns: module, issuename, issuedescription, solutiontype...</p>
                        <div className="flex gap-4 items-center">
                            <Input
                                id="file-upload"
                                type="file"
                                accept=".xlsx, .csv"
                                className="max-w-xs cursor-pointer"
                                onChange={handleFileChange}
                            />
                            {file && (
                                <div className="flex items-center gap-2 text-sm bg-blue-50 text-blue-700 px-3 py-1 rounded">
                                    <FileSpreadsheet className="h-4 w-4" />
                                    {file.name}
                                </div>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>

            {parsedData.length > 0 && (
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle>Preview ({parsedData.length} entries)</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="rounded-md border mb-4">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Module</TableHead>
                                        <TableHead>Issue Name</TableHead>
                                        <TableHead>Description</TableHead>
                                        <TableHead>Solution Type</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {parsedData.map((row, i) => (
                                        <TableRow key={i}>
                                            <TableCell>{row.module}</TableCell>
                                            <TableCell>{row.issuename}</TableCell>
                                            <TableCell>{row.issuedescription}</TableCell>
                                            <TableCell>{row.solutiontype}</TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                        <div className="flex gap-2">
                            <Button onClick={handleUpload} className="bg-black text-white hover:bg-gray-800">Send for Approval</Button>
                            <Button variant="outline" onClick={handleClear}>Clear</Button>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
