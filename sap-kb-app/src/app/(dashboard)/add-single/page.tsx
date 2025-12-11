"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { MODULES, SOLUTION_TYPES, LOG_CATEGORIES, LOG_SUBCATEGORIES } from "@/lib/constants";
import { useEffect } from "react";

const formSchema = z.object({
    module: z.string().min(1, "Module is required"),
    issuename: z.string().min(1, "Issue Name is required"),
    issuedescription: z.string().min(1, "Issue Description is required"),
    solutiontype: z.string().min(1, "Solution Type is required"),
    stepbystep: z.string().min(1, "Step by step instructions are required"),
    logcategory: z.string().min(1, "Category is required"), // ID as string
    logsubcategory: z.string().optional(), // ID as string
    notes: z.string().optional(),
});

export default function AddSingleErrorPage() {
    const router = useRouter();
    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            issuename: "",
            issuedescription: "",
            stepbystep: "",
            notes: "",
        },
    });

    const selectedCategory = form.watch("logcategory");

    // Reset subcategory when category changes
    useEffect(() => {
        form.setValue("logsubcategory", "");
    }, [selectedCategory, form]);

    const subcategories = selectedCategory
        ? LOG_SUBCATEGORIES[parseInt(selectedCategory)] || []
        : [];

    const onSubmit = async (values: z.infer<typeof formSchema>) => {
        console.log("Submitting:", values);

        // Mock API call / Store in local storage
        const newEntry = {
            id: crypto.randomUUID(),
            ...values,
            logcategory: parseInt(values.logcategory),
            logsubcategory: values.logsubcategory ? parseInt(values.logsubcategory) : null,
            status: "pending",
            createdAt: new Date().toISOString(),
            comments: []
        };

        // Store in localStorage for demo
        const existing = JSON.parse(localStorage.getItem("sap-kb-pending") || "[]");
        localStorage.setItem("sap-kb-pending", JSON.stringify([...existing, newEntry]));

        toast.success("Error submitted for approval successfully!");
        router.push("/approval");
    };

    return (
        <div className="max-w-4xl mx-auto py-6">
            <div className="mb-6">
                <h1 className="text-3xl font-bold tracking-tight">Add Single Error</h1>
                <p className="text-muted-foreground">Fill in all required fields to submit an error for approval</p>
            </div>

            <Card>
                <CardContent className="pt-6">
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

                            <div className="grid grid-cols-2 gap-6">
                                <FormField
                                    control={form.control}
                                    name="module"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Module <span className="text-red-500">*</span></FormLabel>
                                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select a module" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    {MODULES.map((mod) => (
                                                        <SelectItem key={mod} value={mod}>{mod}</SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="issuename"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Issue Name <span className="text-red-500">*</span></FormLabel>
                                            <FormControl>
                                                <Input placeholder="e.g. Transaction timeout error" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <FormField
                                control={form.control}
                                name="issuedescription"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Issue Description <span className="text-red-500">*</span></FormLabel>
                                        <FormControl>
                                            <Textarea placeholder="Describe the issue in detail..." className="h-24 resize-none" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <div className="grid grid-cols-2 gap-6">
                                <FormField
                                    control={form.control}
                                    name="solutiontype"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Solution Type <span className="text-red-500">*</span></FormLabel>
                                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select solution type" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    {SOLUTION_TYPES.map((type) => (
                                                        <SelectItem key={type} value={type}>{type}</SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="logcategory"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Log Category <span className="text-red-500">*</span></FormLabel>
                                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select category" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    {LOG_CATEGORIES.map((cat) => (
                                                        <SelectItem key={cat.id} value={cat.id.toString()}>{cat.label}</SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            {/* Dynamic Subcategory */}
                            {selectedCategory && (
                                <FormField
                                    control={form.control}
                                    name="logsubcategory"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Log Subcategory</FormLabel>
                                            <Select onValueChange={field.onChange} value={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder={subcategories.length > 0 ? "Select subcategory" : "No subcategories available"} />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    {subcategories.length > 0 ? (
                                                        subcategories.map((sub) => (
                                                            <SelectItem key={sub.id} value={sub.id.toString()}>{sub.label}</SelectItem>
                                                        ))
                                                    ) : (
                                                        <SelectItem value="none" disabled>No subcategories available</SelectItem>
                                                    )}
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            )}

                            <FormField
                                control={form.control}
                                name="stepbystep"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Step by Step Solution <span className="text-red-500">*</span></FormLabel>
                                        <FormControl>
                                            <Textarea placeholder="Provide step-by-step instructions to resolve the issue..." className="h-32 resize-none" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="notes"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Notes (Optional)</FormLabel>
                                        <FormControl>
                                            <Textarea placeholder="Additional notes or references..." className="h-20 resize-none" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <div className="flex justify-end gap-4">
                                <Button type="button" variant="outline" onClick={() => router.back()}>Cancel</Button>
                                <Button type="submit" className="bg-black text-white hover:bg-gray-800 w-48">Send for Approval</Button>
                            </div>

                        </form>
                    </Form>
                </CardContent>
            </Card>
        </div>
    );
}
