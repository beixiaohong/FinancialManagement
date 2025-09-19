                            WHEN cast(strftime('%H', datetime(record_date, 'unixepoch')) as integer) BETWEEN 18 AND 23 THEN '晚上'
                            ELSE '深夜'
                        END as time_period,
                        COUNT(*) as record_count,
                        SUM(amount) as total_amount,
                        AVG(amount) as avg_amount
                    FROM records r
                    WHERE r.account_id = ? AND r.is_deleted = 0 {time_condition}
                    GROUP BY time_period
                    ORDER BY 
                        CASE time_period 
                            WHEN '上午' THEN 1 
                            WHEN '下午' THEN 2 
                            WHEN '晚上' THEN 3 
                            ELSE 4 
                        END
                """
                
                time_patterns = conn.execute(time_pattern_sql, time_params).fetchall()
                
                # 6. 预算分析（如果有预算设置）
                budget_analysis = self._get_budget_analysis(conn, account_id, date_range)
                
                # 组装结果
                result = {
                    'summary': {
                        'total_income': float(basic_stats['total_income'] or 0),
                        'total_expense': float(basic_stats['total_expense'] or 0),
                        'net_income': float((basic_stats['total_income'] or 0) - (basic_stats['total_expense'] or 0)),
                        'income_count': basic_stats['income_count'] or 0,
                        'expense_count': basic_stats['expense_count'] or 0,
                        'total_records': basic_stats['total_records'] or 0,
                        'avg_expense': float(basic_stats['avg_expense'] or 0),
                        'max_expense': float(basic_stats['max_expense'] or 0),
                        'min_expense': float(basic_stats['min_expense'] or 0)
                    },
                    'category_breakdown': [dict(row) for row in category_stats],
                    'monthly_trend': [dict(row) for row in monthly_trend],
                    'account_distribution': [dict(row) for row in account_distribution],
                    'time_patterns': [dict(row) for row in time_patterns],
                    'budget_analysis': budget_analysis,
                    'date_range': {
                        'start': date_range[0].isoformat() if date_range else None,
                        'end': date_range[1].isoformat() if date_range else None
                    },
                    'generated_at': datetime.now().isoformat()
                }
                
                # 缓存结果
                if use_cache:
                    self._set_cache(cache_key, result, ttl=1800)  # 30分钟缓存
                
                return result
                
        except Exception as e:
            logger.error(f"获取高级分析失败: {e}")
            return {'error': str(e)}
        finally:
            self.db._record_query_stats('get_advanced_analytics', time.time() - start_time)
    
    def batch_operations(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量操作"""
        start_time = time.time()
        results = {
            'total': len(operations),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            with self.db.pool.get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                
                try:
                    for op in operations:
                        op_type = op.get('type')
                        
                        if op_type == 'create':
                            record = Record(**op['data'])
                            self._insert_record(conn, record)
                            results['successful'] += 1
                            
                        elif op_type == 'update':
                            record_id = op['record_id']
                            updates = op['data']
                            if self._update_record_by_id(conn, record_id, updates):
                                results['successful'] += 1
                            else:
                                results['failed'] += 1
                                results['errors'].append(f"Update failed for record {record_id}")
                                
                        elif op_type == 'delete':
                            record_id = op['record_id']
                            if self._soft_delete_record(conn, record_id):
                                results['successful'] += 1
                            else:
                                results['failed'] += 1
                                results['errors'].append(f"Delete failed for record {record_id}")
                    
                    conn.commit()
                    logger.info(f"批量操作完成: {results['successful']}/{results['total']}")
                    
                except Exception as e:
                    conn.rollback()
                    results['failed'] = results['total']
                    results['successful'] = 0
                    results['errors'].append(f"Batch operation failed: {e}")
                    logger.error(f"批量操作失败: {e}")
                    
        except Exception as e:
            logger.error(f"批量操作执行失败: {e}")
            results['errors'].append(str(e))
            
        finally:
            self.db._record_query_stats('batch_operations', time.time() - start_time)
            
        return results
    
    def search_records(self, account_id: str, search_query: str, 
                      filters: Optional[Dict] = None,
                      limit: int = 50) -> List[Dict[str, Any]]:
        """全文搜索记录"""
        start_time = time.time()
        
        try:
            with self.db.pool.get_connection() as conn:
                # 构建搜索查询
                search_terms = search_query.strip().split()
                search_conditions = []
                search_params = [account_id]
                
                for term in search_terms:
                    term_pattern = f"%{term}%"
                    search_conditions.append("""
                        (r.description LIKE ? OR 
                         r.location LIKE ? OR 
                         r.project_name LIKE ? OR 
                         c.name LIKE ? OR 
                         pa.name LIKE ?)
                    """)
                    search_params.extend([term_pattern] * 5)
                
                search_clause = " AND ".join(search_conditions)
                
                # 构建完整查询
                sql = f"""
                    SELECT 
                        r.*,
                        c.name as category_name,
                        c.icon_name as category_icon,
                        pa.name as payment_account_name,
                        -- 计算相关性分数
                        (
                            CASE WHEN r.description LIKE ? THEN 10 ELSE 0 END +
                            CASE WHEN r.location LIKE ? THEN 5 ELSE 0 END +
                            CASE WHEN c.name LIKE ? THEN 3 ELSE 0 END
                        ) as relevance_score
                    FROM records r
                    LEFT JOIN categories c ON r.category_id = c.id
                    LEFT JOIN payment_accounts pa ON r.payment_account_id = pa.id
                    WHERE r.account_id = ? 
                        AND r.is_deleted = 0 
                        AND ({search_clause})
                    ORDER BY relevance_score DESC, r.record_date DESC
                    LIMIT ?
                """
                
                # 为相关性计算添加参数
                relevance_params = [f"%{search_query}%"] * 3
                final_params = relevance_params + search_params + [limit]
                
                cursor = conn.execute(sql, final_params)
                results = []
                
                for row in cursor.fetchall():
                    record_dict = dict(row)
                    # 转换时间戳
                    record_dict['record_date'] = datetime.fromtimestamp(record_dict['record_date'])
                    record_dict['created_at'] = datetime.fromtimestamp(record_dict['created_at'])
                    record_dict['updated_at'] = datetime.fromtimestamp(record_dict['updated_at'])
                    
                    # 解析JSON字段
                    for field in ['tags', 'related_people', 'images']:
                        if record_dict.get(field):
                            try:
                                record_dict[field] = json.loads(record_dict[field])
                            except json.JSONDecodeError:
                                record_dict[field] = []
                    
                    # 高亮搜索关键词
                    record_dict['highlighted_description'] = self._highlight_text(
                        record_dict.get('description', ''), search_terms
                    )
                    
                    results.append(record_dict)
                
                return results
                
        except Exception as e:
            logger.error(f"搜索记录失败: {e}")
            return []
        finally:
            self.db._record_query_stats('search_records', time.time() - start_time)
    
    def get_duplicate_records(self, account_id: str, 
                            similarity_threshold: float = 0.8) -> List[List[Dict]]:
        """检测重复记录"""
        start_time = time.time()
        
        try:
            with self.db.pool.get_connection() as conn:
                # 获取所有记录
                sql = """
                    SELECT id, amount, description, record_date, category_id, payment_account_id
                    FROM records 
                    WHERE account_id = ? AND is_deleted = 0
                    ORDER BY record_date DESC
                """
                
                cursor = conn.execute(sql, (account_id,))
                records = [dict(row) for row in cursor.fetchall()]
                
                # 检测重复
                duplicates = []
                processed_ids = set()
                
                for i, record1 in enumerate(records):
                    if record1['id'] in processed_ids:
                        continue
                        
                    similar_group = [record1]
                    
                    for j, record2 in enumerate(records[i+1:], i+1):
                        if record2['id'] in processed_ids:
                            continue
                            
                        similarity = self._calculate_record_similarity(record1, record2)
                        
                        if similarity >= similarity_threshold:
                            similar_group.append(record2)
                            processed_ids.add(record2['id'])
                    
                    if len(similar_group) > 1:
                        processed_ids.add(record1['id'])
                        duplicates.append(similar_group)
                
                return duplicates
                
        except Exception as e:
            logger.error(f"检测重复记录失败: {e}")
            return []
        finally:
            self.db._record_query_stats('get_duplicate_records', time.time() - start_time)
    
    def _calculate_record_similarity(self, record1: Dict, record2: Dict) -> float:
        """计算记录相似度"""
        score = 0.0
        total_weight = 0.0
        
        # 金额相似度 (权重: 0.4)
        if record1['amount'] == record2['amount']:
            score += 0.4
        elif abs(record1['amount'] - record2['amount']) / max(record1['amount'], record2['amount']) < 0.1:
            score += 0.2
        total_weight += 0.4
        
        # 描述相似度 (权重: 0.3)
        desc1 = record1.get('description', '').lower()
        desc2 = record2.get('description', '').lower()
        if desc1 and desc2:
            desc_similarity = self._text_similarity(desc1, desc2)
            score += desc_similarity * 0.3
        total_weight += 0.3
        
        # 日期相似度 (权重: 0.2)
        date_diff = abs(record1['record_date'] - record2['record_date'])
        if date_diff <= 86400:  # 1天内
            score += 0.2
        elif date_diff <= 259200:  # 3天内
            score += 0.1
        total_weight += 0.2
        
        # 分类相似度 (权重: 0.1)
        if record1.get('category_id') == record2.get('category_id'):
            score += 0.1
        total_weight += 0.1
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简单实现）"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _highlight_text(self, text: str, search_terms: List[str]) -> str:
        """高亮搜索关键词"""
        if not text or not search_terms:
            return text
        
        highlighted = text
        for term in search_terms:
            highlighted = highlighted.replace(
                term, 
                f"<mark>{term}</mark>", 
                # 忽略大小写
            )
        
        return highlighted
    
    def _get_budget_analysis(self, conn: sqlite3.Connection, 
                           account_id: str, 
                           date_range: Optional[Tuple[datetime, datetime]]) -> Dict:
        """获取预算分析（如果实现了预算功能）"""
        # 这里可以实现预算相关的分析
        # 目前返回空字典作为占位符
        return {
            'budgets': [],
            'overspent_categories': [],
            'savings_opportunities': []
        }
    
    def _calculate_hash(self, record: Record) -> str:
        """计算记录哈希"""
        content = {
            'account_id': record.account_id,
            'record_type': record.record_type,
            'amount': record.amount,
            'record_date': record.record_date.isoformat(),
            'description': record.description,
            'category_id': record.category_id,
            'payment_account_id': record.payment_account_id
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    
    def _calculate_hash_from_dict(self, data: Dict) -> str:
        """从字典计算哈希"""
        content = {k: v for k, v in data.items() 
                  if k not in ['sync_status', 'local_version', 'server_version', 
                             'device_id', 'hash_value', 'created_at', 'updated_at']}
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    
    def _insert_record(self, conn: sqlite3.Connection, record: Record):
        """插入记录到数据库"""
        data = asdict(record)
        
        # 转换特殊字段
        data['record_date'] = int(record.record_date.timestamp())
        data['created_at'] = int(record.created_at.timestamp())
        data['updated_at'] = int(record.updated_at.timestamp())
        data['sync_status'] = record.sync_status.value
        data['tags'] = json.dumps(record.tags)
        data['related_people'] = json.dumps(record.related_people)
        data['images'] = json.dumps(record.images)
        data['is_deleted'] = 1 if record.is_deleted else 0
        
        # 移除None值
        data = {k: v for k, v in data.items() if v is not None}
        
        fields = list(data.keys())
        placeholders = ', '.join(['?' for _ in fields])
        values = [data[field] for field in fields]
        
        sql = f"INSERT INTO records ({', '.join(fields)}) VALUES ({placeholders})"
        conn.execute(sql, values)
    
    def _get_record_by_id(self, conn: sqlite3.Connection, record_id: str) -> Optional[Dict]:
        """根据ID获取记录"""
        cursor = conn.execute("SELECT * FROM records WHERE id = ? AND is_deleted = 0", (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def _update_record_data(self, conn: sqlite3.Connection, record_id: str, data: Dict):
        """更新记录数据"""
        update_fields = {k: v for k, v in data.items() if k != 'id'}
        set_clause = ', '.join([f"{field} = ?" for field in update_fields.keys()])
        values = list(update_fields.values()) + [record_id]
        
        sql = f"UPDATE records SET {set_clause} WHERE id = ?"
        conn.execute(sql, values)
    
    def _update_record_by_id(self, conn: sqlite3.Connection, record_id: str, updates: Dict) -> bool:
        """根据ID更新记录"""
        try:
            current = self._get_record_by_id(conn, record_id)
            if not current:
                return False
            
            updated_data = dict(current)
            updated_data.update(updates)
            updated_data['updated_at'] = int(datetime.now().timestamp())
            updated_data['local_version'] = current['local_version'] + 1
            updated_data['sync_status'] = SyncStatus.NOT_SYNCED.value
            
            self._update_record_data(conn, record_id, updated_data)
            return True
        except Exception:
            return False
    
    def _soft_delete_record(self, conn: sqlite3.Connection, record_id: str) -> bool:
        """软删除记录"""
        try:
            conn.execute("""
                UPDATE records 
                SET is_deleted = 1, 
                    updated_at = ?, 
                    local_version = local_version + 1,
                    sync_status = ?
                WHERE id = ? AND is_deleted = 0
            """, (int(datetime.now().timestamp()), SyncStatus.NOT_SYNCED.value, record_id))
            return True
        except Exception:
            return False
    
    def _mark_conflict(self, conn: sqlite3.Connection, record_id: str, conflicting_data: Dict):
        """标记冲突记录"""
        conflict_data = json.dumps(conflicting_data)
        conn.execute("""
            UPDATE records 
            SET sync_status = ?, conflict_data = ?, updated_at = ?
            WHERE id = ?
        """, (SyncStatus.CONFLICT.value, conflict_data, int(datetime.now().timestamp()), record_id))
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self.db._cache_lock:
            if key in self.db._cache:
                # 检查是否过期
                if key in self.db._cache_ttl:
                    if datetime.now().timestamp() > self.db._cache_ttl[key]:
                        del self.db._cache[key]
                        del self.db._cache_ttl[key]
                        return None
                
                return self.db._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存"""
        with self.db._cache_lock:
            self.db._cache[key] = value
            self.db._cache_ttl[key] = datetime.now().timestamp() + ttl

class SyncQueueManager:
    """同步队列管理器"""
    
    def __init__(self, db_manager: AdvancedDatabaseManager):
        self.db = db_manager
    
    def add_to_queue(self, item: SyncQueueItem) -> int:
        """添加项目到同步队列"""
        try:
            with self.db.pool.get_connection() as conn:
                sql = """
                    INSERT INTO sync_queue 
                    (table_name, record_id, operation, priority, data, changes, 
                     retry_count, max_retries, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor = conn.execute(sql, (
                    item.table_name,
                    item.record_id, 
                    item.operation,
                    item.priority.value,
                    json.dumps(item.data),
                    json.dumps(item.changes) if item.changes else None,
                    item.retry_count,
                    item.max_retries,
                    item.status,
                    int(item.created_at.timestamp()),
                    int(item.updated_at.timestamp())
                ))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"添加同步队列项目失败: {e}")
            return 0
    
    def get_pending_items(self, limit: int = 50, 
                         priority_filter: Optional[List[Priority]] = None) -> List[SyncQueueItem]:
        """获取待同步项目"""
        try:
            with self.db.pool.get_connection() as conn:
                conditions = ["status IN (0, 3)"]  # 待同步或失败
                params = []
                
                if priority_filter:
                    priority_values = [p.value for p in priority_filter]
                    placeholders = ','.join(['?' for _ in priority_values])
                    conditions.append(f"priority IN ({placeholders})")
                    params.extend(priority_values)
                
                # 检查重试时间
                current_time = int(datetime.now().timestamp())
                conditions.append("(next_retry_at IS NULL OR next_retry_at <= ?)")
                params.append(current_time)
                
                sql = f"""
                    SELECT * FROM sync_queue 
                    WHERE {' AND '.join(conditions)}
                    ORDER BY priority ASC, created_at ASC
                    LIMIT ?
                """
                params.append(limit)
                
                cursor = conn.execute(sql, params)
                items = []
                
                for row in cursor.fetchall():
                    row_dict = dict(row)
                    
                    # 转换时间戳
                    row_dict['created_at'] = datetime.fromtimestamp(row_dict['created_at'])
                    row_dict['updated_at'] = datetime.fromtimestamp(row_dict['updated_at'])
                    
                    # 解析JSON数据
                    row_dict['data'] = json.loads(row_dict['data']) if row_dict['data'] else {}
                    row_dict['changes'] = json.loads(row_dict['changes']) if row_dict['changes'] else None
                    
                    # 转换优先级
                    row_dict['priority'] = Priority(row_dict['priority'])
                    
                    items.append(SyncQueueItem(**row_dict))
                
                return items
                
        except Exception as e:
            logger.error(f"获取同步队列失败: {e}")
            return []
    
    def mark_completed(self, queue_id: int, server_version: Optional[int] = None):
        """标记同步完成"""
        try:
            with self.db.pool.get_connection() as conn:
                # 更新队列状态
                conn.execute("""
                    UPDATE sync_queue 
                    SET status = 2, updated_at = ?
                    WHERE id = ?
                """, (int(datetime.now().timestamp()), queue_id))
                
                # 如果有服务器版本，更新原记录
                if server_version:
                    queue_item = conn.execute(
                        "SELECT table_name, record_id FROM sync_queue WHERE id = ?", 
                        (queue_id,)
                    ).fetchone()
                    
                    if queue_item and queue_item['table_name'] == 'records':
                        conn.execute("""
                            UPDATE records 
                            SET sync_status = ?, 
                                server_version = ?,
                                last_sync_at = ?
                            WHERE id = ?
                        """, (SyncStatus.SYNCED.value, server_version, 
                             int(datetime.now().timestamp()), queue_item['record_id']))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"标记同步完成失败: {e}")
    
    def mark_failed(self, queue_id: int, error_message: str):
        """标记同步失败"""
        try:
            with self.db.pool.get_connection() as conn:
                # 获取当前重试信息
                cursor = conn.execute(
                    "SELECT retry_count, max_retries FROM sync_queue WHERE id = ?", 
                    (queue_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    retry_count = row['retry_count'] + 1
                    max_retries = row['max_retries']
                    
                    if retry_count >= max_retries:
                        # 超过最大重试次数
                        status = 3
                        next_retry_at = None
                    else:
                        # 计算下次重试时间（指数退避）
                        delay_seconds = min(2 ** retry_count * 60, 3600)  # 最大1小时
                        next_retry_at = int(datetime.now().timestamp()) + delay_seconds
                        status = 3  # 失败状态，等待重试
                    
                    conn.execute("""
                        UPDATE sync_queue 
                        SET retry_count = ?, 
                            status = ?,
                            next_retry_at = ?,
                            error_message = ?,
                            updated_at = ?
                        WHERE id = ?
                    """, (retry_count, status, next_retry_at, error_message,
                         int(datetime.now().timestamp()), queue_id))
                    
                    conn.commit()
                
        except Exception as e:
            logger.error(f"标记同步失败失败: {e}")
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        try:
            with self.db.pool.get_connection() as conn:
                stats_sql = """
                    SELECT 
                        status,
                        COUNT(*) as count,
                        AVG(retry_count) as avg_retries
                    FROM sync_queue 
                    GROUP BY status
                """
                
                cursor = conn.execute(stats_sql)
                status_stats = {
                    'pending': 0,
                    'syncing': 0, 
                    'completed': 0,
                    'failed': 0
                }
                
                status_names = {0: 'pending', 1: 'syncing', 2: 'completed', 3: 'failed'}
                
                for row in cursor.fetchall():
                    status_name = status_names.get(row['status'], 'unknown')
                    status_stats[status_name] = row['count']
                
                # 获取优先级统计
                priority_sql = """
                    SELECT priority, COUNT(*) as count
                    FROM sync_queue 
                    WHERE status IN (0, 3)
                    GROUP BY priority
                """
                
                cursor = conn.execute(priority_sql)
                priority_stats = {}
                priority_names = {1: 'critical', 2: 'high', 3: 'normal', 4: 'low'}
                
                for row in cursor.fetchall():
                    priority_name = priority_names.get(row['priority'], 'unknown')
                    priority_stats[priority_name] = row['count']
                
                # 获取最近的错误
                recent_errors_sql = """
                    SELECT error_message, COUNT(*) as count
                    FROM sync_queue 
                    WHERE status = 3 AND error_message IS NOT NULL
                        AND updated_at > ?
                    GROUP BY error_message
                    ORDER BY count DESC
                    LIMIT 5
                """
                
                last_hour = int((datetime.now() - timedelta(hours=1)).timestamp())
                cursor = conn.execute(recent_errors_sql, (last_hour,))
                recent_errors = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'status_breakdown': status_stats,
                    'priority_breakdown': priority_stats,
                    'recent_errors': recent_errors,
                    'total_pending': status_stats['pending'] + status_stats['failed'],
                    'success_rate': (
                        status_stats['completed'] / 
                        max(sum(status_stats.values()), 1) * 100
                    )
                }
                
        except Exception as e:
            logger.error(f"获取队列统计失败: {e}")
            return {}

# 使用示例和测试
class DatabaseService:
    """数据库服务门面类"""
    
    def __init__(self, db_path: str = "accounting.db"):
        self.db_manager = AdvancedDatabaseManager(db_path)
        self.record_service = RecordService(self.db_manager)
        self.sync_queue = SyncQueueManager(self.db_manager)
        
        # 注册事件回调
        self.db_manager.register_event_callback('record_created', self._on_record_created)
        self.db_manager.register_event_callback('record_updated', self._on_record_updated)
    
    def _on_record_created(self, data: Dict):
        """记录创建事件回调"""
        logger.info(f"记录已创建: {data['record_id']}")
    
    def _on_record_updated(self, data: Dict):
        """记录更新事件回调"""
        logger.info(f"记录已更新: {data['record_id']}, 版本: {data['version']}")
    
    def create_expense_record(self, account_id: str, amount: float, 
                            description: str = "", **kwargs) -> str:
        """创建支出记录的便捷方法"""
        record = Record(
            id=str(uuid.uuid4()),
            account_id=account_id,
            record_type="expense",
            amount=amount,
            record_date=kwargs.get('record_date', datetime.now()),
            description=description,
            creator_id=kwargs.get('creator_id'),
            payment_account# app/database/advanced_database_manager.py
import sqlite3
import json
import uuid
import hashlib
import logging
import asyncio
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from pathlib import Path
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import weakref

logger = logging.getLogger(__name__)

# 数据模型定义
class SyncStatus(Enum):
    NOT_SYNCED = 0
    SYNCED = 1
    CONFLICT = 2
    FAILED = 3

class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

@dataclass
class Record:
    id: str
    account_id: str
    record_type: str  # income/expense/transfer
    amount: float
    record_date: datetime
    description: str = ""
    creator_id: Optional[str] = None
    payment_account_id: Optional[str] = None
    category_id: Optional[str] = None
    tags: List[str] = None
    location: Optional[str] = None
    project_name: Optional[str] = None
    related_people: List[str] = None
    images: List[str] = None
    
    # 同步相关字段
    sync_status: SyncStatus = SyncStatus.NOT_SYNCED
    local_version: int = 1
    server_version: int = 0
    device_id: Optional[str] = None
    hash_value: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    is_deleted: bool = False
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.related_people is None:
            self.related_people = []
        if self.images is None:
            self.images = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass
class SyncQueueItem:
    id: Optional[int]
    table_name: str
    record_id: str
    operation: str  # CREATE/UPDATE/DELETE
    priority: Priority
    data: Dict[str, Any]
    changes: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3
    status: int = 0  # 0:待同步 1:同步中 2:已同步 3:失败
    error_message: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class DatabaseConnectionPool:
    """数据库连接池"""
    
    def __init__(self, db_path: str, pool_size: int = 10):
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool = []
        self._used_connections = set()
        self._lock = threading.RLock()
        self._init_pool()
    
    def _init_pool(self):
        """初始化连接池"""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            self._pool.append(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """创建新的数据库连接"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -64000")
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn
    
    @contextmanager
    def get_connection(self):
        """获取连接的上下文管理器"""
        conn = None
        try:
            with self._lock:
                if self._pool:
                    conn = self._pool.pop()
                else:
                    conn = self._create_connection()
                self._used_connections.add(conn)
            
            yield conn
            
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise
        finally:
            if conn:
                with self._lock:
                    self._used_connections.discard(conn)
                    if len(self._pool) < self.pool_size:
                        try:
                            # 验证连接是否仍然有效
                            conn.execute("SELECT 1")
                            self._pool.append(conn)
                        except:
                            conn.close()
                            # 创建新连接补充池
                            try:
                                new_conn = self._create_connection()
                                self._pool.append(new_conn)
                            except:
                                pass
                    else:
                        conn.close()
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            # 关闭池中的连接
            for conn in self._pool:
                try:
                    conn.close()
                except:
                    pass
            self._pool.clear()
            
            # 关闭正在使用的连接
            for conn in list(self._used_connections):
                try:
                    conn.close()
                except:
                    pass
            self._used_connections.clear()

class QueryBuilder:
    """SQL查询构建器"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self._select_fields = []
        self._from_table = ""
        self._joins = []
        self._where_conditions = []
        self._group_by = []
        self._having_conditions = []
        self._order_by = []
        self._limit_clause = ""
        self._params = []
        return self
    
    def select(self, *fields):
        self._select_fields.extend(fields)
        return self
    
    def from_table(self, table, alias=None):
        self._from_table = f"{table}" + (f" {alias}" if alias else "")
        return self
    
    def left_join(self, table, condition, alias=None):
        table_clause = f"{table}" + (f" {alias}" if alias else "")
        self._joins.append(f"LEFT JOIN {table_clause} ON {condition}")
        return self
    
    def inner_join(self, table, condition, alias=None):
        table_clause = f"{table}" + (f" {alias}" if alias else "")
        self._joins.append(f"INNER JOIN {table_clause} ON {condition}")
        return self
    
    def where(self, condition, *params):
        self._where_conditions.append(condition)
        self._params.extend(params)
        return self
    
    def where_in(self, field, values):
        if values:
            placeholders = ','.join(['?' for _ in values])
            self._where_conditions.append(f"{field} IN ({placeholders})")
            self._params.extend(values)
        return self
    
    def where_between(self, field, start, end):
        self._where_conditions.append(f"{field} BETWEEN ? AND ?")
        self._params.extend([start, end])
        return self
    
    def group_by(self, *fields):
        self._group_by.extend(fields)
        return self
    
    def having(self, condition, *params):
        self._having_conditions.append(condition)
        self._params.extend(params)
        return self
    
    def order_by(self, field, direction="ASC"):
        self._order_by.append(f"{field} {direction}")
        return self
    
    def limit(self, count, offset=None):
        if offset:
            self._limit_clause = f"LIMIT {count} OFFSET {offset}"
        else:
            self._limit_clause = f"LIMIT {count}"
        return self
    
    def build(self) -> Tuple[str, List]:
        """构建最终的SQL语句和参数"""
        # SELECT子句
        select_clause = "SELECT " + (
            ", ".join(self._select_fields) if self._select_fields else "*"
        )
        
        # FROM子句
        if not self._from_table:
            raise ValueError("FROM table is required")
        from_clause = f"FROM {self._from_table}"
        
        # JOIN子句
        join_clause = " ".join(self._joins)
        
        # WHERE子句
        where_clause = ""
        if self._where_conditions:
            where_clause = "WHERE " + " AND ".join(self._where_conditions)
        
        # GROUP BY子句
        group_clause = ""
        if self._group_by:
            group_clause = "GROUP BY " + ", ".join(self._group_by)
        
        # HAVING子句
        having_clause = ""
        if self._having_conditions:
            having_clause = "HAVING " + " AND ".join(self._having_conditions)
        
        # ORDER BY子句
        order_clause = ""
        if self._order_by:
            order_clause = "ORDER BY " + ", ".join(self._order_by)
        
        # 组装完整SQL
        sql_parts = [select_clause, from_clause]
        if join_clause:
            sql_parts.append(join_clause)
        if where_clause:
            sql_parts.append(where_clause)
        if group_clause:
            sql_parts.append(group_clause)
        if having_clause:
            sql_parts.append(having_clause)
        if order_clause:
            sql_parts.append(order_clause)
        if self._limit_clause:
            sql_parts.append(self._limit_clause)
        
        sql = " ".join(sql_parts)
        return sql, self._params

class AdvancedDatabaseManager:
    """高级数据库管理器"""
    
    def __init__(self, db_path: str = "accounting.db", pool_size: int = 10):
        self.db_path = Path(db_path)
        self.device_id = self._get_or_create_device_id()
        self.pool = DatabaseConnectionPool(str(self.db_path), pool_size)
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # 事件回调
        self._event_callbacks = {}
        
        # 缓存管理
        self._cache = {}
        self._cache_ttl = {}
        self._cache_lock = threading.RLock()
        
        # 批处理队列
        self._batch_queue = []
        self._batch_lock = threading.Lock()
        self._batch_timer = None
        
        # 性能监控
        self._query_stats = {}
        self._stats_lock = threading.RLock()
        
        self._init_database()
        
    def _init_database(self):
        """初始化数据库"""
        try:
            # 确保数据库目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self.pool.get_connection() as conn:
                self._create_tables(conn)
                self._ensure_device_info(conn)
                conn.commit()
                
            logger.info(f"数据库初始化完成: {self.db_path}")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _create_tables(self, conn: sqlite3.Connection):
        """创建数据库表"""
        # 读取schema文件
        schema_file = Path(__file__).parent / "local_schema.sql"
        if schema_file.exists():
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # 分割并执行SQL语句
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            for statement in statements:
                if statement and not statement.startswith('--'):
                    try:
                        conn.execute(statement)
                    except sqlite3.Error as e:
                        logger.warning(f"执行SQL语句失败: {e}")
    
    def _get_or_create_device_id(self) -> str:
        """获取或创建设备ID"""
        device_file = self.db_path.parent / ".device_id"
        
        if device_file.exists():
            try:
                with open(device_file, 'r') as f:
                    return f.read().strip()
            except:
                pass
        
        # 生成新的设备ID
        device_id = str(uuid.uuid4())
        try:
            with open(device_file, 'w') as f:
                f.write(device_id)
        except:
            pass
        
        return device_id
    
    def _ensure_device_info(self, conn: sqlite3.Connection):
        """确保设备信息存在"""
        cursor = conn.execute(
            "SELECT device_id FROM device_info WHERE device_id = ?", 
            (self.device_id,)
        )
        if not cursor.fetchone():
            conn.execute("""
                INSERT OR REPLACE INTO device_info 
                (device_id, device_name, device_type, installation_id)
                VALUES (?, ?, ?, ?)
            """, (self.device_id, "Python Device", "desktop", str(uuid.uuid4())))
    
    def register_event_callback(self, event: str, callback: Callable):
        """注册事件回调"""
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []
        self._event_callbacks[event].append(callback)
    
    def _emit_event(self, event: str, data: Dict[str, Any]):
        """触发事件"""
        if event in self._event_callbacks:
            for callback in self._event_callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"事件回调执行失败 {event}: {e}")
    
    def _record_query_stats(self, query_type: str, execution_time: float):
        """记录查询统计"""
        with self._stats_lock:
            if query_type not in self._query_stats:
                self._query_stats[query_type] = {
                    'count': 0,
                    'total_time': 0.0,
                    'avg_time': 0.0,
                    'max_time': 0.0
                }
            
            stats = self._query_stats[query_type]
            stats['count'] += 1
            stats['total_time'] += execution_time
            stats['avg_time'] = stats['total_time'] / stats['count']
            stats['max_time'] = max(stats['max_time'], execution_time)

class RecordService:
    """记录服务类"""
    
    def __init__(self, db_manager: AdvancedDatabaseManager):
        self.db = db_manager
        self.query_builder = QueryBuilder()
    
    async def create_record_async(self, record: Record) -> str:
        """异步创建记录"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.db.executor, 
            self.create_record, 
            record
        )
    
    def create_record(self, record: Record) -> str:
        """创建记录"""
        start_time = time.time()
        
        try:
            # 设置默认值
            if not record.id:
                record.id = str(uuid.uuid4())
            
            record.device_id = self.db.device_id
            record.hash_value = self._calculate_hash(record)
            record.created_at = datetime.now()
            record.updated_at = datetime.now()
            
            with self.db.pool.get_connection() as conn:
                # 插入记录
                self._insert_record(conn, record)
                conn.commit()
                
                # 触发事件
                self.db._emit_event('record_created', {
                    'record_id': record.id,
                    'account_id': record.account_id,
                    'amount': record.amount,
                    'record_type': record.record_type
                })
                
                logger.info(f"记录创建成功: {record.id}")
                return record.id
                
        except Exception as e:
            logger.error(f"创建记录失败: {e}")
            raise
        finally:
            self.db._record_query_stats('create_record', time.time() - start_time)
    
    def update_record(self, record_id: str, updates: Dict[str, Any]) -> bool:
        """更新记录"""
        start_time = time.time()
        
        try:
            with self.db.pool.get_connection() as conn:
                # 获取当前记录
                current = self._get_record_by_id(conn, record_id)
                if not current:
                    logger.warning(f"记录不存在: {record_id}")
                    return False
                
                # 检查版本冲突
                if current['server_version'] > current['local_version']:
                    self._mark_conflict(conn, record_id, updates)
                    logger.warning(f"记录存在版本冲突: {record_id}")
                    return False
                
                # 准备更新数据
                updated_data = dict(current)
                updated_data.update(updates)
                updated_data.update({
                    'local_version': current['local_version'] + 1,
                    'sync_status': SyncStatus.NOT_SYNCED.value,
                    'updated_at': int(datetime.now().timestamp()),
                    'hash_value': self._calculate_hash_from_dict(updated_data)
                })
                
                # 执行更新
                self._update_record_data(conn, record_id, updated_data)
                conn.commit()
                
                # 触发事件
                self.db._emit_event('record_updated', {
                    'record_id': record_id,
                    'changes': updates,
                    'version': updated_data['local_version']
                })
                
                logger.info(f"记录更新成功: {record_id}")
                return True
                
        except Exception as e:
            logger.error(f"更新记录失败: {e}")
            return False
        finally:
            self.db._record_query_stats('update_record', time.time() - start_time)
    
    def get_records_paginated(self, 
                            account_id: str, 
                            page: int = 1, 
                            page_size: int = 20,
                            filters: Optional[Dict] = None,
                            use_cache: bool = True) -> Dict[str, Any]:
        """分页获取记录"""
        cache_key = f"records_{account_id}_{page}_{page_size}_{hash(str(filters))}"
        
        # 检查缓存
        if use_cache:
            cached_result = self._get_cache(cache_key)
            if cached_result:
                return cached_result
        
        start_time = time.time()
        
        try:
            with self.db.pool.get_connection() as conn:
                # 构建查询
                query = (self.query_builder
                        .reset()
                        .select(
                            "r.*",
                            "c.name as category_name",
                            "c.icon_name as category_icon",
                            "c.color as category_color",
                            "pa.name as payment_account_name",
                            "u.nickname as creator_name"
                        )
                        .from_table("records", "r")
                        .left_join("categories c", "r.category_id = c.id")
                        .left_join("payment_accounts pa", "r.payment_account_id = pa.id")
                        .left_join("users u", "r.creator_id = u.id")
                        .where("r.account_id = ? AND r.is_deleted = 0", account_id))
                
                # 应用过滤器
                if filters:
                    if 'record_type' in filters:
                        query.where("r.record_type = ?", filters['record_type'])
                    
                    if 'date_from' in filters:
                        query.where("r.record_date >= ?", int(filters['date_from'].timestamp()))
                    
                    if 'date_to' in filters:
                        query.where("r.record_date <= ?", int(filters['date_to'].timestamp()))
                    
                    if 'category_id' in filters:
                        query.where("r.category_id = ?", filters['category_id'])
                    
                    if 'min_amount' in filters:
                        query.where("r.amount >= ?", filters['min_amount'])
                    
                    if 'max_amount' in filters:
                        query.where("r.amount <= ?", filters['max_amount'])
                    
                    if 'search' in filters and filters['search']:
                        search_term = f"%{filters['search']}%"
                        query.where("(r.description LIKE ? OR r.location LIKE ?)", 
                                   search_term, search_term)
                
                # 添加排序和分页
                offset = (page - 1) * page_size
                query.order_by("r.record_date", "DESC").order_by("r.created_at", "DESC")
                query.limit(page_size, offset)
                
                sql, params = query.build()
                cursor = conn.execute(sql, params)
                records = []
                
                for row in cursor.fetchall():
                    record_dict = dict(row)
                    # 转换时间戳
                    record_dict['record_date'] = datetime.fromtimestamp(record_dict['record_date'])
                    record_dict['created_at'] = datetime.fromtimestamp(record_dict['created_at'])
                    record_dict['updated_at'] = datetime.fromtimestamp(record_dict['updated_at'])
                    
                    # 解析JSON字段
                    for field in ['tags', 'related_people', 'images']:
                        if record_dict.get(field):
                            try:
                                record_dict[field] = json.loads(record_dict[field])
                            except json.JSONDecodeError:
                                record_dict[field] = []
                    
                    records.append(record_dict)
                
                # 获取总数
                count_query = (QueryBuilder()
                              .select("COUNT(*)")
                              .from_table("records")
                              .where("account_id = ? AND is_deleted = 0", account_id))
                
                # 应用相同的过滤器到计数查询
                if filters:
                    if 'record_type' in filters:
                        count_query.where("record_type = ?", filters['record_type'])
                    # ... 其他过滤器
                
                count_sql, count_params = count_query.build()
                total_count = conn.execute(count_sql, count_params).fetchone()[0]
                
                result = {
                    'records': records,
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total': total_count,
                        'total_pages': (total_count + page_size - 1) // page_size,
                        'has_next': page * page_size < total_count,
                        'has_prev': page > 1
                    },
                    'filters_applied': filters or {},
                    'generated_at': datetime.now().isoformat()
                }
                
                # 缓存结果
                if use_cache:
                    self._set_cache(cache_key, result, ttl=300)  # 5分钟缓存
                
                return result
                
        except Exception as e:
            logger.error(f"获取分页记录失败: {e}")
            return {
                'records': [],
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': 0,
                    'total_pages': 0,
                    'has_next': False,
                    'has_prev': False
                },
                'error': str(e)
            }
        finally:
            self.db._record_query_stats('get_records_paginated', time.time() - start_time)
    
    def get_advanced_analytics(self, account_id: str, 
                             date_range: Optional[Tuple[datetime, datetime]] = None,
                             use_cache: bool = True) -> Dict[str, Any]:
        """获取高级分析数据"""
        cache_key = f"analytics_{account_id}_{hash(str(date_range))}"
        
        if use_cache:
            cached_result = self._get_cache(cache_key)
            if cached_result:
                return cached_result
        
        start_time = time.time()
        
        try:
            with self.db.pool.get_connection() as conn:
                # 构建时间条件
                time_condition = ""
                time_params = [account_id]
                
                if date_range:
                    time_condition = " AND r.record_date BETWEEN ? AND ?"
                    time_params.extend([
                        int(date_range[0].timestamp()),
                        int(date_range[1].timestamp())
                    ])
                
                # 1. 基础统计
                basic_stats_sql = f"""
                    SELECT 
                        SUM(CASE WHEN record_type = 'income' THEN amount ELSE 0 END) as total_income,
                        SUM(CASE WHEN record_type = 'expense' THEN amount ELSE 0 END) as total_expense,
                        COUNT(CASE WHEN record_type = 'income' THEN 1 END) as income_count,
                        COUNT(CASE WHEN record_type = 'expense' THEN 1 END) as expense_count,
                        COUNT(*) as total_records,
                        AVG(CASE WHEN record_type = 'expense' THEN amount END) as avg_expense,
                        MAX(CASE WHEN record_type = 'expense' THEN amount END) as max_expense,
                        MIN(CASE WHEN record_type = 'expense' THEN amount END) as min_expense
                    FROM records r
                    WHERE r.account_id = ? AND r.is_deleted = 0 {time_condition}
                """
                
                basic_stats = conn.execute(basic_stats_sql, time_params).fetchone()
                
                # 2. 分类统计（支出）
                category_stats_sql = f"""
                    SELECT 
                        COALESCE(c.name, '未分类') as category_name,
                        c.icon_name,
                        c.color,
                        SUM(r.amount) as total_amount,
                        COUNT(*) as record_count,
                        AVG(r.amount) as avg_amount,
                        ROUND(SUM(r.amount) * 100.0 / (
                            SELECT SUM(amount) FROM records 
                            WHERE account_id = ? AND record_type = 'expense' AND is_deleted = 0 {time_condition}
                        ), 2) as percentage
                    FROM records r
                    LEFT JOIN categories c ON r.category_id = c.id
                    WHERE r.account_id = ? 
                        AND r.record_type = 'expense' 
                        AND r.is_deleted = 0 {time_condition}
                    GROUP BY c.id, c.name, c.icon_name, c.color
                    ORDER BY total_amount DESC
                """
                
                category_params = time_params + time_params
                category_stats = conn.execute(category_stats_sql, category_params).fetchall()
                
                # 3. 月度趋势
                monthly_trend_sql = f"""
                    SELECT 
                        strftime('%Y-%m', datetime(record_date, 'unixepoch')) as month,
                        SUM(CASE WHEN record_type = 'income' THEN amount ELSE 0 END) as monthly_income,
                        SUM(CASE WHEN record_type = 'expense' THEN amount ELSE 0 END) as monthly_expense,
                        COUNT(*) as monthly_records
                    FROM records r
                    WHERE r.account_id = ? AND r.is_deleted = 0 {time_condition}
                    GROUP BY strftime('%Y-%m', datetime(record_date, 'unixepoch'))
                    ORDER BY month DESC
                    LIMIT 12
                """
                
                monthly_trend = conn.execute(monthly_trend_sql, time_params).fetchall()
                
                # 4. 支付账户分布
                account_distribution_sql = f"""
                    SELECT 
                        pa.name as account_name,
                        pa.account_type,
                        pa.icon_name,
                        SUM(r.amount) as total_amount,
                        COUNT(*) as transaction_count,
                        ROUND(AVG(r.amount), 2) as avg_transaction
                    FROM records r
                    LEFT JOIN payment_accounts pa ON r.payment_account_id = pa.id
                    WHERE r.account_id = ? AND r.is_deleted = 0 {time_condition}
                    GROUP BY pa.id, pa.name, pa.account_type, pa.icon_name
                    ORDER BY total_amount DESC
                """
                
                account_distribution = conn.execute(account_distribution_sql, time_params).fetchall()
                
                # 5. 时间模式分析
                time_pattern_sql = f"""
                    SELECT 
                        CASE 
                            WHEN cast(strftime('%H', datetime(record_date, 'unixepoch')) as integer) BETWEEN 6 AND 11 THEN '上午'
                            WHEN cast(strftime('%H', datetime(record_date, 'unixepoch')) as integer) BETWEEN 12 AND 17 THEN '下午'
                            WHEN cast(