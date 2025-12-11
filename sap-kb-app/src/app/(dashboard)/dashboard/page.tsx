import Link from "next/link";
import { PlusCircle, UploadCloud, CheckSquare, Eye } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";

export default function DashboardPage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Welcome to SAP Error Knowledge Base</h1>
                <p className="text-muted-foreground mt-2">
                    Manage errors for the AI agent with ease. Use the sidebar to navigate through different sections.
                </p>
            </div>

            {/* Main Stats Card */}
            <div className="rounded-xl border bg-primary text-primary-foreground p-8 shadow-sm">
                <div className="flex items-center justify-between">
                    <div className="space-y-1">
                        <h2 className="text-sm font-medium opacity-90">Pending Approvals</h2>
                        <div className="text-5xl font-bold">0</div>
                        <p className="text-sm opacity-90 pt-2">No errors waiting for approval</p>
                    </div>
                    <CheckSquare className="h-16 w-16 opacity-20" />
                </div>
            </div>

            {/* Quick Actions Grid */}
            <div className="grid gap-6 md:grid-cols-2">
                <Link href="/add-single">
                    <Card className="h-full hover:shadow-md transition-shadow cursor-pointer">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                Add Single Error
                            </CardTitle>
                            <CardDescription>
                                Add a single error entry with all required details and submit for approval.
                            </CardDescription>
                        </CardHeader>
                    </Card>
                </Link>
                <Link href="/bulk-upload">
                    <Card className="h-full hover:shadow-md transition-shadow cursor-pointer">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                Bulk Upload
                            </CardTitle>
                            <CardDescription>
                                Upload multiple errors at once using an Excel file for faster data entry.
                            </CardDescription>
                        </CardHeader>
                    </Card>
                </Link>
                <Link href="/approval">
                    <Card className="h-full hover:shadow-md transition-shadow cursor-pointer">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                Approval Queue
                            </CardTitle>
                            <CardDescription>
                                Review and approve pending errors with detailed information and comments.
                            </CardDescription>
                        </CardHeader>
                    </Card>
                </Link>
                <Link href="/preview">
                    <Card className="h-full hover:shadow-md transition-shadow cursor-pointer">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                Preview Errors
                            </CardTitle>
                            <CardDescription>
                                Search and view all approved errors stored in the knowledge base.
                            </CardDescription>
                        </CardHeader>
                    </Card>
                </Link>
            </div>

            {/* System Information */}
            <Card className="bg-blue-50/50 dark:bg-slate-900 border-blue-100 dark:border-slate-800">
                <CardHeader>
                    <CardTitle className="text-lg">System Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-muted-foreground">
                    <p><span className="font-medium text-foreground">Logged in as:</span> consultant</p>
                    <p>All error data is stored securely and converted to JSON format upon approval for integration with the AI agent.</p>
                </CardContent>
            </Card>
        </div>
    );
}
