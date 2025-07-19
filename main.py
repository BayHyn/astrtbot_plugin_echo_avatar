# -*- coding: utf-8 -*-

import asyncio
import os
import sqlite3
import random
from pathlib import Path
from datetime import datetime

from astrbot.api import logger, AstrBotConfig
from astrbot.api.event import (
    filter,
    AstrMessageEvent,
)
from astrbot.api.star import Context, Star, register

# 插件元数据
PLUGIN_METADATA = {
    "name": "仿言分身 (Echo Avatar)",
    "author": "LumineStory",
    "description": "学习、构建并模仿指定用户的数字人格，生成专业的Prompt。",
    "version": "1.0.0",
    "repo": "https://github.com/oyxning/astrtbot_plugin_echo_avatar",
}

# --- 数据目录与路径定义 ---
DATA_ROOT = Path("data/astrtbot_plugin_echo_avatar")
USER_DATA_DIR = DATA_ROOT / "user_data"

# --- HTML 模板定义 ---
PREVIEW_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户数据预览</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f8f9fa; color: #212529; margin: 0; padding: 20px; }
        .container { background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 800px; margin: auto; padding: 30px; }
        h1, h2 { color: #007bff; border-bottom: 2px solid #dee2e6; padding-bottom: 10px; }
        h1 { font-size: 28px; text-align: center; }
        h2 { font-size: 22px; margin-top: 30px; }
        .profile-item { font-size: 18px; margin-bottom: 10px; }
        .profile-item strong { color: #495057; }
        ul { list-style-type: none; padding-left: 0; }
        li { background-color: #e9ecef; border-radius: 5px; padding: 12px; margin-bottom: 8px; font-size: 16px; line-height: 1.5; word-wrap: break-word; }
        .annotation { border-left: 4px solid #dc3545; }
        .memory { border-left: 4px solid #6c757d; }
        .chat { border-left: 4px solid #28a745; }
        .annotation-author, .memory-author { font-size: 12px; color: #6c757d; display: block; text-align: right; margin-top: 5px; }
        .empty { color: #6c757d; font-style: italic; }
        .footer { text-align: center; margin-top: 40px; font-size: 14px; color: #6c757d; }
    </style>
</head>
<body>
    <div class="container">
        <h1>仿言分身 - 数据预览</h1>
        
        <h2>👤 用户资料</h2>
        <div class="profile-item"><strong>ID:</strong> {{ user_id }}</div>
        <div class="profile-item"><strong>昵称:</strong> {{ nickname }}</div>

        <h2>📌 管理员批注 (最高权重)</h2>
        {% if admin_annotations %}
            <ul>
                {% for item in admin_annotations %}
                    <li class="annotation">
                        {{ item.text }}
                        <span class="annotation-author">by: {{ item.author }} at {{ item.time }}</span>
                    </li>
                {% endfor %}
            </ul>
        {% else %}
            <p class="empty">暂无管理员批注。</p>
        {% endif %}

        <h2>🧠 第三方记忆 (辅助参考)</h2>
        {% if third_party_memories %}
            <ul>
                {% for item in third_party_memories %}
                    <li class="memory">
                        {{ item.text }}
                        <span class="memory-author">by: {{ item.author }} at {{ item.time }}</span>
                    </li>
                {% endfor %}
            </ul>
        {% else %}
            <p class="empty">暂无第三方记忆。</p>
        {% endif %}

        <h2>💬 最新聊天记录 (样本)</h2>
        {% if chat_history %}
            <ul>
                {% for item in chat_history %}
                    <li class="chat">{{ item.message }}</li>
                {% endfor %}
            </ul>
        {% else %}
            <p class="empty">暂无聊天记录。</p>
        {% endif %}

        <div class="footer">
            由 Echo Avatar 插件生成
        </div>
    </div>
</body>
</html>
"""

# --- 数据库辅助函数 ---
def init_user_db(db_path: Path):
    """初始化用户的数据库，创建所有需要的表"""
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 聊天记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )""")
        
        # 用户资料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                key TEXT PRIMARY KEY,
                value TEXT
            )""")

        # 管理员批注表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                added_by TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )""")
        
        # 第三方记忆表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS third_party_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                added_by TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )""")
            
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"[{PLUGIN_METADATA['name']}] 初始化数据库 {db_path} 失败: {e}")

def get_user_db_path(user_id: str) -> Path:
    """获取指定用户的数据库文件路径"""
    return USER_DATA_DIR / f"{user_id}.db"

# --- 插件主类 ---
@register(
    PLUGIN_METADATA["name"],
    PLUGIN_METADATA["author"],
    PLUGIN_METADATA["description"],
    PLUGIN_METADATA["version"],
    PLUGIN_METADATA["repo"],
)
class EchoAvatarPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.target_users = self.config.get("target_users", [])
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"[{PLUGIN_METADATA['name']}] 插件已加载。当前监控用户: {self.target_users}")

    @filter.event_message_type(filter.EventMessageType.ALL, priority=100)
    async def message_recorder(self, event: AstrMessageEvent):
        sender_id = event.get_sender_id()
        self.target_users = self.config.get("target_users", [])

        if sender_id in self.target_users:
            message_text = event.message_str
            if not message_text: return

            db_path = get_user_db_path(sender_id)
            if not db_path.exists():
                init_user_db(db_path)

            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO chat_history (user_id, message, timestamp) VALUES (?, ?, ?)",
                    (sender_id, message_text, int(event.message_obj.timestamp)),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"[{PLUGIN_METADATA['name']}] 记录消息到 {db_path} 失败: {e}")

    @filter.command_group("echo_avatar", alias={"仿言分身"})
    def echo_avatar_group(self):
        """仿言分身指令组"""
        pass

    # --- 管理员指令 ---
    @filter.permission_type(filter.PermissionType.ADMIN)
    @echo_avatar_group.command("状态")
    async def get_status(self, event: AstrMessageEvent):
        """查询当前插件的监控状态"""
        self.target_users = self.config.get("target_users", [])
        user_list_str = "\n- ".join(self.target_users) if self.target_users else "无"
        yield event.plain_result(f"[{PLUGIN_METADATA['name']}]\n当前正在监控以下用户：\n- {user_list_str}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @echo_avatar_group.command("完善资料")
    async def update_profile(self, event: AstrMessageEvent, user_id: str, key: str, *, value: str):
        """完善指定ID的资料。用法: /echo_avatar 完善资料 <ID> 昵称 <昵称内容>"""
        if key.lower() != '昵称':
            yield event.plain_result("目前只支持完善“昵称”字段。")
            return
        
        db_path = get_user_db_path(user_id)
        init_user_db(db_path)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO profile (key, value) VALUES (?, ?)", ('nickname', value))
            conn.commit()
            conn.close()
            yield event.plain_result(f"已将用户 {user_id} 的昵称更新为: {value}")
        except Exception as e:
            logger.error(f"[{PLUGIN_METADATA['name']}] 更新资料失败: {e}")
            yield event.plain_result(f"更新资料失败: {e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @echo_avatar_group.command("添加批注")
    async def add_admin_annotation(self, event: AstrMessageEvent, user_id: str, *, text: str):
        """为指定ID添加一条管理员批注。"""
        db_path = get_user_db_path(user_id)
        init_user_db(db_path)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO admin_annotations (text, added_by, timestamp) VALUES (?, ?, ?)",
                           (text, event.get_sender_id(), int(datetime.now().timestamp())))
            conn.commit()
            conn.close()
            yield event.plain_result(f"已为用户 {user_id} 添加一条管理员批注。")
        except Exception as e:
            logger.error(f"[{PLUGIN_METADATA['name']}] 添加批注失败: {e}")
            yield event.plain_result(f"添加批注失败: {e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @echo_avatar_group.command("数据预览")
    async def preview_data(self, event: AstrMessageEvent, user_id: str):
        """以图片形式预览指定ID的所有数据。"""
        db_path = get_user_db_path(user_id)
        if not db_path.exists():
            yield event.plain_result(f"未找到用户 {user_id} 的数据记录。")
            return

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 获取资料
            cursor.execute("SELECT value FROM profile WHERE key = 'nickname'")
            nickname_row = cursor.fetchone()
            nickname = nickname_row['value'] if nickname_row else "未设置"

            # 获取批注
            cursor.execute("SELECT text, added_by, timestamp FROM admin_annotations ORDER BY timestamp DESC")
            annotations = [{"text": row['text'], "author": row['added_by'], "time": datetime.fromtimestamp(row['timestamp']).strftime('%Y-%m-%d %H:%M')} for row in cursor.fetchall()]

            # 获取记忆
            cursor.execute("SELECT text, added_by, timestamp FROM third_party_memories ORDER BY timestamp DESC")
            memories = [{"text": row['text'], "author": row['added_by'], "time": datetime.fromtimestamp(row['timestamp']).strftime('%Y-%m-%d %H:%M')} for row in cursor.fetchall()]

            # 获取聊天记录
            cursor.execute("SELECT message FROM chat_history ORDER BY timestamp DESC LIMIT 10")
            history = [{"message": row['message']} for row in cursor.fetchall()]
            
            conn.close()

            render_data = {
                "user_id": user_id,
                "nickname": nickname,
                "admin_annotations": annotations,
                "third_party_memories": memories,
                "chat_history": history
            }

            image_url = await self.html_render(PREVIEW_HTML_TEMPLATE, render_data)
            yield event.image_result(image_url)

        except Exception as e:
            logger.error(f"[{PLUGIN_METADATA['name']}] 数据预览失败: {e}")
            yield event.plain_result(f"数据预览失败: {e}")

    # --- 开放指令 ---
    @echo_avatar_group.command("添加记忆")
    async def add_third_party_memory(self, event: AstrMessageEvent, user_id: str, *, text: str):
        """为指定ID添加一条第三方记忆。"""
        db_path = get_user_db_path(user_id)
        init_user_db(db_path)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO third_party_memories (text, added_by, timestamp) VALUES (?, ?, ?)",
                           (text, event.get_sender_id(), int(datetime.now().timestamp())))
            conn.commit()
            conn.close()
            yield event.plain_result(f"感谢你！已为用户 {user_id} 添加一条新的记忆。")
        except Exception as e:
            logger.error(f"[{PLUGIN_METADATA['name']}] 添加记忆失败: {e}")
            yield event.plain_result(f"添加记忆失败: {e}")

    # --- 核心生成指令 ---
    @filter.permission_type(filter.PermissionType.ADMIN)
    @echo_avatar_group.command("生成")
    async def generate_full_prompt(self, event: AstrMessageEvent, user_id: str):
        """使用所有维度的信息生成最终的Prompt"""
        db_path = get_user_db_path(user_id)
        if not db_path.exists():
            yield event.plain_result(f"数据库中没有找到用户 {user_id} 的任何记录。")
            return

        yield event.plain_result(f"正在为用户 {user_id} 生成多维度人格Prompt，请稍候...")
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 1. 获取资料
            cursor.execute("SELECT value FROM profile WHERE key = 'nickname'")
            nickname = (r['value'] for r in cursor.fetchall())
            profile_str = f"昵称: {next(nickname, '未设置')}"

            # 2. 获取管理员批注
            cursor.execute("SELECT text FROM admin_annotations ORDER BY timestamp")
            annotations_str = "\n".join([f"- {r['text']}" for r in cursor.fetchall()]) or "无"

            # 3. 获取第三方记忆
            cursor.execute("SELECT text FROM third_party_memories ORDER BY timestamp")
            memories_str = "\n".join([f"- {r['text']}" for r in cursor.fetchall()]) or "无"

            # 4. 获取聊天记录
            cursor.execute("SELECT message FROM chat_history ORDER BY timestamp DESC LIMIT 200")
            history_str = "\n".join([f'"{r["message"]}"' for r in cursor.fetchall()]) or "无"
            
            conn.close()

            prompt_template = (
                "你是一个顶级的语言风格模仿大师和提示词创作专家。\n"
                "你的任务是深度分析以下提供的关于用户 '{user_id}' 的多维度资料，并模仿其风格创作。\n\n"
                "资料分为四个部分，请按权重顺序理解：\n\n"
                "1. **管理员批注 (最高权重)**: 这是关于用户最准确的、必须遵守的核心设定。\n{admin_annotations}\n\n"
                "2. **用户资料 (高权重)**: 用户的基本信息。\n{profile_info}\n\n"
                "3. **聊天记录 (主要参考)**: 这是用户最真实的语言样本，用于学习其风格、口头禅、语气和表情使用习惯。\n{chat_history}\n\n"
                "4. **第三方记忆 (辅助参考)**: 这是其他人对用户的印象，权重较低，可用于丰富细节，但如果与聊天记录冲突，以聊天记录为准。\n{third_party_memories}\n\n"
                "---\n"
                "**你的任务:**\n"
                "1. **深度分析**: 综合以上所有信息，在脑中形成一个对用户 '{user_id}' 的完整、立体的画像。\n"
                "2. **风格模仿与创作**: 完全代入该用户的角色，创作一个全新的、高质量的、看起来就像是这个用户本人会说出来的Prompt。这个Prompt必须：\n"
                "    - 严格符合【管理员批注】中的设定。\n"
                "    - 体现【用户资料】中的信息。\n"
                "    - 语言风格、语气、用词习惯与【聊天记录】高度一致。\n"
                "    - 可以适当融入【第三方记忆】中的细节来增加趣味性。\n\n"
                "---\n"
                "**请输出最终创作的Prompt (直接输出Prompt文本，不要包含分析过程):**"
            )

            final_prompt = prompt_template.format(
                user_id=user_id,
                admin_annotations=annotations_str,
                profile_info=profile_str,
                chat_history=history_str,
                third_party_memories=memories_str
            )
            
            yield event.request_llm(prompt=final_prompt)

        except Exception as e:
            logger.error(f"[{PLUGIN_METADATA['name']}] 正式生成失败: {e}")
            yield event.plain_result(f"生成失败: {e}")
            
    @filter.permission_type(filter.PermissionType.ADMIN)
    @echo_avatar_group.command("清理数据")
    async def clear_user_data(self, event: AstrMessageEvent, user_id: str):
        """一键清理选定用户的所有数据"""
        db_path = get_user_db_path(user_id)
        if not db_path.exists():
            yield event.plain_result(f"未找到用户 {user_id} 的数据记录，无需清理。")
            return
        try:
            db_path.unlink()
            logger.info(f"[{PLUGIN_METADATA['name']}] 已成功删除用户 {user_id} 的数据文件: {db_path}")
            yield event.plain_result(f"[{PLUGIN_METADATA['name']}]\n已成功清理用户 {user_id} 的所有数据。")
        except Exception as e:
            logger.error(f"[{PLUGIN_METADATA['name']}] 清理用户 {user_id} 数据失败: {e}")
            yield event.plain_result(f"清理失败: {e}")

    async def terminate(self):
        """插件卸载/停用时调用"""
        logger.info(f"[{PLUGIN_METADATA['name']}] 插件已卸载。")
