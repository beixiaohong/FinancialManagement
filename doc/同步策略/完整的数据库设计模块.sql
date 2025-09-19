-- =====================================================
-- 离线优先记账应用 - 完整数据库设计
-- =====================================================

-- =====================================================
-- 1. 本地SQLite数据库设计 (app/database/local_schema.sql)
-- =====================================================

-- 设备信息表 - 存储当前设备标识
CREATE TABLE IF NOT EXISTS device_info (
    device_id TEXT PRIMARY KEY,                -- 设备唯一标识(UUID)
    device_name TEXT NOT NULL,                 -- 设备名称
    device_type TEXT NOT NULL,                 -- 设备类型：android/ios/web
    user_id TEXT,                             -- 关联用户ID
    installation_id TEXT UNIQUE,              -- 应用安装标识
    last_sync_token TEXT,                     -- 最后同步令牌
    last_sync_at INTEGER,                     -- 最后同步时间戳
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- 用户表 - 本地缓存的用户信息
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,                      -- UUID
    server_id INTEGER,                        -- 服务器端ID
    username TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    nickname TEXT,
    avatar_url TEXT,
    user_level TEXT DEFAULT 'free',          -- free/member/premium
    user_status TEXT DEFAULT 'active',       -- active/inactive/frozen
    member_expires_at INTEGER,                -- 会员到期时间戳
    
    -- 同步相关字段
    sync_status INTEGER DEFAULT 0,           -- 0:未同步 1:已同步 2:冲突 3:删除
    local_version INTEGER DEFAULT 1,         -- 本地版本号
    server_version INTEGER DEFAULT 0,        -- 服务器版本号
    last_sync_at INTEGER,                    -- 最后同步时间
    device_id TEXT,                          -- 最后修改设备
    conflict_data TEXT,                      -- 冲突数据(JSON)
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    is_deleted INTEGER DEFAULT 0
);

-- 账本表
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,                      -- UUID
    server_id INTEGER,                        -- 服务器端ID
    name TEXT NOT NULL,
    description TEXT,
    account_type TEXT DEFAULT 'personal',    -- personal/family/team/project
    currency TEXT DEFAULT 'CNY',
    icon_url TEXT,
    color TEXT DEFAULT '#1890ff',
    
    -- 统计字段(冗余设计，提高查询性能)
    total_income REAL DEFAULT 0,
    total_expense REAL DEFAULT 0,
    balance REAL DEFAULT 0,
    total_records INTEGER DEFAULT 0,
    member_count INTEGER DEFAULT 1,
    
    -- 所有者信息
    owner_id TEXT NOT NULL,                  -- 本地用户UUID
    owner_server_id INTEGER,                 -- 服务器用户ID
    
    -- 同步相关字段
    sync_status INTEGER DEFAULT 0,
    local_version INTEGER DEFAULT 1,
    server_version INTEGER DEFAULT 0,
    last_sync_at INTEGER,
    device_id TEXT,
    conflict_data TEXT,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    is_deleted INTEGER DEFAULT 0,
    
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

-- 账本成员表
CREATE TABLE IF NOT EXISTS account_members (
    id TEXT PRIMARY KEY,
    server_id INTEGER,
    account_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT DEFAULT 'viewer',              -- admin/editor/viewer
    invite_status TEXT DEFAULT 'accepted',   -- pending/accepted/rejected/expired
    invite_code TEXT,
    invited_by_id TEXT,
    invited_at INTEGER,
    accepted_at INTEGER,
    
    -- 同步相关字段
    sync_status INTEGER DEFAULT 0,
    local_version INTEGER DEFAULT 1,
    server_version INTEGER DEFAULT 0,
    last_sync_at INTEGER,
    device_id TEXT,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    is_deleted INTEGER DEFAULT 0,
    
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(account_id, user_id)
);

-- 支付账户表
CREATE TABLE IF NOT EXISTS payment_accounts (
    id TEXT PRIMARY KEY,
    server_id INTEGER,
    account_id TEXT NOT NULL,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL,              -- savings/credit/investment
    description TEXT,
    
    -- 账户属性
    balance REAL DEFAULT 0,
    credit_limit REAL,                       -- 信用额度
    interest_rate REAL,                      -- 利率
    bill_day INTEGER,                        -- 账单日
    due_day INTEGER,                         -- 还款日
    
    -- 显示设置
    icon_name TEXT,
    color TEXT DEFAULT '#1890ff',
    sort_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    
    -- 同步相关字段
    sync_status INTEGER DEFAULT 0,
    local_version INTEGER DEFAULT 1,
    server_version INTEGER DEFAULT 0,
    last_sync_at INTEGER,
    device_id TEXT,
    conflict_data TEXT,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    is_deleted INTEGER DEFAULT 0,
    
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- 分类表(三级分类)
CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    server_id INTEGER,
    account_id TEXT NOT NULL,                -- 0表示系统默认分类
    name TEXT NOT NULL,
    description TEXT,
    parent_id TEXT,                          -- 父分类ID
    level INTEGER NOT NULL,                  -- 分类层级 1/2/3
    full_path TEXT,                          -- 完整路径: 餐饮/早餐/包子
    
    -- 显示设置
    icon_name TEXT,
    color TEXT DEFAULT '#1890ff',
    sort_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    is_system INTEGER DEFAULT 0,            -- 是否系统预设分类
    
    -- 统计信息(冗余)
    record_count INTEGER DEFAULT 0,
    total_amount REAL DEFAULT 0,
    
    -- 同步相关字段
    sync_status INTEGER DEFAULT 0,
    local_version INTEGER DEFAULT 1,
    server_version INTEGER DEFAULT 0,
    last_sync_at INTEGER,
    device_id TEXT,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    is_deleted INTEGER DEFAULT 0,
    
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);

-- 记账记录表(核心业务表)
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,
    server_id INTEGER,
    account_id TEXT NOT NULL,
    record_type TEXT NOT NULL,               -- income/expense/transfer
    amount REAL NOT NULL,
    record_date INTEGER NOT NULL,            -- 记录日期时间戳
    description TEXT,
    
    -- 关联信息
    creator_id TEXT NOT NULL,
    payment_account_id TEXT NOT NULL,
    category_id TEXT,
    
    -- 转账相关(仅转账类型使用)
    target_payment_account_id TEXT,
    transfer_fee REAL DEFAULT 0,
    
    -- 扩展信息
    tags TEXT,                               -- JSON格式标签数组
    location TEXT,                           -- 消费地点
    weather TEXT,                            -- 天气情况
    mood TEXT,                               -- 心情
    project_name TEXT,                       -- 关联项目
    related_people TEXT,                     -- 关联人员(JSON)
    images TEXT,                             -- 图片URLs(JSON)
    
    -- 业务扩展字段
    is_recurring INTEGER DEFAULT 0,         -- 是否重复记录
    recurring_rule TEXT,                    -- 重复规则(JSON)
    original_record_id TEXT,                -- 原始记录ID(用于重复记录)
    
    -- 同步相关字段
    sync_status INTEGER DEFAULT 0,
    local_version INTEGER DEFAULT 1,
    server_version INTEGER DEFAULT 0,
    last_sync_at INTEGER,
    device_id TEXT,
    conflict_data TEXT,
    hash_value TEXT,                        -- 内容哈希值(用于快速比较)
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    is_deleted INTEGER DEFAULT 0,
    
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (creator_id) REFERENCES users(id),
    FOREIGN KEY (payment_account_id) REFERENCES payment_accounts(id),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (target_payment_account_id) REFERENCES payment_accounts(id)
);

-- 同步队列表 - 待同步的操作队列
CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,               -- 操作的表名
    record_id TEXT NOT NULL,                -- 记录UUID
    operation TEXT NOT NULL,                -- CREATE/UPDATE/DELETE
    priority INTEGER DEFAULT 3,            -- 优先级 1:最高 4:最低
    data TEXT,                              -- 完整记录数据(JSON)
    changes TEXT,                           -- 变更字段(JSON,仅UPDATE使用)
    
    -- 重试机制
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at INTEGER,
    
    -- 状态管理
    status INTEGER DEFAULT 0,              -- 0:待同步 1:同步中 2:已同步 3:失败 4:跳过
    error_message TEXT,
    estimated_size INTEGER DEFAULT 0,      -- 预估数据大小(字节)
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- 冲突解决记录表
CREATE TABLE IF NOT EXISTS conflict_resolutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    conflict_type TEXT NOT NULL,           -- version/field/deletion/concurrent
    
    -- 冲突数据
    local_data TEXT,                       -- 本地数据(JSON)
    server_data TEXT,                      -- 服务器数据(JSON)
    resolved_data TEXT,                    -- 解决后数据(JSON)
    
    -- 解决信息
    resolution_strategy TEXT,             -- auto/manual/merge
    resolution_rule TEXT,                 -- 具体解决规则
    resolved_by TEXT DEFAULT 'system',    -- system/user
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    resolved_at INTEGER
);

-- 本地缓存表 - 存储分析结果等
CREATE TABLE IF NOT EXISTS local_cache (
    cache_key TEXT PRIMARY KEY,
    cache_data TEXT,                       -- JSON数据
    expires_at INTEGER,                    -- 过期时间戳
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- =====================================================
-- 2. 索引设计 - 优化查询性能
-- =====================================================

-- 用户表索引
CREATE INDEX IF NOT EXISTS idx_users_sync ON users(sync_status, updated_at);
CREATE INDEX IF NOT EXISTS idx_users_server ON users(server_id);

-- 账本表索引
CREATE INDEX IF NOT EXISTS idx_accounts_owner ON accounts(owner_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_accounts_sync ON accounts(sync_status);

-- 账本成员表索引
CREATE INDEX IF NOT EXISTS idx_account_members_account ON account_members(account_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_account_members_user ON account_members(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_account_members_unique ON account_members(account_id, user_id) WHERE is_deleted = 0;

-- 支付账户表索引
CREATE INDEX IF NOT EXISTS idx_payment_accounts_account ON payment_accounts(account_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_payment_accounts_active ON payment_accounts(account_id, is_active, sort_order);

-- 分类表索引
CREATE INDEX IF NOT EXISTS idx_categories_account ON categories(account_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_level ON categories(level, is_active);
CREATE INDEX IF NOT EXISTS idx_categories_system ON categories(is_system, account_id);

-- 记录表索引(最重要的性能优化)
CREATE INDEX IF NOT EXISTS idx_records_account_date ON records(account_id, record_date DESC, is_deleted);
CREATE INDEX IF NOT EXISTS idx_records_account_type ON records(account_id, record_type, is_deleted);
CREATE INDEX IF NOT EXISTS idx_records_creator ON records(creator_id, record_date DESC);
CREATE INDEX IF NOT EXISTS idx_records_category ON records(category_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_records_payment_account ON records(payment_account_id);
CREATE INDEX IF NOT EXISTS idx_records_sync ON records(sync_status, updated_at);
CREATE INDEX IF NOT EXISTS idx_records_hash ON records(hash_value);
CREATE INDEX IF NOT EXISTS idx_records_date_range ON records(account_id, record_date, record_type, is_deleted);

-- 同步队列表索引
CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_sync_queue_record ON sync_queue(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_sync_queue_retry ON sync_queue(status, next_retry_at);

-- 冲突解决记录索引
CREATE INDEX IF NOT EXISTS idx_conflict_resolutions_record ON conflict_resolutions(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_conflict_resolutions_time ON conflict_resolutions(created_at);

-- 缓存表索引
CREATE INDEX IF NOT EXISTS idx_local_cache_expires ON local_cache(expires_at);

-- =====================================================
-- 3. 触发器 - 自动维护数据一致性
-- =====================================================

-- 更新时间戳触发器
CREATE TRIGGER IF NOT EXISTS trigger_users_updated_at 
    AFTER UPDATE ON users
    FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = strftime('%s', 'now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trigger_accounts_updated_at
    AFTER UPDATE ON accounts 
    FOR EACH ROW
BEGIN
    UPDATE accounts SET updated_at = strftime('%s', 'now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trigger_records_updated_at
    AFTER UPDATE ON records
    FOR EACH ROW  
BEGIN
    UPDATE records SET updated_at = strftime('%s', 'now') WHERE id = NEW.id;
END;

-- 记录变更触发器 - 自动添加到同步队列
CREATE TRIGGER IF NOT EXISTS trigger_records_sync_insert
    AFTER INSERT ON records
    FOR EACH ROW
    WHEN NEW.sync_status = 0  -- 只有未同步的记录才加入队列
BEGIN
    INSERT INTO sync_queue (table_name, record_id, operation, priority, data)
    VALUES (
        'records', 
        NEW.id, 
        'CREATE', 
        CASE 
            WHEN NEW.amount > 1000 THEN 2  -- 大额交易高优先级
            ELSE 3  -- 普通优先级
        END,
        json_object(
            'id', NEW.id,
            'account_id', NEW.account_id,
            'record_type', NEW.record_type,
            'amount', NEW.amount,
            'record_date', NEW.record_date,
            'description', NEW.description,
            'creator_id', NEW.creator_id,
            'payment_account_id', NEW.payment_account_id,
            'category_id', NEW.category_id,
            'device_id', NEW.device_id,
            'created_at', NEW.created_at
        )
    );
END;

CREATE TRIGGER IF NOT EXISTS trigger_records_sync_update
    AFTER UPDATE ON records
    FOR EACH ROW
    WHEN NEW.sync_status = 0 AND (OLD.sync_status != 0 OR 
         OLD.amount != NEW.amount OR 
         OLD.description != NEW.description OR
         OLD.category_id != NEW.category_id)
BEGIN
    INSERT INTO sync_queue (table_name, record_id, operation, priority, data, changes)
    VALUES (
        'records',
        NEW.id,
        'UPDATE',
        CASE 
            WHEN OLD.amount != NEW.amount THEN 2  -- 金额变更高优先级
            ELSE 3
        END,
        json_object(
            'id', NEW.id,
            'account_id', NEW.account_id,
            'record_type', NEW.record_type,
            'amount', NEW.amount,
            'record_date', NEW.record_date,
            'description', NEW.description,
            'category_id', NEW.category_id,
            'local_version', NEW.local_version,
            'updated_at', NEW.updated_at
        ),
        json_object(
            'old_amount', OLD.amount,
            'new_amount', NEW.amount,
            'old_description', OLD.description,
            'new_description', NEW.description
        )
    );
END;

CREATE TRIGGER IF NOT EXISTS trigger_records_sync_delete
    AFTER UPDATE ON records
    FOR EACH ROW
    WHEN NEW.is_deleted = 1 AND OLD.is_deleted = 0
BEGIN
    INSERT INTO sync_queue (table_name, record_id, operation, priority, data)
    VALUES (
        'records',
        NEW.id,
        'DELETE',
        1,  -- 删除操作最高优先级
        json_object('id', NEW.id, 'is_deleted', 1)
    );
END;

-- 账本统计更新触发器
CREATE TRIGGER IF NOT EXISTS trigger_update_account_stats_insert
    AFTER INSERT ON records
    FOR EACH ROW
    WHEN NEW.is_deleted = 0
BEGIN
    UPDATE accounts 
    SET 
        total_income = total_income + CASE WHEN NEW.record_type = 'income' THEN NEW.amount ELSE 0 END,
        total_expense = total_expense + CASE WHEN NEW.record_type = 'expense' THEN NEW.amount ELSE 0 END,
        balance = balance + CASE 
            WHEN NEW.record_type = 'income' THEN NEW.amount
            WHEN NEW.record_type = 'expense' THEN -NEW.amount
            ELSE 0 END,
        total_records = total_records + 1,
        updated_at = strftime('%s', 'now')
    WHERE id = NEW.account_id;
    
    -- 更新分类统计
    UPDATE categories 
    SET 
        record_count = record_count + 1,
        total_amount = total_amount + CASE WHEN NEW.record_type = 'expense' THEN NEW.amount ELSE 0 END
    WHERE id = NEW.category_id;
END;

-- =====================================================
-- 4. 视图 - 简化复杂查询
-- =====================================================

-- 账本详情视图
CREATE VIEW IF NOT EXISTS v_account_details AS
SELECT 
    a.*,
    u.nickname as owner_name,
    u.avatar_url as owner_avatar,
    COUNT(DISTINCT am.user_id) as actual_member_count,
    COUNT(DISTINCT r.id) as actual_record_count,
    SUM(CASE WHEN r.record_type = 'income' AND r.is_deleted = 0 THEN r.amount ELSE 0 END) as actual_income,
    SUM(CASE WHEN r.record_type = 'expense' AND r.is_deleted = 0 THEN r.amount ELSE 0 END) as actual_expense
FROM accounts a
LEFT JOIN users u ON a.owner_id = u.id
LEFT JOIN account_members am ON a.id = am.account_id AND am.is_deleted = 0
LEFT JOIN records r ON a.id = r.account_id AND r.is_deleted = 0
WHERE a.is_deleted = 0
GROUP BY a.id;

-- 待同步项目视图
CREATE VIEW IF NOT EXISTS v_pending_sync AS
SELECT 
    sq.*,
    CASE 
        WHEN sq.table_name = 'records' THEN r.amount 
        ELSE 0 
    END as amount,
    CASE 
        WHEN sq.table_name = 'records' THEN r.record_type 
        ELSE null 
    END as record_type,
    LENGTH(sq.data) as data_size
FROM sync_queue sq
LEFT JOIN records r ON sq.table_name = 'records' AND sq.record_id = r.id
WHERE sq.status IN (0, 3)  -- 待同步或失败的项目
ORDER BY sq.priority, sq.created_at;

-- 冲突记录视图  
CREATE VIEW IF NOT EXISTS v_conflict_records AS
SELECT 
    r.*,
    'record' as conflict_type,
    r.conflict_data,
    c.name as category_name,
    pa.name as payment_account_name,
    u.nickname as creator_name
FROM records r
LEFT JOIN categories c ON r.category_id = c.id
LEFT JOIN payment_accounts pa ON r.payment_account_id = pa.id  
LEFT JOIN users u ON r.creator_id = u.id
WHERE r.sync_status = 2  -- 冲突状态
ORDER BY r.updated_at DESC;

-- =====================================================
-- 5. 存储过程(SQLite用户定义函数)
-- =====================================================

-- 注意：SQLite不支持存储过程，以下是应用层面的函数实现参考

-- =====================================================
-- 6. 数据初始化脚本
-- =====================================================

-- 插入默认分类数据
INSERT OR IGNORE INTO categories (id, account_id, name, level, icon_name, color, is_system, sort_order) VALUES
-- 一级分类
('cat_income_1', '0', '工资收入', 1, 'work', '#52c41a', 1, 1),
('cat_income_2', '0', '兼职收入', 1, 'part_time', '#13c2c2', 1, 2),
('cat_income_3', '0', '投资收益', 1, 'investment', '#1890ff', 1, 3),
('cat_income_4', '0', '其他收入', 1, 'other', '#722ed1', 1, 4),

('cat_expense_1', '0', '餐饮', 1, 'restaurant', '#ff4d4f', 1, 10),
('cat_expense_2', '0', '交通', 1, 'car', '#fa8c16', 1, 11),
('cat_expense_3', '0', '购物', 1, 'shopping', '#fadb14', 1, 12),
('cat_expense_4', '0', '娱乐', 1, 'game', '#a0d911', 1, 13),
('cat_expense_5', '0', '医疗', 1, 'medical', '#40a9ff', 1, 14),
('cat_expense_6', '0', '教育', 1, 'book', '#b37feb', 1, 15),
('cat_expense_7', '0', '居住', 1, 'home', '#ff85c0', 1, 16),
('cat_expense_8', '0', '其他支出', 1, 'more', '#8c8c8c', 1, 17);

-- 二级分类示例
INSERT OR IGNORE INTO categories (id, account_id, name, parent_id, level, full_path, icon_name, is_system, sort_order) VALUES
('cat_expense_1_1', '0', '早餐', 'cat_expense_1', 2, '餐饮/早餐', 'breakfast', 1, 1),
('cat_expense_1_2', '0', '午餐', 'cat_expense_1', 2, '餐饮/午餐', 'lunch', 1, 2),
('cat_expense_1_3', '0', '晚餐', 'cat_expense_1', 2, '餐饮/晚餐', 'dinner', 1, 3),
('cat_expense_1_4', '0', '零食饮料', 'cat_expense_1', 2, '餐饮/零食饮料', 'snack', 1, 4),

('cat_expense_2_1', '0', '打车/网约车', 'cat_expense_2', 2, '交通/打车网约车', 'taxi', 1, 1),
('cat_expense_2_2', '0', '公交地铁', 'cat_expense_2', 2, '交通/公交地铁', 'subway', 1, 2),
('cat_expense_2_3', '0', '汽油费', 'cat_expense_2', 2, '交通/汽油费', 'gas', 1, 3),
('cat_expense_2_4', '0', '停车费', 'cat_expense_2', 2, '交通/停车费', 'parking', 1, 4);

-- 创建初始设备信息(如果不存在)
INSERT OR IGNORE INTO device_info (device_id, device_name, device_type) 
VALUES ('default_device', '默认设备', 'unknown');

-- =====================================================
-- 7. 数据库版本管理
-- =====================================================

-- 版本信息表
CREATE TABLE IF NOT EXISTS db_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER DEFAULT (strftime('%s', 'now')),
    description TEXT
);

-- 插入当前版本
INSERT OR REPLACE INTO db_version (version, description) VALUES (1, '初始数据库结构');

-- =====================================================
-- 8. 性能优化配置
-- =====================================================

-- SQLite性能优化设置
PRAGMA journal_mode = WAL;          -- 使用WAL模式提高并发性能
PRAGMA synchronous = NORMAL;        -- 平衡安全性和性能
PRAGMA cache_size = -64000;         -- 64MB缓存
PRAGMA temp_store = MEMORY;         -- 临时表存储在内存
PRAGMA mmap_size = 134217728;       -- 128MB内存映射
PRAGMA optimize;                    -- 优化统计信息

-- =====================================================
-- 9. 数据库维护函数
-- =====================================================

-- 清理过期缓存
DELETE FROM local_cache WHERE expires_at < strftime('%s', 'now');

-- 清理已同步的队列项目(保留最近7天)
DELETE FROM sync_queue 
WHERE status = 2 
AND created_at < strftime('%s', 'now', '-7 days');

-- 清理旧的冲突解决记录(保留最近30天)  
DELETE FROM conflict_resolutions 
WHERE resolved_at IS NOT NULL 
AND resolved_at < strftime('%s', 'now', '-30 days');

-- =====================================================
-- 10. 数据完整性检查
-- =====================================================

-- 检查孤立记录
SELECT COUNT(*) as orphaned_records
FROM records r
WHERE r.account_id NOT IN (SELECT id FROM accounts WHERE is_deleted = 0)
AND r.is_deleted = 0;

-- 检查同步状态一致性
SELECT 
    table_name,
    COUNT(*) as pending_count,
    MIN(created_at) as oldest_pending
FROM sync_queue 
WHERE status = 0
GROUP BY table_name;

-- 检查数据版本冲突
SELECT COUNT(*) as version_conflicts
FROM records 
WHERE local_version > server_version + 1
AND sync_status != 0;