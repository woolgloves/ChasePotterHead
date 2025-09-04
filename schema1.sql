-- Levels
CREATE TABLE level (
  level        INT PRIMARY KEY,
  max_hp       INT NOT NULL
);

-- Houses
CREATE TABLE house (
  house_id     INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  house_name   VARCHAR(100) NOT NULL UNIQUE
);

-- Spells
CREATE TABLE spells (
  spell_id     INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(100) NOT NULL,
  damage       INT NOT NULL,
  price        INT NOT NULL,
  unlock_level INT NOT NULL,
  mana_cost    INT NOT NULL,
  FOREIGN KEY (unlock_level) REFERENCES level(level)
);

-- Achievements
CREATE TABLE achievements (
  achievement_id     INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  achievement_title  VARCHAR(150) NOT NULL UNIQUE,
  points_awarded     INT NOT NULL
);

-- Players
CREATE TABLE players (
  player_id   INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username    VARCHAR(50)  NOT NULL UNIQUE,
  password    VARCHAR(255) NOT NULL,
  level       INT NOT NULL,
  experience  INT NOT NULL DEFAULT 0,
  currency    INT NOT NULL DEFAULT 0,
  house_id    INT,
  FOREIGN KEY (level)    REFERENCES level(level),
  FOREIGN KEY (house_id) REFERENCES house(house_id)
);

-- Battles
CREATE TABLE battles (
  battle_id              INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  status                 VARCHAR(20) NOT NULL,
  battle_date            TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  challenger_hp          INT NOT NULL,
  opponent_hp            INT NOT NULL,
  winner_id              INT,
  current_turn_player_id INT,
  challenger_id          INT NOT NULL,
  opponent_id            INT NOT NULL,
  FOREIGN KEY (winner_id)              REFERENCES players(player_id),
  FOREIGN KEY (current_turn_player_id) REFERENCES players(player_id),
  FOREIGN KEY (challenger_id)          REFERENCES players(player_id),
  FOREIGN KEY (opponent_id)            REFERENCES players(player_id)
);

-- Many-to-many link tables 
CREATE TABLE is_learned_by (
  player_id INT NOT NULL,
  spell_id  INT NOT NULL,
  learned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (player_id, spell_id),
  FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
  FOREIGN KEY (spell_id)  REFERENCES spells(spell_id)  ON DELETE CASCADE
);

CREATE TABLE is_awarded (
  player_id      INT NOT NULL,
  achievement_id INT NOT NULL,
  awarded_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (player_id, achievement_id),
  FOREIGN KEY (player_id)      REFERENCES players(player_id)      ON DELETE CASCADE,
  FOREIGN KEY (achievement_id) REFERENCES achievements(achievement_id) ON DELETE CASCADE
);

-- Indexes 
CREATE INDEX idx_players_level     ON players(level);
CREATE INDEX idx_players_house     ON players(house_id);
CREATE INDEX idx_spells_unlock     ON spells(unlock_level);
CREATE INDEX idx_battles_turn      ON battles(current_turn_player_id);
CREATE INDEX idx_battles_challenger ON battles(challenger_id);
CREATE INDEX idx_battles_opponent   ON battles(opponent_id);
CREATE INDEX idx_battles_status_date ON battles(status, battle_date);
