import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    if not os.path.exists(filename): return None
    config = configparser.ConfigParser()
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Smart System (วัดความเร็ว + ค้นหาฉลาด) =================
def calibrate_system():
    """วัดความเร็วเครื่องเพื่อปรับ Timeout"""
    log("...ตรวจสอบความเร็วเครื่อง...")
    start = time.time()
    for _ in range(3000000): pass # Test CPU
    duration = time.time() - start
    
    factor = 2.0 if duration > 0.5 else (1.5 if duration > 0.25 else 1.0)
    log(f"[System] Speed Factor: x{factor} (Duration: {duration:.2f}s)")
    return factor

def smart_click(window, criteria, timeout=5):
    """หาปุ่มและกด (รองรับ Deep Search)"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            # หาแบบปกติ + แบบ Deep Search ในตัวเดียว
            if window.child_window(title=criteria).exists():
                window.child_window(title=criteria).click_input()
                log(f"[/] Click '{criteria}'")
                return True
            
            for child in window.descendants():
                if child.is_visible() and criteria in child.window_text():
                    child.click_input()
                    log(f"[/] Click '{criteria}' (Deep)")
                    return True
        except: pass
        time.sleep(0.3)
    log(f"[X] Not Found: '{criteria}'")
    return False

def force_scroll(window, dist=-20):
    """เลื่อนจอลง"""
    try:
        rect = window.rectangle()
        # คลิกกลางจอก่อนเลื่อน
        mouse.click(coords=(rect.left+300, rect.top+300))
        time.sleep(0.1)
        mouse.scroll(coords=(rect.left+300, rect.top+300), wheel_dist=dist)
        time.sleep(0.5)
    except: window.type_keys("{PGDN}")

def smart_input_phone(window, phone, scroll_dist):
    """เลื่อนหาช่องเบอร์ -> คลิก Label -> กด Tab -> พิมพ์"""
    log(f"...ค้นหาช่องเบอร์โทรศัพท์...")
    labels = ["หมายเลขโทรศัพท์", "เบอร์โทรศัพท์", "โทรศัพท์"]
    
    # วนลูปเลื่อนหา 3 รอบ
    for i in range(3):
        # ลองหา Label ก่อน
        for label in labels:
            if smart_click(window, label, timeout=1):
                # ถ้าเจอ Label ให้กด TAB เข้าช่อง Input
                window.type_keys("{TAB}")
                time.sleep(0.2)
                window.type_keys(str(phone), with_spaces=True)
                log("[/] กรอกเบอร์สำเร็จ")
                return True
        
        # ถ้าไม่เจอ ให้เลื่อนจอลงแล้วหาใหม่
        log(f"...ไม่เจอช่องเบอร์ (รอบ {i+1}) -> Scroll Down...")
        force_scroll(window, scroll_dist)

    # ทาง