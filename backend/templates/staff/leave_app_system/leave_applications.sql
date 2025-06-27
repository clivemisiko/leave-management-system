SELECT * FROM leave_app.leave_applications;
ALTER TABLE leave_applications
    ADD COLUMN will_be_paid VARCHAR(5) DEFAULT 'Yes',
    MODIFY COLUMN salary_option VARCHAR(50),
    MODIFY COLUMN salary_address TEXT;
