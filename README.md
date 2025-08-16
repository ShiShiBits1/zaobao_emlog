# 每日简报自动发布到 Emlog

## 项目简介
本项目用于每天早上9点自动获取 ALAPI 每日简报，并通过 Emlog 博客 API 自动发布为新文章，同时支持飞书群组通知。

## 功能说明
- 自动获取 ALAPI 早报数据（文本与图片）
- 自动生成精美 HTML 文章内容
- 一键发布到 Emlog 博客系统
- 发布成功/失败自动推送飞书群组卡片通知

## 使用方法
1. 配置环境变量（EMLOG_DOMAIN、EMLOG_API_KEY、ALAPI_TOKEN、FEISHU_APP_ID、FEISHU_APP_SECRET、FEISHU_CHAT_ID等）
2. 安装依赖：`pip install requests urllib3`
3. 运行脚本：`python zaobao_emlog.py`

## 依赖模块
- requests
- urllib3

## 目录结构
- zaobao_emlog.py  主程序

## License
MIT