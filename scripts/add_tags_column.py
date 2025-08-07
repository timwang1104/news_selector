#!/usr/bin/env python3
"""
数据库迁移脚本：为Article表添加tags字段

这个脚本会为现有的Article表添加tags字段，用于存储AI生成的细分标签。
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import setup_database
from config.settings import DB_URL

def add_tags_column():
    """
    为Article表添加tags字段
    """
    print(f"连接到数据库: {DB_URL}")
    engine = create_engine(DB_URL)
    
    try:
        with engine.connect() as connection:
            # 检查tags字段是否已存在
            try:
                result = connection.execute(text("SELECT tags FROM articles LIMIT 1"))
                print("tags字段已存在，无需添加")
                return
            except OperationalError:
                # 字段不存在，需要添加
                print("tags字段不存在，正在添加...")
                pass
            
            # 添加tags字段
            connection.execute(text("ALTER TABLE articles ADD COLUMN tags TEXT"))
            connection.commit()
            print("成功添加tags字段到articles表")
            
    except Exception as e:
        print(f"添加tags字段时发生错误: {e}")
        raise
    finally:
        engine.dispose()

if __name__ == '__main__':
    add_tags_column()
    print("数据库迁移完成")