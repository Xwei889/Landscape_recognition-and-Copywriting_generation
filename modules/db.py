# -*- coding: utf-8 -*-
"""
MySQL 数据库模块
- 启动时自动建库、建表
- 提供通用的查询 / 单条查询 / 执行(增删改) / 插入并返回自增ID 方法
"""
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
import config


# ---------------- 连接 ----------------
def _connect(use_db=True):
    return pymysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DB if use_db else None,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


# ---------------- 建库 / 建表 ----------------
_CREATE_DB = (
    f"CREATE DATABASE IF NOT EXISTS {config.MYSQL_DB} "
    "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
)

_TABLES = {
    # 用户表
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'user',
            nickname VARCHAR(50),
            avatar VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # 生成记录表
    "records": """
        CREATE TABLE IF NOT EXISTS records (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT,
            img_path VARCHAR(255),
            scene VARCHAR(50),
            style VARCHAR(100),
            caption TEXT,
            is_public TINYINT DEFAULT 0,
            is_edited TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_scene (scene),
            INDEX idx_public (is_public),
            CONSTRAINT fk_records_user FOREIGN KEY (user_id)
                REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # 收藏表
    "favorites": """
        CREATE TABLE IF NOT EXISTS favorites (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            record_id INT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fav (user_id, record_id),
            CONSTRAINT fk_fav_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT fk_fav_record FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # 点赞表（广场）
    "likes": """
        CREATE TABLE IF NOT EXISTS likes (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            record_id INT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_like (user_id, record_id),
            CONSTRAINT fk_like_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT fk_like_record FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # 评分表
    "ratings": """
        CREATE TABLE IF NOT EXISTS ratings (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            record_id INT NOT NULL,
            score INT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_rating (user_id, record_id),
            CONSTRAINT fk_rate_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT fk_rate_record FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # 纠错表
    "corrections": """
        CREATE TABLE IF NOT EXISTS corrections (
            id INT PRIMARY KEY AUTO_INCREMENT,
            record_id INT,
            user_id INT,
            wrong_scene VARCHAR(50),
            correct_scene VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_correct (correct_scene),
            CONSTRAINT fk_corr_record FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE,
            CONSTRAINT fk_corr_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # 操作日志表
    "operation_logs": """
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT,
            action VARCHAR(50),
            detail VARCHAR(500),
            ip VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_oplog_user (user_id),
            CONSTRAINT fk_oplog_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # 登录日志表
    "login_logs": """
        CREATE TABLE IF NOT EXISTS login_logs (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT,
            username VARCHAR(50),
            ip VARCHAR(50),
            success TINYINT DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_loginlog_user (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # 评论表
    "comments": """
        CREATE TABLE IF NOT EXISTS comments (
            id INT PRIMARY KEY AUTO_INCREMENT,
            record_id INT NOT NULL,
            user_id INT,
            content VARCHAR(500) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_comment_record (record_id),
            CONSTRAINT fk_comment_record FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE,
            CONSTRAINT fk_comment_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # 关注表：follower 关注 followee
    "follows": """
        CREATE TABLE IF NOT EXISTS follows (
            id INT PRIMARY KEY AUTO_INCREMENT,
            follower_id INT NOT NULL,
            followee_id INT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_follow (follower_id, followee_id),
            CONSTRAINT fk_follow_follower FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT fk_follow_followee FOREIGN KEY (followee_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
}


def init_db():
    """建库 + 建全部表，启动时调用一次。"""
    # 1. 建库（此时不指定 database）
    conn = _connect(use_db=False)
    try:
        with conn.cursor() as cur:
            cur.execute(_CREATE_DB)
        conn.commit()
    finally:
        conn.close()

    # 2. 建表
    conn = _connect(use_db=True)
    try:
        with conn.cursor() as cur:
            for name, ddl in _TABLES.items():
                cur.execute(ddl)
        conn.commit()
        print(f"[db] 数据库 {config.MYSQL_DB} 就绪，共 {len(_TABLES)} 张表")
    finally:
        conn.close()


# ---------------- 通用方法 ----------------
def query(sql, args=None):
    """查询，返回字典列表。"""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    finally:
        conn.close()


def query_one(sql, args=None):
    """查询单条，返回字典或 None。"""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchone()
    finally:
        conn.close()


def execute(sql, args=None):
    """增删改，返回受影响行数。"""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            rows = cur.execute(sql, args)
        conn.commit()
        return rows
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_get_id(sql, args=None):
    """插入并返回自增主键 ID。"""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            new_id = cur.lastrowid
        conn.commit()
        return new_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
