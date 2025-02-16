-- Создание базы данных
CREATE DATABASE ptdev;

-- Подключение к созданной базе данных
\c ptdev

-- Создание таблицы phone
CREATE TABLE phone (
    id SERIAL PRIMARY KEY,
    phonenum VARCHAR(20) NOT NULL
);

-- Создание таблицы mails
CREATE TABLE mails (
    id SERIAL PRIMARY KEY,
    mail VARCHAR(255) NOT NULL
);
