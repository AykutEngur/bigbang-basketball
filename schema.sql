-- Big Bang Basketball — MySQL schema draft

CREATE DATABASE IF NOT EXISTS bigbang_basketball
  CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;

USE bigbang_basketball;

CREATE TABLE players (
  id INT AUTO_INCREMENT PRIMARY KEY,
  first_name VARCHAR(50) NOT NULL,
  last_name VARCHAR(50) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  birth_date DATE NOT NULL,
  phone VARCHAR(20),
  profile_photo VARCHAR(255) NULL,
  team_id INT NULL,
  jersey_number INT NULL,
  is_free_agent BOOLEAN DEFAULT TRUE,
  has_paid BOOLEAN DEFAULT FALSE,
  points_total INT DEFAULT 0,
  contract_accepted BOOLEAN NOT NULL DEFAULT FALSE,
  contract_accepted_at TIMESTAMP NULL,
  is_banned BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE teams (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  logo VARCHAR(255) NULL,
  captain_id INT NULL,
  leader_contract_accepted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (captain_id) REFERENCES players(id)
);

ALTER TABLE players
  ADD CONSTRAINT fk_player_team
  FOREIGN KEY (team_id) REFERENCES teams(id);

CREATE TABLE matches (
  id INT AUTO_INCREMENT PRIMARY KEY,
  home_team_id INT NOT NULL,
  away_team_id INT NOT NULL,
  match_date DATETIME NOT NULL,
  home_score INT DEFAULT NULL,
  away_score INT DEFAULT NULL,
  stage ENUM('regular', 'semifinal', 'final', 'third_place') DEFAULT 'regular',
  FOREIGN KEY (home_team_id) REFERENCES teams(id),
  FOREIGN KEY (away_team_id) REFERENCES teams(id)
);

CREATE TABLE payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  player_id INT NOT NULL,
  amount DECIMAL(10, 2) NOT NULL,
  status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE join_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  player_id INT NOT NULL,
  team_id INT NOT NULL,
  token VARCHAR(64) NOT NULL UNIQUE,
  status ENUM('pending', 'approved', 'rejected', 'expired') NOT NULL DEFAULT 'pending',
  requested_jersey_number INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  decided_at TIMESTAMP NULL,
  FOREIGN KEY (player_id) REFERENCES players(id),
  FOREIGN KEY (team_id) REFERENCES teams(id)
);