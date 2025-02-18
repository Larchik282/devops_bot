

\c ptdev

CREATE TABLE phone (
    id SERIAL PRIMARY KEY,
    phonenum VARCHAR(20) NOT NULL
);

CREATE TABLE mails (
    id SERIAL PRIMARY KEY,
    mail VARCHAR(255) NOT NULL
);
