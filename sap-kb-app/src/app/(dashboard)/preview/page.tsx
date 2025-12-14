"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getApprovedErrors } from "@/lib/actions";
import { LOG_CATEGORIES, LOG_SUBCATEGORIES } from "@/lib/constants";
import { Search } from "lucide-react";

export default function PreviewPage() {
    const [errors, setErrors] = useState<any[]>([]);
    const [search, setSearch] = useState("");

    useEffect(() => {
        getApprovedErrors().then(setErrors);
    }, []);

    const getCategoryLabel = (id: number) => LOG_CATEGORIES.find((c) => c.id === id)?.label || id;
    const getSubcategoryLabel = (catId: number, subId: number) =>
        LOG_SUBCATEGORIES[catId]?.find((s) => s.id === subId)?.label || subId || "-";

    const filteredErrors = errors.filter((error) =>
        (error.error_code || '').toLowerCase().includes(search.toLowerCase()) ||
        (error.error_description || '').toLowerCase().includes(search.toLowerCase()) ||
        (error.module || '').toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Preview Errors</h1>
                    <p className="text-muted-foreground">Search and view approved knowledge base entries</p>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            type="search"
                            placeholder="Search by issue name, description, or module..."
                            className="pl-8 max-w-md"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Module</TableHead>
                                    <TableHead>Issue Name</TableHead>
                                    <TableHead className="w-[300px]">Description</TableHead>
                                    <TableHead>Solution Type</TableHead>
                                    <TableHead className="w-[300px]">Solution</TableHead>
                                    <TableHead>Expert Comment</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredErrors.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center h-24 text-muted-foreground">
                                            No errors found.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredErrors.map((error, index) => (
                                        <TableRow key={index}>
                                            <TableCell className="font-medium">{error.module}</TableCell>
                                            <TableCell>{error.error_code}</TableCell>
                                            <TableCell className="truncate max-w-[300px]" title={error.error_description}>{error.error_description}</TableCell>
                                            <TableCell>{error.solution_type}</TableCell>
                                            <TableCell className="truncate max-w-[300px]" title={error.steps_to_resolve}>{error.steps_to_resolve}</TableCell>
                                            <TableCell className="truncate max-w-[200px]" title={error.expert_comment}>{error.expert_comment || '-'}</TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
