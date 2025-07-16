# 仿言分身 (Echo Avatar)

<!-- 在这里替换为你的头图 -->
<div align="center">

![Echo Avatar Logo](https://raw.githubusercontent.com/oyxning/oyxning/refs/heads/main/echoavatarlogo.png)

</div>


**仿言分身 (Echo Avatar)** 是一个为 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 设计的独特插件，它能够学习并模仿指定用户的语言风格，并利用强大的大型语言模型（LLM）生成具有该用户特色的 Prompt。

本插件由全局管理员完全控制，确保了使用的私密性和安全性。

## ✨ 功能特性

- **用户风格学习**: 自动、静默地记录由管理员指定用户的聊天记录，建立语言风格数据库。
- **管理员专属**: 所有功能仅对 AstrBot 的全局管理员开放，保证了插件的安全可控。
- **智能 Prompt 生成**:
    - **测试生成**: 快速选取少量数据，测试生成一个模仿用户风格的 Prompt，方便管理员预览效果。
    - **正式生成**: 调用全局 LLM，对目标用户的全部聊天数据进行深度分析，生成一个高度相似且专业的 Prompt。
- **数据统计**: 管理员可以随时查询已记录的聊天数据条数，了解插件运行状态。
- **简单配置**: 通过 AstrBot 的 WebUI 插件管理界面，轻松配置需要监控的用户列表。

## 🛠️ 安装方式

本插件已在 AstrBot 官方插件市场发布。

您只需进入 AstrBot 的 WebUI，在 **“插件”** -> **“插件市场”** 中搜索 **“Echo Avatar”** 或 **“仿言分身”**，点击安装即可，所有依赖将自动处理。

## 📝 使用指南

所有指令仅供全局管理员使用。

1.  **配置插件**:
    -   进入 AstrBot WebUI 的 **“插件”** 页面。
    -   找到 “仿言分身 (Echo Avatar)” 插件，点击 **“配置”**。
    -   在 `target_users` 字段中，输入您想要监控的用户的 ID（例如 QQ 号），多个用户请使用英文逗号分隔。
    -   保存配置并重载插件。

2.  **查询数据**:
    -   向机器人发送以下指令，可以查看当前数据库中记录了多少条消息：
        ```
        /echo_avatar 数据条数
        ```

3.  **测试生成 Prompt**:
    -   向机器人发送以下指令，插件会随机抽取部分记录，快速生成一个测试性的 Prompt：
        ```
        /echo_avatar 测试生成 <用户ID>
        ```
        例如： `/echo_avatar 测试生成 12345678`

4.  **正式生成 Prompt**:
    -   当收集到足够的数据后，使用以下指令来生成一个完整的、高质量的 Prompt：
        ```
        /echo_avatar 生成 <用户ID>
        ```
        例如： `/echo_avatar 生成 12345678`

## ⚠️ 注意事项

-   本插件会将指定用户的聊天记录以纯文本形式存储在本地数据库文件 `data/astrtbot_plugin_echo_avatar/chat_history.db` 中。请确保 AstrBot 运行环境的磁盘安全。
-   生成 Prompt 的质量高度依赖于所记录的聊天数据量和多样性。数据越丰富，模仿得越像。
-   请在遵守相关法律法规和平台用户协议的前提下使用本插件，尊重用户隐私。

## 🧑‍💻 作者

-   **LumineStory**

## 🔗 仓库地址

[github.com/oyxning/astrtbot_plugin_echo_avatar](https://github.com/oyxning/astrtbot_plugin_echo_avatar)

## 💡 另：插件反馈群

由于作者持续的那么一个懒，平常不会及时的看issues，所以开了个QQ反馈群方便用户及时的拷打作者。
* 群号：928985352       
* 进群密码：神人desuwa


