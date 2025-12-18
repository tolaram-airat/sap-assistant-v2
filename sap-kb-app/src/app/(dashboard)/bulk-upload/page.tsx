"use client";

import { useState } from "react";
import { savePendingError } from "@/lib/actions";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { UploadCloud, FileSpreadsheet, Trash2 } from "lucide-react";
import Papa from "papaparse";
import * as XLSX from "xlsx";

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

            const toastId = toast.loading("Parsing file...");

            const processData = (data: any[]) => {
                if (data.length === 0) {
                    toast.error("File appears to be empty.");
                    toast.dismiss(toastId);
                    return;
                }

                // Helper to normalize keys (lowercase, remove spaces)
                const normalizeKey = (key: string) => key.toLowerCase().replace(/[^a-z0-9]/g, "");

                const validData = data.map((row: any) => {
                    const normalizedRow: any = {};
                    Object.keys(row).forEach(key => {
                        normalizedRow[normalizeKey(key)] = row[key];
                    });

                    return {
                        module: normalizedRow.module || "N/A",
                        issuename: normalizedRow.issuename || normalizedRow.errorcode || "Untitled Issue",
                        issuedescription: normalizedRow.issuedescription || normalizedRow.errordescription || "No description",
                        solutiontype: normalizedRow.solutiontype || "User Guidance",
                        stepbystep: normalizedRow.stepbystep || normalizedRow.stepstoresolve || "No steps provided",
                        logcategory: parseInt(normalizedRow.logcategory) || 2703,
                        logsubcategory: parseInt(normalizedRow.logsubcategory) || null,
                        notes: normalizedRow.notes || normalizedRow.expertcomment || ""
                    };
                });

                setParsedData(validData);
                toast.dismiss(toastId);
                toast.success(`Successfully parsed ${validData.length} entries.`);
            };

            const fileExtension = selectedFile.name.split('.').pop()?.toLowerCase();

            if (fileExtension === 'csv') {
                Papa.parse(selectedFile, {
                    header: true,
                    skipEmptyLines: true,
                    complete: (results) => {
                        const meaningfulErrors = results.errors.filter(
                            (err) => err.code !== "UndetectableDelimiter" && err.code !== "TooFewFields"
                        );
                        if (meaningfulErrors.length > 0 && results.data.length === 0) {
                            toast.error(`Error parsing file: ${meaningfulErrors[0].message}`);
                            toast.dismiss(toastId);
                            return;
                        }
                        processData(results.data);
                    },
                    error: (error) => {
                        toast.dismiss(toastId);
                        toast.error(`Failed to parse CSV: ${error.message}`);
                    }
                });
            } else {
                // Handle Excel (.xlsx, .xls)
                const reader = new FileReader();
                reader.onload = (e) => {
                    try {
                        const data = e.target?.result;
                        const workbook = XLSX.read(data, { type: 'binary' });
                        const sheetName = workbook.SheetNames[0];
                        const sheet = workbook.Sheets[sheetName];
                        const jsonData = XLSX.utils.sheet_to_json(sheet);
                        processData(jsonData);
                    } catch (error) {
                        toast.dismiss(toastId);
                        toast.error("Failed to parse Excel file.");
                        console.error(error);
                    }
                };
                reader.readAsBinaryString(selectedFile);
            }
        }
    };

    const handleClear = () => {
        setFile(null);
        setParsedData([]);
        const input = document.getElementById('file-upload') as HTMLInputElement;
        if (input) input.value = '';
    };

    const handleUpload = async () => {
        if (parsedData.length === 0) return;

        try {
            // Use Promise.all to save all in parallel
            await Promise.all(parsedData.map(d =>
                savePendingError({
                    module: d.module,
                    error_code: d.issuename,
                    error_description: d.issuedescription,
                    solution_type: d.solutiontype,
                    steps_to_resolve: d.stepbystep,
                    expert_comment: d.notes + `\n\n[Category: ${d.logcategory}, Sub: ${d.logsubcategory || 'None'}]`
                })
            ));

            toast.success(`${parsedData.length} errors queued for approval.`);
            router.push("/approval");
        } catch (error) {
            console.error(error);
            toast.error("Failed to upload errors.");
        }
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
