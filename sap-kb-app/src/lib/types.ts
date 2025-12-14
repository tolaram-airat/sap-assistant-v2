export interface KBError {
    id: number;
    error_code: string;
    error_description: string;
    module: string;
    solution_type: string;
    steps_to_resolve: string;
    expert_comment?: string;
    status: 'PENDING' | 'APPROVED';
    created_at?: Date;
    created_by?: string;
    approved_at?: Date;
    approved_by?: string;
}

export type UserRole = 'ADMIN' | 'USER';

export interface User {
    id: number;
    email: string;
    name: string;
    role: UserRole;
}
