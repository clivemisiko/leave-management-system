CREATE DATABASE IF NOT EXISTS leave_app;

USE leave_app;

CREATE TABLE leave_applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    pno VARCHAR(50),
    designation VARCHAR(100),
    leave_days INT,
    start_date DATE,
    end_date DATE,
    last_leave_start DATE,
    last_leave_end DATE,
    contact_address VARCHAR(255),
    contact_tel VARCHAR(20),
    salary_option VARCHAR(20),
    salary_address VARCHAR(255),
    delegate VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
