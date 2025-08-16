#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日简报自动发布到 Emlog
功能：每天早上9点自动获取ALAPI每日简报并发布到Emlog博客
作者：AI助手
日期：2025-08-03
"""

import datetime
import requests
import json
import base64
from io import BytesIO
import urllib3
import ssl
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Emlog 配置
DOMAIN      = os.environ.get("EMLOG_DOMAIN") or "https://emlog.xxxxxxxx.com"  # 结尾不要 /
API_KEY     = os.environ.get("EMLOG_API_KEY") or "xxxxxxxxxxxxxxxxxxxxxx"   # Emlog API Key
AUTHOR_UID  = int(os.environ.get("EMLOG_AUTHOR_UID")) or 1 # 作者 UID
SORT_ID     = int(os.environ.get("EMLOG_SORT_ID")) or 2   # 分类 ID

# ALAPI 配置
ALAPI_TOKEN = os.environ.get("ALAPI_TOKEN") or "xxxxxxxxxxxxxxxx"   # ALAPI Token
ALAPI_URL   = "https://v3.alapi.cn/api/zaobao"  # ALAPI 早报接口

# 飞书机器人应用配置
FS_APP_ID = os.environ.get("FEISHU_APP_ID") or "cli_xxxxxxxxxxxxxxx"
FS_APP_SECRET = os.environ.get("FEISHU_APP_SECRET") or "xxxxxxxxxxxxxxxxxxxxxx"
FS_CHAT_ID = os.environ.get("FEISHU_CHAT_ID") or "oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 指定群组ID


TIMEOUT = 20

class SSLAdapter(HTTPAdapter):
    """自定义SSL适配器，用于处理SSL连接问题"""
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

def create_session():
    """创建带有重试和SSL配置的会话"""
    session = requests.Session()
    
    # 配置重试策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    # 挂载SSL适配器
    adapter = SSLAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session

# ---------- 飞书通知函数 ----------
def get_tenant_access_token():
    """获取飞书应用的tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    data = {
        "app_id": FS_APP_ID,
        "app_secret": FS_APP_SECRET
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=TIMEOUT)
        result = response.json()
        if result.get("code") == 0:
            return result["tenant_access_token"]
        else:
            raise RuntimeError(f"获取token失败: {result}")
    except Exception as e:
        raise RuntimeError(f"获取token异常: {e}")

def fs_send_card(title: str, content: str, template: str = "blue"):
    """发送卡片消息到飞书群组"""
    token = get_tenant_access_token()
    
    # 构建卡片内容
    card_elements = [
        {
            "tag": "div",
            "text": {
                "content": content,
                "tag": "lark_md"
            }
        }
    ]
    
    card_content = {
        "config": {
            "wide_screen_mode": True
        },
        "elements": card_elements,
        "header": {
            "title": {
                "content": title,
                "tag": "plain_text"
            },
            "template": template
        }
    }
    
    # 发送消息
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    params = {"receive_id_type": "chat_id"}
    data = {
        "receive_id": FS_CHAT_ID,
        "msg_type": "interactive",
        "content": json.dumps(card_content)
    }
    
    try:
        response = requests.post(url, headers=headers, params=params, json=data, timeout=TIMEOUT)
        result = response.json()
        print("[飞书卡片]", result)
        return result
    except Exception as e:
        print(f"[飞书卡片] 发送失败: {e}")
        raise

def send_feishu_success_notification(title: str, article_id: str):
    """发送发布成功通知到飞书"""
    try:
        today = datetime.datetime.now().strftime("%Y年%m月%d日")
        article_url = f"{DOMAIN}/?post={article_id}"  # 构建实际文章链接
        content = f"""**📰 每日简报发布成功！**

📅 **日期：** {today}
📄 **标题：** {title}
🆔 **文章ID：** {article_id}
🔗 **文章链接：** {article_url}
⏰ **发布时间：** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ 文章已成功发布到Emlog博客，读者可以查看最新的每日简报内容。"""
        
        fs_send_card("🎉 每日简报发布成功", content, "green")
        print("✅ 飞书成功通知已发送")
    except Exception as e:
        print(f"⚠️ 飞书成功通知发送失败: {e}")

def send_feishu_error_notification(error_msg: str, error_type: str = "发布失败"):
    """发送错误通知到飞书"""
    try:
        today = datetime.datetime.now().strftime("%Y年%m月%d日")
        content = f"""**❌ 每日简报{error_type}！**

📅 **日期：** {today}
🚨 **错误类型：** {error_type}
📝 **错误详情：** {error_msg}
⏰ **发生时间：** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔧 请检查相关配置和网络连接，确保服务正常运行。"""
        
        fs_send_card("🚨 每日简报异常通知", content, "red")
        print("✅ 飞书错误通知已发送")
    except Exception as e:
        print(f"⚠️ 飞书错误通知发送失败: {e}")

# ---------- 原有函数 ----------
def get_zaobao_data():
    """获取每日简报数据"""
    try:
        # 调用 ALAPI 早报接口
        params = {
            "token": ALAPI_TOKEN,
            "format": "json"  # 使用 json 格式获取文本数据
        }
        
        session = create_session()
        response = session.get(ALAPI_URL, params=params, timeout=30, verify=False)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("code") != 200:
            raise Exception(f"API 调用失败: {data.get('msg', '未知错误')}")
        
        return data.get("data", {})
        
    except Exception as e:
        print(f"获取早报数据失败: {e}")
        raise

def get_zaobao_image():
    """获取每日简报图片"""
    try:
        # 调用 ALAPI 早报接口获取图片
        params = {
            "token": ALAPI_TOKEN,
            "format": "image"  # 获取图片格式
        }
        
        session = create_session()
        response = session.get(ALAPI_URL, params=params, timeout=30, verify=False)
        response.raise_for_status()
        
        # 返回图片的二进制数据
        return response.content
        
    except Exception as e:
        print(f"获取早报图片失败: {e}")
        return None

def create_article_content(zaobao_data):
    """创建文章内容"""
    today = datetime.datetime.now().strftime("%Y年%m月%d日")
    
    # 获取新闻列表
    news_list = zaobao_data.get("news", [])
    weiyu = zaobao_data.get("weiyu", "")
    
    # 构建新闻列表HTML
    news_html = ""
    for i, news in enumerate(news_list, 1):
        news_html += f"<li style='margin-bottom:8px;line-height:1.6;'>{i}. {news}</li>\n"
    
    # 获取图片并转换为base64（可选）
    image_html = ""
    try:
        image_data = get_zaobao_image()
        if image_data:
            # 可以选择上传图片到图床或直接使用ALAPI的图片链接
            image_url = f"https://v3.alapi.cn/api/zaobao?token={ALAPI_TOKEN}&format=image"
            image_html = f"""
    <div style="text-align:center;margin:20px 0;">
        <img src="{image_url}" alt="每日简报" 
             style="max-width:100%;height:auto;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.15);">
    </div>
    """
    except:
        pass
    
    # 构造完整内容
    content = f"""
<div style="font-size:16px;line-height:1.8;color:#333;">
    <div style="text-align:center;margin-bottom:30px;">
        <h2 style="color:#0066cc;margin:0;font-size:24px;">📰 每日简报</h2>
        <p style="color:#666;margin:10px 0 0;font-size:14px;">{today} · 60秒读懂世界</p>
    </div>
    
    {image_html}
    
    <div style="background:#f8f9fa;padding:20px;border-radius:8px;margin:20px 0;">
        <h3 style="color:#333;margin:0 0 15px;font-size:18px;">🌍 今日要闻</h3>
        <ol style="margin:0;padding-left:20px;">
            {news_html}
        </ol>
    </div>
    
    <div style="background:#e8f4fd;padding:15px;border-radius:8px;border-left:4px solid #0066cc;">
        <h4 style="color:#0066cc;margin:0 0 10px;font-size:16px;">💭 微语</h4>
        <p style="margin:0;font-style:italic;color:#555;">{weiyu}</p>
    </div>
    
    <div style="text-align:center;margin-top:30px;padding-top:20px;border-top:1px solid #eee;">
        <p style="color:#999;font-size:12px;margin:0;">
            数据来源：ALAPI · 每日简报接口<br>
            自动发布时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</div>
"""
    
    return content

def publish_to_emlog(title, content):
    """发布文章到 Emlog"""
    try:
        payload = {
            "api_key": API_KEY,
            "title": title,
            "content": content,
            "author_uid": AUTHOR_UID,
            "sort_id": SORT_ID,
            "draft": "n",
            "auto_cover": "y"
        }
        
        session = create_session()
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Connection': 'close'  # 强制关闭连接，避免连接复用问题
        }
        
        response = session.post(
            f"{DOMAIN}/?rest-api=article_post", 
            data=payload, 
            headers=headers,
            timeout=30,
            verify=False
        )
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("code") != 0:
            raise Exception(f"发布失败: {result.get('msg', '未知错误')}")
        
        article_id = result.get("data", {}).get("article_id")
        print(f"✅ 文章发布成功！文章ID: {article_id}")
        return article_id
        
    except Exception as e:
        print(f"❌ 发布文章失败: {e}")
        raise

def main():
    """主函数"""
    try:
        print("🚀 开始获取每日简报...")
        
        # 获取早报数据
        zaobao_data = get_zaobao_data()
        
        # 生成文章标题
        today = datetime.datetime.now().strftime("%Y年%m月%d日")
        title = f"每日简报 {today} - 60秒读懂世界"
        
        # 创建文章内容
        content = create_article_content(zaobao_data)
        
        # 发布到 Emlog
        print("📝 正在发布文章...")
        article_id = publish_to_emlog(title, content)
        
        # 发送成功通知到飞书
        send_feishu_success_notification(title, str(article_id))
        
        print(f"🎉 每日简报发布完成！")
        print(f"📄 文章标题: {title}")
        print(f"🔗 文章ID: {article_id}")
        
    except Exception as e:
        error_msg = str(e)
        print(f"💥 脚本执行失败: {error_msg}")
        
        # 发送错误通知到飞书
        if "获取早报数据失败" in error_msg:
            send_feishu_error_notification(error_msg, "数据获取失败")
        elif "发布文章失败" in error_msg:
            send_feishu_error_notification(error_msg, "文章发布失败")
        else:
            send_feishu_error_notification(error_msg, "脚本执行失败")
        
        raise

if __name__ == "__main__":

    main()
