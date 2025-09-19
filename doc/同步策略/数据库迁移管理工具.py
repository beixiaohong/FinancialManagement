# app/database/migration_manager.py
import os
import sqlite3
import pymysql
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MigrationInfo:
    version: str
    description: str
    sql_file: str
    checksum: str
    executed_at: Optional[datetime] = None

class DatabaseMigrationManager:
    """数据库迁移管理器 - 支持SQLite和MySQL"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.migration_dir = Path(config.get('migration_dir', 'migrations'))
        self.database_type = config.get('type', 'sqlite')  # sqlite or mysql
        
    def get_connection(self):
        """获取数据库连接"""
        if self.database_type == 'sqlite':
            return sqlite3.connect(self.config['database'])
        elif self.database_type == 'mysql':
            return pymysql.connect(**self.config['mysql'])
        else:
            raise ValueError(f"Unsupported database type: {self.database_type}")
    
    def init_migration_table(self):
        """初始化迁移记录表"""
        with self.get_connection() as conn:
            if self.database_type == 'sqlite':
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version TEXT PRIMARY KEY,
                        description TEXT,
                        checksum TEXT,
                        executed_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:  # mysql
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(50) PRIMARY KEY,
                        description TEXT,
                        checksum VARCHAR(64),
                        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            conn.commit()
    
    def get_migration_files(self) -> List[MigrationInfo]:
        """获取所有迁移文件"""
        migrations = []
        
        if not self.migration_dir.exists():
            self.migration_dir.mkdir(parents=True)
            return migrations
        
        # 扫描迁移文件（格式：YYYY.MM.DD.XXX_description.sql）
        for file_path in sorted(self.migration_dir.glob("*.sql")):
            filename = file_path.stem
            parts = filename.split('_', 1)
            
            if len(parts) == 2:
                version, description = parts
                
                # 计算文件校验和
                with open(file_path, 'rb') as f:
                    content = f.read()
                    checksum = hashlib.sha256(content).hexdigest()
                
                migrations.append(MigrationInfo(
                    version=version,
                    description=description.replace('_', ' '),
                    sql_file=str(file_path),
                    checksum=checksum
                ))
        
        return migrations
    
    def get_executed_migrations(self) -> Dict[str, MigrationInfo]:
        """获取已执行的迁移"""
        executed = {}
        
        try:
            with self.get_connection() as conn:
                if self.database_type == 'sqlite':
                    cursor = conn.execute("""
                        SELECT version, description, checksum, executed_at 
                        FROM schema_migrations ORDER BY version
                    """)
                else:  # mysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("""
                        SELECT version, description, checksum, executed_at 
                        FROM schema_migrations ORDER BY version
                    """)
                
                for row in cursor.fetchall():
                    if self.database_type == 'sqlite':
                        row = dict(row)
                    
                    executed[row['version']] = MigrationInfo(
                        version=row['version'],
                        description=row['description'],
                        sql_file='',
                        checksum=row['checksum'],
                        executed_at=datetime.fromisoformat(row['executed_at']) 
                                   if isinstance(row['executed_at'], str) 
                                   else row['executed_at']
                    )
        
        except Exception as e:
            logger.warning(f"Could not get executed migrations: {e}")
        
        return executed
    
    def get_pending_migrations(self) -> List[MigrationInfo]:
        """获取待执行的迁移"""
        all_migrations = self.get_migration_files()
        executed_migrations = self.get_executed_migrations()
        
        pending = []
        for migration in all_migrations:
            if migration.version not in executed_migrations:
                pending.append(migration)
            else:
                # 检查校验和是否匹配
                executed = executed_migrations[migration.version]
                if executed.checksum != migration.checksum:
                    logger.warning(f"Migration {migration.version} checksum mismatch!")
        
        return pending
    
    def execute_migration(self, migration: MigrationInfo) -> bool:
        """执行单个迁移"""
        try:
            logger.info(f"Executing migration: {migration.version} - {migration.description}")
            
            # 读取SQL文件
            with open(migration.sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 执行迁移
            with self.get_connection() as conn:
                # 分割并执行SQL语句
                statements = self._split_sql_statements(sql_content)
                
                if self.database_type == 'mysql':
                    cursor = conn.cursor()
                    for statement in statements:
                        if statement.strip():
                            cursor.execute(statement)
                else:  # sqlite
                    for statement in statements:
                        if statement.strip():
                            conn.execute(statement)
                
                # 记录迁移执行
                self._record_migration_execution(conn, migration)
                conn.commit()
                
            logger.info(f"Migration {migration.version} executed successfully")
            return True
            