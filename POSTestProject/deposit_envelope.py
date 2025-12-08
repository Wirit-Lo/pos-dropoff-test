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

# ================= 2. Smart Functions (ฉลาด + สั้น) =================
def dump_ui(window):
    """อ่านรายชื่อปุ่มบนหน้าจอ (ทำงานเฉพาะตอนหาไม่เจอ)"""
    log("\n[DEBUG] --- Elements on Screen ---")
    try:
        for child in window.descendants():
            if child.is_visible() and child.window_text():
                # กรองเอาเฉพาะที่สำคัญๆ มาแสดง
                print(f"   • {child.element_info.control_type:12} | '{child.window_text()}'")
    except: pass
    log("----------------------------------\n")

def smart_click(window, criteria_list, timeout=5):
    """
    รับชื่อปุ่มได้หลายชื่อ (List) เช่น ["ดำเนินการ", "เสร็จสิ้น", "Settle"]
    เจออันไหนกดอันนั้น
    """
    if isinstance(criteria_list, str): criteria_list = [criteria_list] # แปลงเป็น list ถ้ามาตัวเดียว
    
    start = time.time()
    while time.time() - start < timeout:
        # วนลูปหาทุกชื่อที่ให้มา
        for criteria in criteria_list:
            try:
                # 1. หาแบบ Deep Search (สแกนทุกลูกหลาน)
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text():
                        try:
                            child.click_input()
                            log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                            return True
                        except:
                            child.click_input(double=True) # เผื่อต้อง Double Click
                            log(f"[/] Double Click '{criteria}'")
                            return True
            except: pass
        time.sleep(0.5)

    log(f"[X] หาปุ่มในรายการ {criteria_list} ไม่เจอ!")
    dump_ui(window) # หาไม่เจอค่อยโชว์ Dump
    return False

def smart_input(window, label_text, value, delay=0.5):
    """
    เทคนิค: คลิกที่ 'ชื่อหัวข้อ' ก่อน -> กด TAB -> พิมพ์ค่า
    ช่วยให้เข้าช่องถูก 100% แม้หา Edit Box ไม่เจอ
    """
    log(f"...กรอก '{label_text}': {value}")
    
    # 1. คลิกที่ Label เพื่อดึง Focus มาใกล้ๆ
    if smart_click(window, label_text, timeout=3):
        time.sleep(0.5)
        # 2. กด TAB เพื่อกระโดดเข้าช่อง Input ข้างๆ
        window.type_keys("{TAB}")
        time.sleep(0.2)
        # 3. พิมพ์ค่าลงไป
        try:
            window.type_keys(str(value), with_spaces=True)
            log(f"[/] พิมพ์ '{value}' เสร็จสิ้น")
            return True
        except:
            log(f"[!] พิมพ์ข้อมูลล้มเหลว")
            return False
    else:
        log(f"[!] หาหัวข้อ '{label_text}' ไม่เจอ (ข้ามการกรอก)")
        return False

def smart_next(window):
    """กดถัดไป หรือ Enter"""
    if not smart_click(window, "ถัดไป", timeout=2):
        # log("...ไม่เจอปุ่มถัดไป -> กด Enter")
        window.type_keys("{ENTER}")

# ================= 3. Main Scenario =================
def run_fast_scenario(main_window, config):
    # โหลดค่า Config
    try:
        weight = config['DEPOSIT_ENVELOPE']['Weight']
        postal = config['DEPOSIT_ENVELOPE']['PostalCode']
        # ดึงค่า Delay ถ้าไม่มีให้ใช้ 1 วินาที
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except: 
        log("[Error] Config ผิดพลาด")
        return

    log(f"\n--- เริ่มต้น Scenario (ซองจดหมาย) ---")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # 2. ซองจดหมาย (รูปร่าง)
    if not smart_click(main_window, "ซองจดหมาย"): return
    time.sleep(step_delay)

    # 3. ซองจดหมาย (หมวดหมู่)
    smart_click(main_window, "ซองจดหมาย") 
    time.sleep(step_delay)

    # 4. น้ำหนัก (ใช้เทคนิค Click Label + Tab)
    # smart_input จะคลิกที่คำว่า "น้ำหนัก" แล้ว TAB ไปกรอกค่าให้เอง
    smart_input(main_window, "น้ำหนัก", weight)
    smart_next(main_window)
    time.sleep(step_delay)

    # 5. รหัสไปรษณีย์
    smart_input(main_window, "รหัสไปรษณีย์", postal)
    smart_next(main_window)
    time.sleep(step_delay)

    # 6. ดำเนินการ / เสร็จสิ้น
    log("STEP 6: จบงาน")
    # ลองหาหลายๆ คำที่เป็นไปได้
    final_buttons = ["ดำเนินการ", "เสร็จสิ้น", "Settle", "ยืนยัน", "ตกลง"]
    if not smart_click(main_window, final_buttons):
        log("...หาปุ่มจบไม่เจอ ลองกด Enter...")
        main_window.type_keys("{ENTER}")

    log("\n[SUCCESS] จบการทำงาน")

# ================= 4. Execution =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            # เพิ่ม Timeout ตอน Connect เผื่อเครื่องช้า
            connect_wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            
            app = Application(backend="uia").connect(title_re=conf['APP']['WindowTitle'], timeout=connect_wait)
            win = app.top_window()
            win.set_focus()
            
            run_fast_scenario(win, conf)
            
        except Exception as e:
            log(f"Error: {e}")