-- Motorcycle Riders Management and Booking System
-- ADUSTech Wudil - Database Schema

CREATE DATABASE IF NOT EXISTS adustech_riders;
USE adustech_riders;

-- Users table (passengers, riders, admins)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('user', 'rider', 'admin') NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rider profiles (linked to users with role='rider')
CREATE TABLE IF NOT EXISTS riders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    rider_id_number VARCHAR(20) NOT NULL UNIQUE,
    license_number VARCHAR(50) NOT NULL,
    motorcycle_plate VARCHAR(20) NOT NULL,
    motorcycle_model VARCHAR(50) NOT NULL,
    motorcycle_color VARCHAR(30),
    id_card_number VARCHAR(50) NOT NULL,
    status ENUM('pending', 'approved', 'rejected', 'suspended') DEFAULT 'pending',
    is_available BOOLEAN DEFAULT FALSE,
    rating DECIMAL(3,2) DEFAULT 5.00,
    total_rides INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Real-time rider locations
CREATE TABLE IF NOT EXISTS rider_locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rider_id INT NOT NULL UNIQUE,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    location_name VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (rider_id) REFERENCES riders(id) ON DELETE CASCADE
);

-- Ride bookings
CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    rider_id INT,
    pickup_location VARCHAR(200) NOT NULL,
    pickup_lat DECIMAL(10, 8),
    pickup_lng DECIMAL(11, 8),
    destination VARCHAR(200) NOT NULL,
    destination_lat DECIMAL(10, 8),
    destination_lng DECIMAL(11, 8),
    fare DECIMAL(10, 2),
    status ENUM('pending', 'accepted', 'in_progress', 'completed', 'cancelled') DEFAULT 'pending',
    notes TEXT,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (rider_id) REFERENCES riders(id) ON DELETE SET NULL
);

-- Campus locations reference
CREATE TABLE IF NOT EXISTS campus_locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category ENUM('faculty', 'hostel', 'gate', 'market', 'other') DEFAULT 'other',
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL
);

-- Admin account is created via POST /api/init-admin after setup
-- Default credentials: admin@adustech.edu.ng / admin123

-- Insert campus locations for ADUSTech Wudil
INSERT INTO campus_locations (name, category, latitude, longitude) VALUES
('Main Gate', 'gate', 11.7850, 8.8700),
('Faculty of Engineering', 'faculty', 11.7865, 8.8715),
('Faculty of Science', 'faculty', 11.7870, 8.8720),
('Faculty of Agriculture', 'faculty', 11.7855, 8.8730),
('Central Library', 'other', 11.7868, 8.8718),
('Male Hostel Block A', 'hostel', 11.7845, 8.8725),
('Female Hostel Block B', 'hostel', 11.7848, 8.8735),
('Wudil Market', 'market', 11.7800, 8.8650),
('Administrative Block', 'other', 11.7860, 8.8710),
('Sports Complex', 'other', 11.7875, 8.8705);
