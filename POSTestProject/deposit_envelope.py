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

# ================= 2. Smart Functions (Adaptive) =================
def smart_click(window, criteria_list, timeout=5, optional=False):
    """
    คลิกปุ่มตามรายการชื่อ (รองรับหลายชื่อ)
    optional=True: ถ้าหาไม่เจอให้ปล่อยผ่าน (ไม่ Error)
    """
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                # Deep Search
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text():
                        try:
                            child.click_input()
                            log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                            return True
                        except:
                            child.click_input(double=True)
                            log(f"[/] Double Click '{criteria}'")
                            return True
            except: pass
        time.sleep(0.5)

    if not optional:
        log(f"[X] หาปุ่ม {criteria_list} ไม่เจอ!")
    return False

def check_sender_popup(window):
    """
    ฟังก์ชันเช็คหน้า 'ผู้ฝากส่ง'
    เพิ่ม Timeout เป็น 5 วินาที เพื่อให้ดักจับ Popup ได้ทัน
    """
    log("...เช็ค Popup ผู้ฝากส่ง (รอ 5 วินาที)...")
    if smart_click(window, "อ่านบัตรประชาชน", timeout=5, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> กดอ่านบัตรเรียบร้อย")
        time.sleep(1)
        smart_click(window, "ถัดไป", timeout=2, optional=True)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง -> ข้ามไปขั้นตอนต่อไป")

def smart_input_weight(window, value):
    log(f"...กำลังกรอกน้ำหนัก: {value}")
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            target_box = edits[0]
            target_box.click_input()
            target_box.type_keys(str(value), with_spaces=True)
            log(f"[/] เจอ Edit Box และกรอก '{value}' สำเร็จ")
            return True
    except: pass

    log("...หา Edit Box ไม่เจอ ลองสูตร Click+Tab...")
    try:
        if smart_click(window, "น้ำหนัก", timeout=2, optional=True):
            window.type_keys("{TAB}")
            time.sleep(0.2)
            window.type_keys(str(value), with_spaces=True)
            log(f"[/] กรอก '{value}' ด้วยสูตร Tab สำเร็จ")
            return True
    except: pass

    log("...ลองพิมพ์สด (Blind Type)...")
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_next(window):
    """กดถัดไป หรือ Enter"""
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

def wait_for_text(window, text, timeout=10):
    """รอให้ข้อความปรากฏบนหน้าจอ (ใช้เช็คว่าเปลี่ยนหน้าหรือยัง)"""
    log(f"...รอข้อความ '{text}'...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    return True
        except: pass
        time.sleep(0.5)
    log(f"[!] รอ '{text}' จนหมดเวลา (อาจจะยังอยู่หน้าเดิม)")
    return False

# ================= 3. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE']['Weight']
        postal = config['DEPOSIT_ENVELOPE']['PostalCode']
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except: 
        log("[Error] Config ผิดพลาด")
        return

    log(f"\n--- เริ่มต้น Scenario (ซองจดหมาย - Smart Mode) ---")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # 2. ซองจดหมาย (รูปร่าง)
    if not smart_click(main_window, "ซองจดหมาย"): return
    time.sleep(step_delay)

    # 3. ซองจดหมาย (หมวดหมู่) --> แก้ไข: กด Enter ผ่านไปเลย
    log("STEP 3: กด Enter ผ่านหมวดหมู่")
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # --- เช็ค Popup ผู้ฝากส่ง ---
    check_sender_popup(main_window)
    time.sleep(step_delay)

    # 4. น้ำหนัก
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    
    # --- แก้ไข: รอให้หน้าจอเปลี่ยนไปหน้า "รหัสไปรษณีย์" ก่อน ---
    # ป้องกันการพิมพ์เลข ปณ. ใส่ช่องน้ำหนัก
    wait_for_text(main_window, "รหัสไปรษณีย์")
    time.sleep(0.5) 

    # 5. รหัสไปรษณีย์
    log(f"...กรอกรหัสไปรษณีย์: {postal}")
    try:
        # หา Edit Box ตัวแรก (ตอนนี้ควรเป็นหน้าใหม่แล้ว)
        edits = [e for e in main_window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            postal_box = edits[0]
            postal_box.click_input()
            postal_box.type_keys(str(postal))
        else:
            # ถ้าไม่เจอช่อง ให้พิมพ์สด
            main_window.type_keys(str(postal), with_spaces=True)
    except:
        main_window.type_keys(str(postal), with_spaces=True)
    
    smart_next(main_window)
    time.sleep(step_delay)

    # 6. จบงาน
    log("STEP 6: จบงาน")
    if smart_click(main_window, "ดำเนินการ", timeout=3, optional=True):
        log("[/] กดปุ่ม 'ดำเนินการ' (Popup ทับซ้อน) สำเร็จ")
    
    final_buttons = ["เสร็จสิ้น", "Settle", "ยืนยัน", "ตกลง"]
    smart_click(main_window, final_buttons, timeout=3, optional=True)
    
    main_window.type_keys("{ENTER}")

    log("\n[SUCCESS] จบการทำงาน")

# ================= 4. Execution =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            connect_wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app = Application(backend="uia").connect(title_re=conf['APP']['WindowTitle'], timeout=connect_wait)
            win = app.top_window()
            win.set_focus()
            
            run_smart_scenario(win, conf)
            
        except Exception as e:
            log(f"Error: {e}")