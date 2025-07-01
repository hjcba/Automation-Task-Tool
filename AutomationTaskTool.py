import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import os
import shutil
import logging
import configparser
from datetime import datetime
from logging import handlers
from tkinter import messagebox

# 设置日志记录
def setup_logging():
    # 创建 RotatingFileHandler，并设置日志文件编码为 utf-8
    handler = handlers.RotatingFileHandler("automation_tool.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
    
    # 设置日志格式和日期格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)  # 将格式设置给处理器
    
    # 添加日志处理器
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.DEBUG)

# 读取配置文件
def read_config():
    config = configparser.ConfigParser()
    config.read('config.ini')  # 配置文件名
    return config

# 清理过期文件
def clean_up_old_files(directory, days_threshold):
    try:
        now = time.time()
        deleted_files = []
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_mod_time = os.path.getmtime(file_path)
                file_age_days = (now - file_mod_time) / (3600 * 24)  # 转换为天数
                
                if file_age_days > days_threshold:
                    os.remove(file_path)
                    deleted_files.append(filename)
        
        if deleted_files:
            logging.info(f"已删除过期文件: {', '.join(deleted_files)}")
            return f"已删除过期文件: {', '.join(deleted_files)}"
        else:
            logging.info(f"没有需要删除的过期文件。")
            return "没有需要删除的过期文件。"
    except Exception as e:
        logging.error(f"清理文件时出错: {e}")
        return f"错误: {e}"

# 备份任务
def backup_directory(source_dir, backup_dir):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{backup_dir}/backup_{timestamp}"
        shutil.copytree(source_dir, backup_path)
        logging.info(f"目录 {source_dir} 已备份到 {backup_path}")
        return f"备份完成: {backup_path}"
    except Exception as e:
        logging.error(f"备份任务失败: {e}")
        return f"备份失败: {e}"

# 更新日志区域
def update_log(log_text, message):
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, message + "\n")
    log_text.config(state=tk.DISABLED)
    log_text.yview(tk.END)  # 自动滚动到最新日志

# 启动任务的线程
def start_task(log_text, config, pause_event, stop_event):
    def task_thread():
        target_directory = config['TASKS']['Directory']
        expiration_days = int(config['TASKS']['ExpirationDays'])
        backup_source = config['TASKS']['BackupSource']
        backup_target = config['TASKS']['BackupTarget']

        # 任务1: 清理过期文件
        message = clean_up_old_files(target_directory, expiration_days)
        update_log(log_text, message)
        
        # 如果任务被暂停，等待恢复
        while pause_event.is_set():
            time.sleep(1)
        
        if stop_event.is_set():
            update_log(log_text, "任务已停止。")
            return

        # 任务2: 备份任务
        message = backup_directory(backup_source, backup_target)
        update_log(log_text, message)

    # 确保任务线程已经启动
    logging.info("任务开始执行...")
    threading.Thread(target=task_thread).start()

# 暂停任务
def pause_task(pause_event, pause_button):
    if pause_event.is_set():
        pause_event.clear()
        pause_button.config(text="暂停")
    else:
        pause_event.set()
        pause_button.config(text="恢复")

# 停止任务
def stop_task(stop_event, pause_event, stop_button, pause_button):
    stop_event.set()  # 设置停止标志
    pause_event.clear()  # 停止时也清除暂停标志
    stop_button.config(state=tk.DISABLED)  # 停止按钮禁用
    pause_button.config(state=tk.DISABLED)  # 暂停按钮禁用

# 创建 GUI 窗口
def create_gui():
    window = tk.Tk()
    window.title("自动化任务工具")

    # 配置窗口大小
    window.geometry("600x400")

    # 配置输入框和标签
    tk.Label(window, text="清理文件夹路径:").grid(row=0, column=0, padx=10, pady=5)
    entry_directory = tk.Entry(window, width=40)
    entry_directory.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(window, text="文件过期天数:").grid(row=1, column=0, padx=10, pady=5)
    entry_days = tk.Entry(window, width=40)
    entry_days.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(window, text="备份源目录:").grid(row=2, column=0, padx=10, pady=5)
    entry_backup_source = tk.Entry(window, width=40)
    entry_backup_source.grid(row=2, column=1, padx=10, pady=5)

    tk.Label(window, text="备份目标目录:").grid(row=3, column=0, padx=10, pady=5)
    entry_backup_target = tk.Entry(window, width=40)
    entry_backup_target.grid(row=3, column=1, padx=10, pady=5)

    # 控制按钮
    pause_event = threading.Event()  # 用于暂停/恢复
    stop_event = threading.Event()   # 用于停止任务

    def start_button_action():
        config = read_config()
        # 更新配置文件中的任务参数
        config['TASKS']['Directory'] = entry_directory.get()
        config['TASKS']['ExpirationDays'] = entry_days.get()
        config['TASKS']['BackupSource'] = entry_backup_source.get()
        config['TASKS']['BackupTarget'] = entry_backup_target.get()

        with open('config.ini', 'w') as configfile:
            config.write(configfile)

        # 调用启动任务
        logging.info("点击了启动任务按钮...")
        start_task(log_text, config, pause_event, stop_event)

    start_button = tk.Button(window, text="启动任务", command=start_button_action)
    start_button.grid(row=4, column=0, columnspan=2, pady=10)

    # 暂停和停止按钮
    pause_button = tk.Button(window, text="暂停", command=lambda: pause_task(pause_event, pause_button))
    pause_button.grid(row=5, column=0, padx=10, pady=5)

    stop_button = tk.Button(window, text="停止", command=lambda: stop_task(stop_event, pause_event, stop_button, pause_button))
    stop_button.grid(row=5, column=1, padx=10, pady=5)

    # 日志输出区域
    log_text = scrolledtext.ScrolledText(window, width=70, height=15, wrap=tk.WORD, state=tk.DISABLED)
    log_text.grid(row=6, column=0, columnspan=2, padx=10, pady=10)



    window.mainloop()

if __name__ == "__main__":
    setup_logging()
    create_gui()
