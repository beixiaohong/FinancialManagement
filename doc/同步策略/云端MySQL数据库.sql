-- =====================================================
-- 云端MySQL数据库设计 (app/database/mysql_schema.sql)
-- =====================================================

-- 设置字符集和排序规则
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- =====================================================
-- 1. 用户相关表
-- =====================================================

-- 用户表
CREATE TABLE `users` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `uuid` CHAR(36) UNIQUE NOT NULL COMMENT '客户端UUID标识',
    `username` VARCHAR(50) UNIQUE NOT NULL,
    `email` VARCHAR(100) UNIQUE,
    `phone` VARCHAR(20) UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    
    -- 个人信息
    `nickname` VARCHAR(50),
    `avatar_url` VARCHAR(500),
    `bio` TEXT,
    
    -- 用户等级和状态
    `user_level` ENUM('free', 'member', 'premium') DEFAULT 'free',
    `user_status` ENUM('active', 'inactive', 'frozen') DEFAULT 'active',
    `member_expires_at` TIMESTAMP NULL,
    
    -- 统计信息
    `total_accounts` INT UNSIGNED DEFAULT 0,
    `total_records` INT UNSIGNED DEFAULT 0,
    `last_login_at` TIMESTAMP NULL,
    
    -- 版本控制
    `version` INT UNSIGNED DEFAULT 1 COMMENT '记录版本号',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT DEFAULT 0,
    
    INDEX `idx_users_uuid` (`uuid`),
    INDEX `idx_users_level_status` (`user_level`, `user_status`),
    INDEX `idx_users_updated` (`updated_at`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='用户表';

-- 设备注册表
CREATE TABLE `devices` (
    `device_id` CHAR(36) PRIMARY KEY,
    `user_id` INT UNSIGNED NOT NULL,
    `device_name` VARCHAR(100) NOT NULL,
    `device_type` ENUM('android', 'ios', 'web', 'desktop') NOT NULL,
    `installation_id` CHAR(36) UNIQUE,
    `last_sync_token` VARCHAR(100),
    `last_sync_at` TIMESTAMP NULL,
    `is_active` TINYINT DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_devices_user` (`user_id`, `is_active`),
    INDEX `idx_devices_sync` (`last_sync_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='设备注册表';

-- =====================================================
-- 2. 账本相关表
-- =====================================================

-- 账本表
CREATE TABLE `accounts` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `uuid` CHAR(36) UNIQUE NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `description` TEXT,
    `account_type` ENUM('personal', 'family', 'team', 'project') DEFAULT 'personal',
    `currency` VARCHAR(10) DEFAULT 'CNY',
    `icon_url` VARCHAR(500),
    `color` VARCHAR(20) DEFAULT '#1890ff',
    
    -- 统计信息(冗余设计，定期同步)
    `total_income` DECIMAL(15,2) DEFAULT 0.00,
    `total_expense` DECIMAL(15,2) DEFAULT 0.00,
    `balance` DECIMAL(15,2) DEFAULT 0.00,
    `total_records` INT UNSIGNED DEFAULT 0,
    `member_count` INT UNSIGNED DEFAULT 1,
    
    -- 所有者信息
    `owner_id` INT UNSIGNED NOT NULL,
    
    -- 版本控制
    `version` INT UNSIGNED DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT DEFAULT 0,
    
    FOREIGN KEY (`owner_id`) REFERENCES `users`(`id`) ON DELETE RESTRICT,
    INDEX `idx_accounts_uuid` (`uuid`),
    INDEX `idx_accounts_owner` (`owner_id`, `is_deleted`),
    INDEX `idx_accounts_updated` (`updated_at`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='账本表';

-- 账本成员表
CREATE TABLE `account_members` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `uuid` CHAR(36) UNIQUE NOT NULL,
    `account_id` INT UNSIGNED NOT NULL,
    `user_id` INT UNSIGNED NOT NULL,
    `role` ENUM('admin', 'editor', 'viewer') DEFAULT 'viewer',
    `invite_status` ENUM('pending', 'accepted', 'rejected', 'expired') DEFAULT 'pending',
    `invite_code` VARCHAR(50) UNIQUE,
    `invited_by_id` INT UNSIGNED,
    `invited_at` TIMESTAMP NULL,
    `accepted_at` TIMESTAMP NULL,
    
    -- 版本控制
    `version` INT UNSIGNED DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT DEFAULT 0,
    
    FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`invited_by_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    
    UNIQUE KEY `idx_account_members_unique` (`account_id`, `user_id`, `is_deleted`),
    INDEX `idx_account_members_user` (`user_id`),
    INDEX `idx_account_members_invite` (`invite_code`, `invite_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='账本成员表';

-- =====================================================
-- 3. 支付账户和分类表
-- =====================================================

-- 支付账户表
CREATE TABLE `payment_accounts` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `uuid` CHAR(36) UNIQUE NOT NULL,
    `account_id` INT UNSIGNED NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `account_type` ENUM('savings', 'credit', 'investment') NOT NULL,
    `description` TEXT,
    
    -- 账户属性
    `balance` DECIMAL(15,2) DEFAULT 0.00,
    `credit_limit` DECIMAL(15,2),
    `interest_rate` DECIMAL(8,4),
    `bill_day` TINYINT UNSIGNED,
    `due_day` TINYINT UNSIGNED,
    
    -- 显示设置
    `icon_name` VARCHAR(50),
    `color` VARCHAR(20) DEFAULT '#1890ff',
    `sort_order` INT DEFAULT 0,
    `is_active` TINYINT DEFAULT 1,
    
    -- 版本控制
    `version` INT UNSIGNED DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT DEFAULT 0,
    
    FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON DELETE CASCADE,
    INDEX `idx_payment_accounts_uuid` (`uuid`),
    INDEX `idx_payment_accounts_account` (`account_id`, `is_deleted`),
    INDEX `idx_payment_accounts_active` (`account_id`, `is_active`, `sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='支付账户表';

-- 分类表
CREATE TABLE `categories` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `uuid` CHAR(36) UNIQUE NOT NULL,
    `account_id` INT UNSIGNED NOT NULL COMMENT '0表示系统默认分类',
    `name` VARCHAR(100) NOT NULL,
    `description` TEXT,
    `parent_id` INT UNSIGNED,
    `level` TINYINT UNSIGNED NOT NULL,
    `full_path` VARCHAR(255),
    
    -- 显示设置
    `icon_name` VARCHAR(50),
    `color` VARCHAR(20) DEFAULT '#1890ff',
    `sort_order` INT DEFAULT 0,
    `is_active` TINYINT DEFAULT 1,
    `is_system` TINYINT DEFAULT 0,
    
    -- 统计信息(异步更新)
    `record_count` INT UNSIGNED DEFAULT 0,
    `total_amount` DECIMAL(15,2) DEFAULT 0.00,
    
    -- 版本控制
    `version` INT UNSIGNED DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT DEFAULT 0,
    
    FOREIGN KEY (`parent_id`) REFERENCES `categories`(`id`) ON DELETE SET NULL,
    INDEX `idx_categories_uuid` (`uuid`),
    INDEX `idx_categories_account` (`account_id`, `is_deleted`),
    INDEX `idx_categories_parent` (`parent_id`),
    INDEX `idx_categories_level` (`level`, `is_active`),
    INDEX `idx_categories_system` (`is_system`, `account_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='三级分类表';

-- =====================================================
-- 4. 记账记录表(核心业务表)
-- =====================================================

-- 记账记录表
CREATE TABLE `records` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `uuid` CHAR(36) UNIQUE NOT NULL,
    `account_id` INT UNSIGNED NOT NULL,
    `record_type` ENUM('income', 'expense', 'transfer') NOT NULL,
    `amount` DECIMAL(15,2) NOT NULL,
    `record_date` TIMESTAMP NOT NULL,
    `description` TEXT,
    
    -- 关联信息
    `creator_id` INT UNSIGNED NOT NULL,
    `last_editor_id` INT UNSIGNED,
    `payment_account_id` INT UNSIGNED NOT NULL,
    `category_id` INT UNSIGNED,
    
    -- 转账相关(仅转账类型使用)
    `target_payment_account_id` INT UNSIGNED,
    `transfer_fee` DECIMAL(10,2) DEFAULT 0.00,
    
    -- 扩展信息(JSON格式)
    `tags` JSON COMMENT '标签数组',
    `location` VARCHAR(255) COMMENT '消费地点',
    `weather` VARCHAR(50) COMMENT '天气情况',
    `mood` VARCHAR(50) COMMENT '心情',
    `project_name` VARCHAR(100) COMMENT '关联项目',
    `related_people` JSON COMMENT '关联人员',
    `images` JSON COMMENT '图片URLs',
    `metadata` JSON COMMENT '其他元数据',
    
    -- 业务扩展
    `is_recurring` TINYINT DEFAULT 0 COMMENT '是否重复记录',
    `recurring_rule` JSON COMMENT '重复规则',
    `original_record_id` INT UNSIGNED COMMENT '原始记录ID',
    
    -- 数据完整性
    `hash_value` CHAR(64) COMMENT 'SHA256内容哈希',
    `source_device_id` CHAR(36) COMMENT '创建设备ID',
    
    -- 版本控制
    `version` INT UNSIGNED DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT DEFAULT 0,
    
    FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON DELETE RESTRICT,
    FOREIGN KEY (`creator_id`) REFERENCES `users`(`id`) ON DELETE RESTRICT,
    FOREIGN KEY (`last_editor_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`payment_account_id`) REFERENCES `payment_accounts`(`id`) ON DELETE RESTRICT,
    FOREIGN KEY (`category_id`) REFERENCES `categories`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`target_payment_account_id`) REFERENCES `payment_accounts`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`original_record_id`) REFERENCES `records`(`id`) ON DELETE SET NULL,
    
    INDEX `idx_records_uuid` (`uuid`),
    INDEX `idx_records_account_date` (`account_id`, `record_date` DESC, `is_deleted`),
    INDEX `idx_records_creator` (`creator_id`, `record_date` DESC),
    INDEX `idx_records_category` (`category_id`, `is_deleted`),
    INDEX `idx_records_payment_account` (`payment_account_id`),
    INDEX `idx_records_hash` (`hash_value`),
    INDEX `idx_records_amount` (`account_id`, `amount`),
    INDEX `idx_records_type_date` (`account_id`, `record_type`, `record_date` DESC),
    INDEX `idx_records_updated` (`updated_at`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='记账记录表'
PARTITION BY RANGE (YEAR(record_date)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- =====================================================
-- 5. 同步相关表
-- =====================================================

-- 同步日志表(用于增量同步)
CREATE TABLE `sync_logs` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `account_id` INT UNSIGNED NOT NULL,
    `table_name` VARCHAR(50) NOT NULL,
    `record_uuid` CHAR(36) NOT NULL,
    `record_id` INT UNSIGNED,
    `operation` ENUM('CREATE', 'UPDATE', 'DELETE') NOT NULL,
    
    -- 操作信息
    `user_id` INT UNSIGNED NOT NULL,
    `device_id` CHAR(36) NOT NULL,
    `version_before` INT UNSIGNED,
    `version_after` INT UNSIGNED,
    
    -- 变更数据(压缩存储)
    `data_before` JSON COMMENT '操作前数据',
    `data_after` JSON COMMENT '操作后数据',
    `changes_only` JSON COMMENT '仅变更字段',
    
    -- 同步相关
    `sync_token` VARCHAR(100) NOT NULL COMMENT '同步令牌',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX `idx_sync_logs_account_token` (`account_id`, `sync_token`),
    INDEX `idx_sync_logs_record` (`table_name`, `record_uuid`),
    INDEX `idx_sync_logs_device` (`device_id`, `created_at`),
    INDEX `idx_sync_logs_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='同步日志表'
PARTITION BY RANGE (UNIX_TIMESTAMP(created_at)) (
    PARTITION p_current VALUES LESS THAN (UNIX_TIMESTAMP('2025-01-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- 冲突解决记录表
CREATE TABLE `conflict_resolutions` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `account_id` INT UNSIGNED NOT NULL,
    `table_name` VARCHAR(50) NOT NULL,
    `record_uuid` CHAR(36) NOT NULL,
    `conflict_type` ENUM('version', 'field', 'deletion', 'concurrent') NOT NULL,
    
    -- 冲突数据
    `local_data` JSON COMMENT '客户端数据',
    `server_data` JSON COMMENT '服务器数据',
    `resolved_data` JSON COMMENT '解决后数据',
    
    -- 解决信息
    `resolution_strategy` ENUM('auto', 'manual', 'merge', 'skip') NOT NULL,
    `resolution_rule` VARCHAR(100) COMMENT '解决规则标识',
    `resolved_by_user_id` INT UNSIGNED,
    `resolved_by_device_id` CHAR(36),
    
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `resolved_at` TIMESTAMP NULL,
    
    FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON DELETE CASCADE,
    INDEX `idx_conflict_resolutions_record` (`table_name`, `record_uuid`),
    INDEX `idx_conflict_resolutions_account` (`account_id`, `created_at`),
    INDEX `idx_conflict_resolutions_status` (`resolved_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='冲突解决记录表';

-- 同步锁表(防止并发同步)
CREATE TABLE `sync_locks` (
    `account_id` INT UNSIGNED PRIMARY KEY,
    `locked_by_device_id` CHAR(36) NOT NULL,
    `locked_by_user_id` INT UNSIGNED NOT NULL,
    `operation_type` VARCHAR(50),
    `locked_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `expires_at` TIMESTAMP NOT NULL,
    
    FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON DELETE CASCADE,
    INDEX `idx_sync_locks_expires` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='同步锁表';

-- =====================================================
-- 6. 管理和审计表
-- =====================================================

-- 管理员操作日志
CREATE TABLE `admin_logs` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `admin_id` INT UNSIGNED NOT NULL,
    `action` VARCHAR(100) NOT NULL,
    `target_type` VARCHAR(50),
    `target_id` INT UNSIGNED,
    `target_uuid` CHAR(36),
    
    -- 详细信息
    `description` TEXT,
    `old_data` JSON,
    `new_data` JSON,
    
    -- 请求信息
    `ip_address` VARCHAR(45),
    `user_agent` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (`admin_id`) REFERENCES `users`(`id`) ON DELETE RESTRICT,
    INDEX `idx_admin_logs_admin` (`admin_id`, `created_at`),
    INDEX `idx_admin_logs_target` (`target_type`, `target_id`),
    INDEX `idx_admin_logs_action` (`action`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='管理员操作日志';

-- 系统统计表(定期更新)
CREATE TABLE `system_statistics` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `stat_date` DATE UNIQUE NOT NULL,
    
    -- 用户统计
    `total_users` INT UNSIGNED DEFAULT 0,
    `active_users_daily` INT UNSIGNED DEFAULT 0,
    `new_users` INT UNSIGNED DEFAULT 0,
    `premium_users` INT UNSIGNED DEFAULT 0,
    
    -- 业务统计
    `total_accounts` INT UNSIGNED DEFAULT 0,
    `total_records` INT UNSIGNED DEFAULT 0,
    `total_amount` DECIMAL(20,2) DEFAULT 0.00,
    `sync_operations` INT UNSIGNED DEFAULT 0,
    `conflict_count` INT UNSIGNED DEFAULT 0,
    
    -- 性能统计
    `avg_response_time` DECIMAL(6,2),
    `error_rate` DECIMAL(5,4),
    
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX `idx_system_statistics_date` (`stat_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='系统统计表';

-- =====================================================
-- 7. 触发器 - 自动维护数据一致性
-- =====================================================

DELIMITER //

-- 记录变更日志触发器
CREATE TRIGGER `trigger_records_sync_log_insert`
    AFTER INSERT ON `records`
    FOR EACH ROW
BEGIN
    INSERT INTO `sync_logs` (
        `account_id`, `table_name`, `record_uuid`, `record_id`, 
        `operation`, `user_id`, `device_id`, `version_after`, 
        `data_after`, `sync_token`
    ) VALUES (
        NEW.account_id, 'records', NEW.uuid, NEW.id,
        'CREATE', NEW.creator_id, NEW.source_device_id, NEW.version,
        JSON_OBJECT(
            'uuid', NEW.uuid,
            'record_type', NEW.record_type,
            'amount', NEW.amount,
            'record_date', NEW.record_date,
            'description', NEW.description,
            'category_id', NEW.category_id
        ),
        CONCAT('sync_', UNIX_TIMESTAMP(), '_', CONNECTION_ID())
    );
END//

CREATE TRIGGER `trigger_records_sync_log_update`
    AFTER UPDATE ON `records`
    FOR EACH ROW
BEGIN
    IF NEW.version != OLD.version THEN
        INSERT INTO `sync_logs` (
            `account_id`, `table_name`, `record_uuid`, `record_id`,
            `operation`, `user_id`, `device_id`, 
            `version_before`, `version_after`,
            `data_before`, `data_after`, `changes_only`, `sync_token`
        ) VALUES (
            NEW.account_id, 'records', NEW.uuid, NEW.id,
            'UPDATE', COALESCE(NEW.last_editor_id, NEW.creator_id), NEW.source_device_id,
            OLD.version, NEW.version,
            JSON_OBJECT('amount', OLD.amount, 'description', OLD.description),
            JSON_OBJECT('amount', NEW.amount, 'description', NEW.description),
            JSON_OBJECT(
                'amount', IF(OLD.amount != NEW.amount, 
                    JSON_OBJECT('old', OLD.amount, 'new', NEW.amount), NULL),
                'description', IF(OLD.description != NEW.description,
                    JSON_OBJECT('old', OLD.description, 'new', NEW.description), NULL)
            ),
            CONCAT('sync_', UNIX_TIMESTAMP(), '_', CONNECTION_ID())
        );
    END IF;
END//

-- 账本统计更新触发器
CREATE TRIGGER `trigger_update_account_stats_insert`
    AFTER INSERT ON `records`
    FOR EACH ROW
BEGIN
    IF NEW.is_deleted = 0 THEN
        UPDATE `accounts` SET
            `total_income` = `total_income` + 
                CASE WHEN NEW.record_type = 'income' THEN NEW.amount ELSE 0 END,
            `total_expense` = `total_expense` + 
                CASE WHEN NEW.record_type = 'expense' THEN NEW.amount ELSE 0 END,
            `balance` = `balance` + 
                CASE 
                    WHEN NEW.record_type = 'income' THEN NEW.amount
                    WHEN NEW.record_type = 'expense' THEN -NEW.amount
                    ELSE 0 
                END,
            `total_records` = `total_records` + 1,
            `version` = `version` + 1
        WHERE `id` = NEW.account_id;
        
        -- 更新分类统计
        IF NEW.category_id IS NOT NULL THEN
            UPDATE `categories` SET
                `record_count` = `record_count` + 1,
                `total_amount` = `total_amount` + 
                    CASE WHEN NEW.record_type = 'expense' THEN NEW.amount ELSE 0 END
            WHERE `id` = NEW.category_id;
        END IF;
    END IF;
END//

DELIMITER ;

-- =====================================================
-- 8. 视图 - 简化查询
-- =====================================================

-- 用户详情视图
CREATE VIEW `v_user_details` AS
SELECT 
    u.*,
    COUNT(DISTINCT a.id) as owned_accounts,
    COUNT(DISTINCT am.account_id) as member_accounts,
    COUNT(DISTINCT r.id) as total_user_records,
    d.device_count
FROM `users` u
LEFT JOIN `accounts` a ON u.id = a.owner_id AND a.is_deleted = 0
LEFT JOIN `account_members` am ON u.id = am.user_id AND am.is_deleted = 0 AND am.invite_status = 'accepted'
LEFT JOIN `records` r ON u.id = r.creator_id AND r.is_deleted = 0
LEFT JOIN (
    SELECT user_id, COUNT(*) as device_count 
    FROM devices 
    WHERE is_active = 1 
    GROUP BY user_id
) d ON u.id = d.user_id
WHERE u.is_deleted = 0
GROUP BY u.id;

-- 同步状态视图
CREATE VIEW `v_sync_status` AS
SELECT 
    sl.account_id,
    sl.table_name,
    COUNT(*) as total_changes,
    MAX(sl.created_at) as last_change,
    COUNT(DISTINCT sl.device_id) as device_count,
    COUNT(CASE WHEN sl.operation = 'CREATE' THEN 1 END) as creates,
    COUNT(CASE WHEN sl.operation = 'UPDATE' THEN 1 END) as updates,
    COUNT(CASE WHEN sl.operation = 'DELETE' THEN 1 END) as deletes
FROM `sync_logs` sl
WHERE sl.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY sl.account_id, sl.table_name;

-- =====================================================
-- 9. 存储过程 - 业务逻辑封装
-- =====================================================

DELIMITER //

-- 获取增量同步数据
CREATE PROCEDURE `GetIncrementalChanges`(
    IN p_account_id INT UNSIGNED,
    IN p_device_id CHAR(36),
    IN p_since_token VARCHAR(100),
    IN p_limit INT DEFAULT 100
)
BEGIN
    DECLARE v_since_id BIGINT DEFAULT 0;
    
    -- 解析同步令牌获取起始ID
    IF p_since_token IS NOT NULL AND p_since_token != '' THEN
        SELECT CAST(SUBSTRING_INDEX(p_since_token, '_', -1) AS UNSIGNED) INTO v_since_id;
    END IF;
    
    -- 返回增量变更
    SELECT 
        sl.id,
        sl.table_name,
        sl.record_uuid,
        sl.operation,
        sl.version_after,
        sl.data_after,
        sl.changes_only,
        sl.created_at,
        CONCAT('sync_', sl.created_at, '_', sl.id) as sync_token
    FROM sync_logs sl
    WHERE sl.account_id = p_account_id
        AND sl.id > v_since_id
        AND sl.device_id != p_device_id  -- 排除自己的变更
    ORDER BY sl.id ASC
    LIMIT p_limit;
    
    -- 返回新的同步令牌
    SELECT CONCAT('sync_', UNIX_TIMESTAMP(), '_', 
        COALESCE(MAX(sl.id), v_since_id)) as next_sync_token
    FROM sync_logs sl
    WHERE sl.account_id = p_account_id AND sl.id > v_since_id;
END//

-- 处理批量同步
CREATE PROCEDURE `ProcessBatchSync`(
    IN p_account_id INT UNSIGNED,
    IN p_device_id CHAR(36),
    IN p_user_id INT UNSIGNED,
    IN p_sync_data JSON
)
BEGIN
    DECLARE v_index INT DEFAULT 0;
    DECLARE v_count INT;
    DECLARE v_item JSON;
    DECLARE v_table_name VARCHAR(50);
    DECLARE v_operation VARCHAR(10);
    DECLARE v_record_uuid CHAR(36);
    DECLARE v_record_data JSON;
    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    -- 获取批量数据数量
    SET v_count = JSON_LENGTH(p_sync_data);
    
    -- 逐项处理
    WHILE v_index < v_count DO
        SET v_item = JSON_EXTRACT(p_sync_data, CONCAT('$[', v_index, ']'));
        SET v_table_name = JSON_UNQUOTE(JSON_EXTRACT(v_item, '$.table_name'));
        SET v_operation = JSON_UNQUOTE(JSON_EXTRACT(v_item, '$.operation'));
        SET v_record_uuid = JSON_UNQUOTE(JSON_EXTRACT(v_item, '$.uuid'));
        SET v_record_data = JSON_EXTRACT(v_item, '$.data');
        
        -- 根据操作类型处理
        CASE v_operation
            WHEN 'CREATE' THEN
                CALL ProcessRecordCreate(v_record_data, p_user_id, p_device_id);
            WHEN 'UPDATE' THEN  
                CALL ProcessRecordUpdate(v_record_uuid, v_record_data, p_user_id, p_device_id);