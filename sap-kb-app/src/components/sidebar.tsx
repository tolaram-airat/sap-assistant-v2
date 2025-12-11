"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, PlusCircle, UploadCloud, CheckSquare, Eye, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const menuItems = [
    {
        title: "Dashboard",
        href: "/dashboard",
        icon: LayoutDashboard,
    },
    {
        title: "Add Single Error",
        href: "/add-single",
        icon: PlusCircle,
    },
    {
        title: "Bulk Upload",
        href: "/bulk-upload",
        icon: UploadCloud,
    },
    {
        title: "Approval Queue",
        href: "/approval",
        icon: CheckSquare,
    },
    {
        title: "Preview Errors",
        href: "/preview",
        icon: Eye,
    },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="flex h-screen w-64 flex-col border-r bg-background">
            <div className="p-6">
                <h1 className="text-2xl font-bold tracking-tight">SAP KB</h1>
                <p className="text-sm text-muted-foreground">Error Management</p>
            </div>

            <div className="flex-1 px-4 py-2">
                <nav className="space-y-2">
                    {menuItems.map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors hover:text-primary",
                                    isActive
                                        ? "bg-primary text-primary-foreground hover:text-primary-foreground"
                                        : "text-muted-foreground hover:bg-muted"
                                )}
                            >
                                <item.icon className="h-5 w-5" />
                                {item.title}
                            </Link>
                        );
                    })}
                </nav>
            </div>

            <div className="p-4 border-t">
                <Link href="/login">
                    <Button variant="outline" className="w-full justify-start gap-3" size="lg">
                        <LogOut className="h-4 w-4" />
                        Logout
                    </Button>
                </Link>
            </div>
        </div>
    );
}
