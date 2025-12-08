import configparser
import os
import time
import datetime
from pywinauto.application import Application

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): return None
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Smart Functions (หัวใจหลัก) =================
def dump_ui(window):
    """ฟังก์ชันฉลาด: อ่านปุ่มทั้งหน้าแล้วบอกเราว่ามีอะไรบ้าง (ใช้เมื่อหาไม่เจอ)"""
    log("\n[DEBUG] --- รายชื่อ Element ที่มองเห็นบนหน้าจอ ---")
    try:
        for child in window.descendants():
            if child.is_visible() and child.window_text():
                print(f"   • Type: {child.element_info.control_type:15} | Name: '{child.window_text()}'")
    except: pass
    log("----------------------------------------------------\n")

def smart_click(window, text_criteria, timeout=5):
    """หาปุ่มที่มีคำว่า text_criteria (ไม่สนว่าเป็นปุ่ม/ข้อความ/รูป) แล้วกดเลย"""
    start = time.time()
    while time.time() - start < timeout:
        # วิธีที่ 1: หาแบบปกติ
        try:
            target = window.child_window(title=text_criteria)
            if target.exists() and target.is_visible():
                target.click_input()
                log(f"[/] กดปุ่ม '{text_criteria}' สำเร็จ")
                return True
        except: pass
        
        # วิธีที่ 2: หาแบบ Deep Search (สแกนลูกหลานทั้งหมด)
        try:
            for child in window.descendants():
                if text_criteria in child.window_text() and child.is_visible():
                    try:
                        child.click_input()
                        log(f"[/] เจอและกด '{text_criteria}' (Deep Search)")
                        return True
                    except: 
                        # ถ้ากดไม่ได้ ลอง Double Click เผื่อเป็น ListItem
                        child.click_input(double=True)
                        log(f"[/] Double Click '{text_criteria}'")
                        return True
        except: pass
        time.sleep(0.5)
    
    log(f"[X] หาปุ่ม '{text_criteria}' ไม่เจอ!")
    dump_ui(window) # <--- สั่งให้อ่านหน้าจอทันทีถ้าหาไม่เจอ
    return False

def smart_type(window, text_value):
    """พิมพ์ข้อมูลลงไปเลย โดยไม่ต้องหาช่อง (ใช้ Active Focus หรือ Tab เอา)"""
    log(f"...กำลังพิมพ์ '{text_value}'...")
    try:
        # วิธีที่ 1: พิมพ์ใส่วินโดว์เลย (ถ้า Cursor กระพริบอยู่แล้ว จะติดทันที)
        window.type_keys(str(text_value), with_spaces=True)
        log(f"[/] ส่งค่า '{text_value}' เรียบร้อย")
        return True
    except Exception as e:
        log(f"[!] พิมพ์ไม่ได้: {e}")
        return False

def smart_next(window):
    """หาปุ่มถัดไป หรือกด Enter"""
    if not smart_click(window, "ถัดไป", timeout=2):
        log("...หาปุ่มถัดไปไม่เจอ -> กด Enter แทน")
        window.type_keys("{ENTER}")

# ================= 3. Main Scenario (สั้นลง เร็วขึ้น) =================
def run_fast_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE']['Weight']
        postal = config['DEPOSIT_ENVELOPE']['PostalCode']
        delay = int(config['SETTINGS']['StepDelay'])
    except: return

    log(f"\n--- เริ่มต้น Fast Scenario (ซองจดหมาย) ---")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(delay)

    # 2. ซองจดหมาย (รูปร่าง)
    if not smart_click(main_window, "ซองจดหมาย"): return
    time.sleep(delay)

    # 3. ซองจดหมาย (หมวดหมู่) - บางทีมันเลือกให้อยู่แล้ว ถ้าไม่เจอก็ข้ามได้
    smart_click(main_window, "ซองจดหมาย") 
    time.sleep(delay)

    # 4. น้ำหนัก (จุดปราบเซียน) -> ใช้ Smart Type
    log(f"STEP 4: กรอกน้ำหนัก {weight}")
    # ลองกด Tab 1 ทีเผื่อ Focus ไม่มา
    # main_window.type_keys("{TAB}") 
    smart_type(main_window, weight)
    smart_next(main_window) # กดถัดไป/Enter
    time.sleep(delay)

    # 5. รหัสไปรษณีย์ -> ใช้ Smart Type เหมือนกัน
    log(f"STEP 5: กรอกรหัสไปรษณีย์ {postal}")
    smart_type(main_window, postal)
    smart_next(main_window)
    time.sleep(delay)

    # 6. ดำเนินการ
    log("STEP 6: ดำเนินการ")
    if not smart_click(main_window, "ดำเนินการ"):
        main_window.type_keys("{ENTER}")

    log("\n[SUCCESS] จบงานแบบรวดเร็ว")

# ================= 4. Execution =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            app = Application(backend="uia").connect(title_re=conf['APP']['WindowTitle'], timeout=10)
            win = app.top_window()
            win.set_focus()
            run_fast_scenario(win, conf)
        except Exception as e:
            log(f"Error: {e}")