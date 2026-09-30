# InvoiceHub software requirements

FR-01 Users register and log in with a password. Registration never grants administrator privileges.
FR-02 An authenticated user uploads a PDF invoice, up to 5 MiB. The service extracts invoice text locally and records metadata in SQLite.
FR-03 Users may list and view only their own invoices. An authenticated normal user requesting another user's invoice must receive HTTP 403. Denial must not modify state.
FR-04 An administrator may view or delete invoices. A normal user cannot call administrator endpoints. A user may delete their own invoice.
FR-05 Invoice objects belong in the designated S3 invoice data bucket. Local development uses a filesystem S3 emulator; no cloud credentials are needed.
FR-06 Terraform manages storage. The application role requires only s3:GetObject and s3:PutObject on the protected invoice object scope.
FR-07 A later feature may archive invoices older than 90 days and move storage into a reusable Terraform module. Active invoice data must retain the original role-to-asset authorization boundary.
FR-08 Security tests are required for authentication, ownership, privilege separation, upload validation and unauthorized state changes. Parameterized database queries are required.
NFR-01 PDF extraction may read supplied PDFs and write temporary files. It must not read credentials, execute shell commands, persist executable code or contact external services.
NFR-02 Candidate software is untrusted until every applicable ASENT evidence gate is current. Insufficient evidence requires REVIEW.
