"use client";

import { useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

import { getPendingErrors, approveError, rejectError } from "@/lib/actions";
import { auth } from "@/auth";
import { useSession } from "next-auth/react";
import { LOG_CATEGORIES, LOG_SUBCATEGORIES } from "@/lib/constants";
import { CheckCircle, XCircle } from "lucide-react";

export default function ApprovalPage() {
    const { data: session } = useSession();
    const [pendingErrors, setPendingErrors] = useState<any[]>([]);
    const [commentInputs, setCommentInputs] = useState<Record<string, string>>({});

    useEffect(() => {
        // Fetch pending errors from server
        getPendingErrors().then(setPendingErrors);
    }, []);

    const getCategoryLabel = (id: number) => LOG_CATEGORIES.find((c) => c.id === id)?.label || id;
    const getSubcategoryLabel = (catId: number, subId: number) =>
        LOG_SUBCATEGORIES[catId]?.find((s) => s.id === subId)?.label || subId || "-";

    const handleApprove = async (error: any) => {
        try {
            const userName = session?.user?.name || "Admin";
            const result = await approveError(error.id, userName);
            if (result.success) {
                setPendingErrors(prev => prev.filter(e => e.id !== error.id));
                toast.success(`Error "${error.error_code || error.issuename}" approved successfully.`);
            } else {
                toast.error("Failed to approve error.");
            }
        } catch (err) {
            console.error(err);
            toast.error("Failed to approve error.");
        }
    };

    const handleDecline = async (id: number) => {
        try {
            const result = await rejectError(id);
            if (result.success) {
                setPendingErrors(prev => prev.filter(e => e.id !== id));
                toast.info("Error request declined.");
            } else {
                toast.error("Failed to decline error.");
            }
        } catch (err) {
            console.error(err);
            toast.error("Failed to decline error.");
        }
    };

    const handleApproveAll = async () => {
        const userName = session?.user?.name || "Admin";
        for (const error of pendingErrors) {
            await approveError(error.id, userName);
        }
        setPendingErrors([]);
        toast.success("All pending errors approved.");
    };

    const handleDeclineAll = async () => {
        for (const error of pendingErrors) {
            await rejectError(error.id);
        }
        setPendingErrors([]);
        toast.info("All pending errors declined.");
    };

    const handleAddComment = (id: string) => {
        const text = commentInputs[id];
        if (!text) return;

        const newPending = pendingErrors.map(e => {
            if (e.id === id) {
                return {
                    ...e,
                    comments: [...(e.comments || []), {
                        id: crypto.randomUUID(),
                        author: "Lead",
                        text,
                        timestamp: new Date().toISOString()
                    }]
                };
            }
            return e;
        });

        setPendingErrors(newPending);
        localStorage.setItem("sap-kb-pending", JSON.stringify(newPending));
        setCommentInputs({ ...commentInputs, [id]: "" });
        toast.success("Comment added.");
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Approval Queue</h1>
                    <p className="text-muted-foreground">Review and approve pending errors ({pendingErrors.length})</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" className="text-red-600 border-red-200 hover:bg-red-50" onClick={handleDeclineAll} disabled={pendingErrors.length === 0}>
                        Decline All
                    </Button>
                    <Button className="bg-green-600 hover:bg-green-700 text-white" onClick={handleApproveAll} disabled={pendingErrors.length === 0}>
                        Approve All
                    </Button>
                </div>
            </div>

            {pendingErrors.length === 0 ? (
                <Card>
                    <CardContent className="flex flex-col items-center justify-center h-40 text-muted-foreground">
                        <CheckCircle className="h-10 w-10 mb-2 opacity-20" />
                        <p>No errors waiting for approval.</p>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-4">
                    {pendingErrors.map((error) => (
                        <Card key={error.id} className="overflow-hidden">
                            <CardHeader className="flex flex-row items-start justify-between bg-muted/30 pb-4">
                                <div className="space-y-1">
                                    <CardTitle className="text-xl">{error.issuename}</CardTitle>
                                    <CardDescription>
                                        <span className="font-semibold text-primary">{error.module}</span> • {getCategoryLabel(error.logcategory)} {error.logsubcategory ? ` / ${getSubcategoryLabel(error.logcategory, error.logsubcategory)}` : ""}
                                    </CardDescription>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white" onClick={() => handleApprove(error)}>
                                        <CheckCircle className="mr-1 h-4 w-4" /> Approve
                                    </Button>
                                    <Button size="sm" variant="outline" className="text-red-600 border-red-200 hover:bg-red-50" onClick={() => handleDecline(error.id)}>
                                        <XCircle className="mr-1 h-4 w-4" /> Decline
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent className="pt-4 grid gap-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <h4 className="text-sm font-semibold mb-1">Description</h4>
                                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">{error.issuedescription}</p>
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-semibold mb-1">Solution ({error.solutiontype})</h4>
                                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">{error.stepbystep}</p>
                                    </div>
                                </div>

                                <div className="text-xs text-muted-foreground pt-2">
                                    <strong>Notes:</strong> {error.notes || "None"}
                                </div>

                                <Accordion type="single" collapsible>
                                    <AccordionItem value="comments" className="border-none">
                                        <AccordionTrigger className="py-2 text-sm">Comments ({error.comments?.length || 0})</AccordionTrigger>
                                        <AccordionContent>
                                            <div className="space-y-3 pl-2">
                                                {error.comments?.map((c: any) => (
                                                    <div key={c.id} className="text-sm bg-muted/50 p-2 rounded">
                                                        <div className="flex justify-between text-xs text-muted-foreground mb-1">
                                                            <span>{c.author}</span>
                                                            <span>{new Date(c.timestamp).toLocaleString()}</span>
                                                        </div>
                                                        <p>{c.text}</p>
                                                    </div>
                                                ))}
                                                <div className="flex gap-2 mt-2">
                                                    <Input
                                                        placeholder="Add a comment..."
                                                        value={commentInputs[error.id] || ""}
                                                        onChange={(e) => setCommentInputs({ ...commentInputs, [error.id]: e.target.value })}
                                                        onKeyDown={(e) => e.key === 'Enter' && handleAddComment(error.id)}
                                                    />
                                                    <Button size="sm" onClick={() => handleAddComment(error.id)}>Post</Button>
                                                </div>
                                            </div>
                                        </AccordionContent>
                                    </AccordionItem>
                                </Accordion>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
