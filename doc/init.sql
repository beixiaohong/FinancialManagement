-- 创建数据库并设置字符集
CREATE DATABASE IF NOT EXISTS accounting_app 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 创建用户并授权
CREATE USER IF NOT EXISTS 'accounting'@'%' IDENTIFIED BY 'accounting123';
GRANT ALL PRIVILEGES ON accounting_app.* TO 'accounting'@'%';
FLUSH PRIVILEGES;

USE accounting_app;

-- 设置时区
SET time_zone = '+8:00';