# -*- coding: utf-8 -*-

import asyncio
import os
import sqlite3
import random
from pathlib import Path

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
    "description": "学习指定用户的说话方式并生成专业的Prompt，仅限全局管理员使用。",
    "version": "0.2.0", 
    "repo": "https://github.com/oyxning/astrtbot_plugin_echo_avatar",
}

# 数据目录路径
DATA_ROOT = Path("data/astrtbot_plugin_echo_avatar")
USER_DATA_DIR = DATA_ROOT / "user_data"

def init_plugin_data_dir():
    """初始化插件所需的数据目录"""
    try:
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"[{PLUGIN_METADATA['name']}] 用户数据目录初始化成功: {USER_DATA_DIR}")
    except Exception as e:
        logger.error(f"[{PLUGIN_METADATA['name']}] 创建数据目录失败: {e}")

def get_user_db_path(user_id: str) -> Path:
    """获取指定用户的数据库文件路径"""
    return USER_DATA_DIR / f"{user_id}.db"

def create_user_table_if_not_exists(db_path: Path):
    """如果表不存在，则在指定用户的数据库中创建表"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"[{PLUGIN_METADATA['name']}] 在 {db_path} 中创建表失败: {e}")


@register(
    PLUGIN_METADATA["name"],
    PLUGIN_METADATA["author"],
    PLUGIN_METADATA["description"],
    PLUGIN_METADATA["version"],
    PLUGIN_METADATA["repo"],
)
class EchoAvatarPlugin(Star):
    """
    仿言分身插件主类
    """

    def __init__(self, context: Context, config: AstrBotConfig):
        """插件初始化"""
        super().__init__(context)
        self.config = config
        self.target_users = self.config.get("target_users", [])
        
        # 初始化数据目录
        init_plugin_data_dir()

        logger.info(f"[{PLUGIN_METADATA['name']}] 插件已加载。")
        logger.info(f"[{PLUGIN_METADATA['name']}] 当前监控的用户: {self.target_users}")

    @filter.event_message_type(filter.EventMessageType.ALL, priority=100)
    async def message_recorder(self, event: AstrMessageEvent):
        """监听并记录目标用户的消息到独立文件中"""
        sender_id = event.get_sender_id()
        self.target_users = self.config.get("target_users", [])

        if sender_id in self.target_users:
            message_text = event.message_str
            if not message_text:
                return

            db_path = get_user_db_path(sender_id)
            # 确保表存在
            create_user_table_if_not_exists(db_path)

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

    @filter.permission_type(filter.PermissionType.ADMIN)
    @echo_avatar_group.command("状态")
    async def get_status(self, event: AstrMessageEvent):
        """查询当前插件的监控状态"""
        self.target_users = self.config.get("target_users", [])
        if not self.target_users:
            yield event.plain_result(f"[{PLUGIN_METADATA['name']}]\n当前未配置任何监控用户。")
        else:
            user_list_str = "\n- ".join(self.target_users)
            yield event.plain_result(f"[{PLUGIN_METADATA['name']}]\n当前正在监控以下用户：\n- {user_list_str}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @echo_avatar_group.command("数据条数")
    async def get_data_count(self, event: AstrMessageEvent, user_id: str):
        """查询指定用户已记录的消息总数"""
        if not user_id:
            yield event.plain_result("指令格式错误，请提供用户ID。例如：/echo_avatar 数据条数 123456")
            return

        db_path = get_user_db_path(user_id)
        if not db_path.exists():
            yield event.plain_result(f"未找到用户 {user_id} 的数据记录。")
            return
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM chat_history")
            count = cursor.fetchone()[0]
            conn.close()
            yield event.plain_result(f"[{PLUGIN_METADATA['name']}]\n用户 {user_id} 已记录 {count} 条消息。")
        except Exception as e:
            logger.error(f"[{PLUGIN_METADATA['name']}] 查询用户 {user_id} 数据条数失败: {e}")
            yield event.plain_result(f"查询失败: {e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @echo_avatar_group.command("清理数据")
    async def clear_user_data(self, event: AstrMessageEvent, user_id: str):
        """一键清理选定用户的所有数据"""
        if not user_id:
            yield event.plain_result("指令格式错误，请提供用户ID。例如：/echo_avatar 清理数据 123456")
            return
        
        db_path = get_user_db_path(user_id)
        if not db_path.exists():
            yield event.plain_result(f"未找到用户 {user_id} 的数据记录，无需清理。")
            return
            
        try:
            db_path.unlink()
            logger.info(f"[{PLUGIN_METADATA['name']}] 已成功删除用户 {user_id} 的数据文件: {db_path}")
            yield event.plain_result(f"[{PLUGIN_METADATA['name']}]\n已成功清理用户 {user_id} 的所有聊天数据。")
        except Exception as e:
            logger.error(f"[{PLUGIN_METADATA['name']}] 清理用户 {user_id} 数据失败: {e}")
            yield event.plain_result(f"清理失败: {e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @echo_avatar_group.command("测试生成")
    async def test_generate_prompt(self, event: AstrMessageEvent, user_id: str):
        """使用少量数据测试生成Prompt"""
        if not user_id:
            yield event.plain_result("指令格式错误，请提供用户ID。")
            return

        db_path = get_user_db_path(user_id)
        if not db_path.exists():
            yield event.plain_result(f"数据库中没有找到用户 {user_id} 的聊天记录。")
            return

        yield event.plain_result(f"正在为用户 {user_id} 生成测试性Prompt，请稍候...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT message FROM chat_history")
            messages = [row[0] for row in cursor.fetchall()]
            conn.close()

            if not messages:
                yield event.plain_result(f"用户 {user_id} 的数据文件为空。")
                return

            sample_messages = random.sample(messages, min(len(messages), 20))
            prompt_template = (
                "你是一个语言风格分析专家和创意提示词工程师。\n"
                f"请分析以下来自用户 '{user_id}' 的聊天记录，总结其独特的语言风格、口头禅、语气和常用句式。\n"
                "基于你的分析，请模仿该用户风格，创作一个全新的Prompt。\n"
                "请严格按照以下格式输出，并补充每一项内容：\n"
                "## Profile\n- author: {user_id}\n- version: 1.0\n- language: Chinese\n- description: （简要描述该用户风格）\n\n## Skills\n（补充该用户的表达技能、特点）\n\n## Rules\n（补充该用户的表达规则、习惯）\n\n## Workflows\n（补充该用户常用的表达流程或沟通方式）\n\n## Init\n（补充初始化内容或开场白）\n"
                "--- 聊天记录样本 ---\n"
                "{messages}\n"
            )
            formatted_messages = "\n".join([f"- {msg}" for msg in sample_messages])
            final_prompt = prompt_template.format(messages=formatted_messages, user_id=user_id)

            llm_response = await self.context.get_using_provider().text_chat(prompt=final_prompt)
            if llm_response and llm_response.completion_text:
                yield event.plain_result(f"为用户 {user_id} 生成的测试Prompt：\n\n{llm_response.completion_text}")
            else:
                yield event.plain_result("调用LLM失败或未返回有效内容。")
        except Exception as e:
            logger.error(f"[{PLUGIN_METADATA['name']}] 测试生成失败: {e}")
            yield event.plain_result(f"测试生成失败: {e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @echo_avatar_group.command("生成")
    async def generate_full_prompt(self, event: AstrMessageEvent, user_id: str):
        """使用全部数据生成最终的Prompt"""
        if not user_id:
            yield event.plain_result("指令格式错误，请提供用户ID。")
            return

        db_path = get_user_db_path(user_id)
        if not db_path.exists():
            yield event.plain_result(f"数据库中没有找到用户 {user_id} 的聊天记录。")
            return

        yield event.plain_result(f"正在为用户 {user_id} 生成正式Prompt，数据量较大，可能需要一些时间，请耐心等待...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT message FROM (SELECT message FROM chat_history ORDER BY timestamp DESC LIMIT 1000) ORDER BY RANDOM()")
            messages = [row[0] for row in cursor.fetchall()]
            conn.close()

            if not messages:
                yield event.plain_result(f"用户 {user_id} 的数据文件为空。")
                return
            
            prompt_template = (
                "你是一个顶级的语言风格模仿大师和提示词创作专家。\n"
                f"你的任务是深度分析以下提供的大量来自用户 '{user_id}' 的真实聊天记录。\n"
                "请精确地、细致地总结出该用户的核心语言特征，包括但不限于：口头禅、语气、句式、表情符号、主题偏好等。\n"
                "在完成上述分析后，请完全代入该用户的角色，创作一个高质量的Prompt。\n"
                "请严格按照以下格式输出，并补充每一项内容：\n"
                "## Profile\n- author: {user_id}\n- version: 1.0\n- language: Chinese\n- description: （简要描述该用户风格）\n\n## Skills\n（补充该用户的表达技能、特点）\n\n## Rules\n（补充该用户的表达规则、习惯）\n\n## Workflows\n（补充该用户常用的表达流程或沟通方式）\n\n## Init\n（补充初始化内容或开场白）\n"
                "--- 聊天记录 ---\n"
                "{messages}\n"
            )
            formatted_messages = "\n".join([f'"{msg}"' for msg in messages])
            final_prompt = prompt_template.format(messages=formatted_messages, user_id=user_id)
            yield event.request_llm(prompt=final_prompt)
        except Exception as e:
            logger.error(f"[{PLUGIN_METADATA['name']}] 正式生成失败: {e}")
            yield event.plain_result(f"生成失败: {e}")

    async def terminate(self):
        """插件卸载/停用时调用"""
        logger.info(f"[{PLUGIN_METADATA['name']}] 插件已卸载。")
