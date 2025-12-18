# SAP AI Agent - Technical Documentation & SOP

## 1. Overview
This document outlines the technical approach, architecture, and standard operating procedures (SOP) for the **SAP AI Agent (v1.0)**. The system is designed to streamline SAP error resolution by providing a searchable knowledge base, a structured submission process for new errors, and an approval workflow to ensure data quality.

## 2. System Architecture

### Core Technologies
-   **Framework**: [Next.js 15](https://nextjs.org/) (React Framework)
-   **Language**: TypeScript
-   **Database**: Vercel Postgres (Cloud SQL)
-   **Authentication**: NextAuth.js (v5)
-   **Styling**: Tailwind CSS / Shadcn UI
-   **File Processing**: `xlsx` (SheetJS) for Excel parsing, `papaparse` for CSV.

### Database Schema
The system uses two primary tables in a PostgreSQL database:

1.  **`users`**: Stores authorized personnel.
    -   `email` (Unique ID)
    -   `password` (Bcrypt Hashed)
    -   `role` ('ADMIN' or 'USER')
    -   `name`

2.  **`kb_errors`**: Stores the knowledge base entries.
    -   `error_code`: The unique SAP error identifier (e.g., "M7001").
    -   `error_description`: Detailed description.
    -   `module`: SAP Module (MM, SD, FICO, etc.).
    -   `solution_type`: Categorization of the fix (User Guidance, Config, etc.).
    -   `steps_to_resolve`: Step-by-step resolution guide.
    -   `expert_comment`: Internal notes and tags.
    -   `status`: 'PENDING' (Newly submitted), 'APPROVED' (Live in search).

---

## 3. Workflows & Implementation Details

### A. Authentication & Security
Access is restricted to authorized users only. Non-authenticated users are redirected to the login page.
-   **Admin Role**: Full access (Dashboard, Search, Add, Bulk Upload, Approval Queue, Export).
-   **User Role**: Limited access (Search, Add, Bulk Upload).

![Login Page](/C:/Users/airat.aroyewun/.gemini/antigravity/brain/bd36b966-6897-4aae-ad56-e46a3dfac4ab/login_page_1765881633150.png)

### B. Dashboard & Search
The main dashboard provides a real-time overview of the system status, including the count of pending approvals.
-   **Implementation**: Server-side data fetching ensures instant load times and up-to-date counts.
-   **Export**: Admins can download the entire approved database as a JSON file.

![Dashboard](/C:/Users/airat.aroyewun/.gemini/antigravity/brain/bd36b966-6897-4aae-ad56-e46a3dfac4ab/dashboard_page_1765881683254.png)

### C. Adding Solutions (Single Entry)
Consultants can document single errors quickly using a standardized form.
-   **Features**: Dropdowns for Modules and Solution Types enforce data consistency.
-   **Validation**: Required fields are checked before submission.

![Add Single Error](/C:/Users/airat.aroyewun/.gemini/antigravity/brain/bd36b966-6897-4aae-ad56-e46a3dfac4ab/add_single_page_1765881731292.png)

### D. Bulk Upload (Excel/CSV)
For mass updates, users can upload spreadsheets.
-   **Excel Support**: Native `.xlsx` parsing.
-   **Smart Mapping**: The system automatically maps headers like "Issue Name", "issue_name", or "issuename" to the correct database fields, reducing format errors.

![Bulk Upload](/C:/Users/airat.aroyewun/.gemini/antigravity/brain/bd36b966-6897-4aae-ad56-e46a3dfac4ab/bulk_upload_page_1765881755781.png)

### E. Approval Queue (Quality Assurance)
To prevent "garbage in, garbage out," all submissions go to a holding area.
-   **Process**: Admins review "PENDING" entries.
-   **Actions**: 
    -   **Approve**: Moves entry to production (searchable).
    -   **Decline**: Permanently deletes the entry from the database.
-   **Security**: Approval buttons are strictly visible only to users with the 'ADMIN' role.

![Approval Queue](/C:/Users/airat.aroyewun/.gemini/antigravity/brain/bd36b966-6897-4aae-ad56-e46a3dfac4ab/approval_page_1765881699953.png)

---

## 4. Maintenance SOP

### Adding New Users
Currently, user management is handled via database scripts for security.
1.  Open `scripts/setup_db.js`.
2.  Add the new user to the `users` array:
    ```javascript
    { email: 'new.user@tolaram.com', name: 'New User', role: 'USER' }
    ```
3.  Run the script: `node scripts/setup_db.js`.

### Updating the Database Schema
If new fields are needed (e.g., "legacy_id"):
1.  Update the `CREATE TABLE` query in `scripts/setup_db.js`.
2.  Update `src/lib/types.ts` to reflect the new interface.
3.  Update `src/lib/actions.ts` to handle the new field in `INSERT`/`SELECT` queries.

### Deployment Updates
The application is connected to GitHub.
1.  Commit changes locally: `git commit -m "update details"`.
2.  Push to main: `git push`.
3.  Vercel will automatically detect the commit and redeploy the site.
