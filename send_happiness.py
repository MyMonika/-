# =========================================================
# 脚本作者：小红书 - 今晚记得吃苹果 (小红书号：5889008949)
# 功能描述：微信自动化新年祝福发送工具（基于大模型个性化生成）
# 注意事项： 1. 请确保 group.png 和 person.png 已放置在脚本同级目录，
#           2. 请确保 Qwen2.5-1.5B-Instruct目录下有huggingface的网络权重，其他大模型也可以
#           3. 请确保 TARGETS 字典的信息和关系已经对应，请确保PROMPT已经按照个人信息修改
# =========================================================

import os
import time
import json
import random
import torch
import pyperclip
import pyautogui
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForCausalLM
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys
from pywinauto.mouse import click

# ==============================
# 1. 基础配置
# ==============================
MODEL_PATH = "./Qwen2.5-1.5B-Instruct"
USE_GPU = True
LOG_FILE = "send_log.json"

TARGETS = {
    "群聊名称1": "好友群聊",
    "群聊名称2": "闺蜜群聊",
    "朋友备注": "好友",
    "朋友备注": "儿子",
}

# ==============================
# 2. 模型加载
# ==============================
print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    dtype=torch.float16 if USE_GPU else torch.float32,
    device_map="auto" if USE_GPU else None,
    trust_remote_code=True
)
print("Model loaded.")

# ==============================
# 3. 祝福语生成 (增加后处理逻辑剔除杂质)
# ==============================
def generate_message(role):
    prompt = f"你的名字是xxx（此处输入个人名字），请写一句新年祝福语。对象类型：{role}\n要求：1.真诚自然 2.不超过40字 3.不要解释\n只输出祝福语："
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=60, do_sample=True, temperature=0.8, top_p=0.9)
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # 清理模型可能输出的引导词、标签或解释
    clean_msg = text.replace(prompt, "").strip().split("\n")[0]
    clean_msg = clean_msg.replace("祝福语：", "").replace("祝福语:", "").strip()
    clean_msg = clean_msg.split('#')[0].strip() # 剔除模型胡言乱语的标签
    
    return clean_msg if clean_msg else "新年快乐，万事如意！"

# ==============================
# 4. 微信控制功能
# ==============================
def connect_wechat():
    """连接微信并调整窗口位置"""
    print("正在定位微信窗口...")
    try:
        desktop = Desktop(backend="uia")
        main_win = desktop.window(title_re=".*微信.*", control_type="Window")
        
        if not main_win.exists(timeout=10):
            raise RuntimeError("未找到微信窗口")

        wrapper = main_win.wrapper_object()
        if wrapper.is_minimized():
            wrapper.restore()
        wrapper.set_focus()
        
        # 使用兼容性更好的方式移动窗口
        try:
            wrapper.move_window(x=0, y=0, width=1000, height=700)
        except:
            print("  - 窗口移动受限，保持当前位置")
            
        time.sleep(1) 
        return None, main_win
    except Exception as e:
        print(f"  - 连接出错: {e}")
        return None, None

def force_click_input_box(main_win):
    """强制点击聊天区域激活输入焦点"""
    try:
        rect = main_win.rectangle()
        click_x = rect.left + int(rect.width() * 0.7)
        click_y = rect.top + int(rect.height() * 0.85)
        click(button='left', coords=(click_x, click_y))
        time.sleep(0.5)
    except:
        pass

def search_and_enter_chat(main_win, target_name, role_info):
    """搜索目标并根据图像识别点击进入聊天"""
    main_win.set_focus()
    time.sleep(0.5)

    send_keys("^f")
    time.sleep(0.5)
    send_keys("^a{BACKSPACE}")
    pyperclip.copy(target_name)
    send_keys("^v")
    print(f"  - [搜索] 正在检索: {target_name}")
    
    time.sleep(2.5) 

    # 根据 role_info 自动决定识别图像
    header_img = "group.png" if "群" in role_info else "person.png"
    print(f"  - [识别] 正在匹配标识图: {header_img}")
    
    try:
        location = pyautogui.locateOnScreen(header_img, confidence=0.8)
        if location:
            center = pyautogui.center(location)
            # 根据标识位置偏移到第一条结果
            target_x = center.x + 100
            target_y = center.y + 65
            pyautogui.click(target_x, target_y)
            time.sleep(1.0)
            return True
        else:
            print(f"  - [失败] 未发现 {header_img}，执行盲点备选方案")
            send_keys("{DOWN}{ENTER}")
            return False
    except Exception as e:
        print(f"  - [报错] 图像识别异常: {e}")
        return False

def send_message(main_win, message):
    """粘贴并发送消息"""
    force_click_input_box(main_win)
    pyperclip.copy(message)
    time.sleep(0.2)
    send_keys("^v")
    time.sleep(0.5)
    send_keys("{ENTER}")

# ==============================
# 5. 日志管理与主流程
# ==============================
def load_log():
    """读取发送记录"""
    return json.load(open(LOG_FILE, "r", encoding="utf-8")) if os.path.exists(LOG_FILE) else {}

def save_log(data):
    """保存发送记录"""
    json.dump(data, open(LOG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def main():
    """执行自动化祝福流程"""
    log_data = load_log()
    today = datetime.now().strftime("%Y-%m-%d")

    _, main_win = connect_wechat()
    if not main_win: return

    for name, role in TARGETS.items():
        if log_data.get(name) == today:
            print(f"[{name}] 今日已发送，跳过。"); continue

        try:
            print(f"\n>>> 任务开始: [{name}]")
            msg = generate_message(role)
            print(f"  - 大模型生成内容: {msg}")

            if search_and_enter_chat(main_win, name, role):
                send_message(main_win, msg)
                print(f"  - [{name}] 发送成功")
                log_data[name] = today
                save_log(log_data)
            
            wait = random.uniform(3, 6)
            print(f"等待 {wait:.2f} 秒后处理下一条...")
            time.sleep(wait)

        except Exception as e:
            print(f"  - [{name}] 失败: {e}")

    print("\n任务全部完成。")

if __name__ == "__main__":
    main()