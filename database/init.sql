CREATE DATABASE IF NOT EXISTS student_db;
USE student_db;

CREATE TABLE students (
    app_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    join_date DATE
);

CREATE TABLE marks (
    id INT AUTO_    INCREMENT PRIMARY KEY,
    app_id VARCHAR(20),
    subject VARCHAR(100),
    obtained INT,
    total INT,
    month VARCHAR(20),
    FOREIGN KEY (app_id) REFERENCES students(app_id)
);

CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    app_id VARCHAR(20),
    month VARCHAR(20),
    status VARCHAR(10),
    FOREIGN KEY (app_id) REFERENCES students(app_id)
);

CREATE TABLE mentors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100),
    password VARCHAR(100)
);

CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100),
    password VARCHAR(100)
);