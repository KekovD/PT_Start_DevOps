CREATE USER replication_user WITH REPLICATION ENCRYPTED PASSWORD 'replication_user_password' LOGIN;

CREATE TABLE IF NOT EXISTS emails (ID SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL);
CREATE TABLE IF NOT EXISTS phone_numbers (ID SERIAL PRIMARY KEY, phone_number VARCHAR(25) NOT NULL);

INSERT INTO emails(email) VALUES
    ('temp@gmail.com'),
    ('dv@ya.ru');

INSERT INTO phone_numbers(phone_number) VALUES
    ('8 (999) 999-99-99'),
    ('8 (800) 555-35-35');


CREATE TABLE hba ( lines text );
COPY hba FROM '/var/lib/postgresql/data/pg_hba.conf';
INSERT INTO hba (lines) VALUES ('host replication all 0.0.0.0/0 md5');
COPY hba TO '/var/lib/postgresql/data/pg_hba.conf';
SELECT pg_reload_conf();

SELECT * FROM pg_create_physical_replication_slot('replication_slot');
