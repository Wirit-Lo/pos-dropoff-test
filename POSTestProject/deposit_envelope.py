import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse  # ต้อง Import mouse เพื่อใช้เลื่อนหน้าจอ

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): return None
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Helper Functions (Scroll & Search) =================
def force_scroll_down(window, scroll_dist=-5):
    """
    ฟังก์ชันช่วยเลื่อนหน้าจอลงโดยใช้ Mouse Wheel
    scroll_dist ติดลบ = เลื่อนลง
    """
    log(f"...กำลังเลื่อนหน้าจอลง (Mouse Wheel {scroll_dist})...")
    try:
        rect = window.rectangle()
        # หาจุดกลางหน้าจอเพื่อวางเมาส์
        center_x = rect.left + 300
        center_y = rect.top + 300
        
        # คลิกเพื่อให้หน้าจอ Focus ก่อนเลื่อน
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.5)
        # สั่งเลื่อนเมาส์
        mouse.scroll(coords=(center_x, center_y), wheel_dist=scroll_dist)
        time.sleep(1)
    except Exception as e:
        log(f"[!] Mouse scroll failed: {e}")
        # ถ้าใช้เมาส์ไม่ได้ ให้ลองกดปุ่ม Page Down แทน
        window.type_keys("{PGDN}")

def smart_click(window, criteria_list, timeout=5, optional=False):
    """คลิกปุ่มตามรายการชื่อ (รองรับหลายชื่อ)"""
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

# ================= 3. Smart Input Functions =================
def smart_input_weight(window, value):
    """ฟังก์ชันกรอกน้ำหนัก"""
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
    
    # Fallback methods...
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_input_with_scroll(window, label_text, value, scroll_times=2):
    """
    ฟังก์ชันกรอกข้อมูลที่รองรับการเลื่อนหน้าจอ
    """
    log(f"...กำลังพยายามกรอก '{label_text}': {value}")

    for i in range(scroll_times + 1):
        try:
            # 1. พยายามหา Edit Box ที่สัมพันธ์กับชื่อ Label
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if edit.is_visible() and (label_text in edit.element_info.name or label_text in edit.window_text()):
                    edit.set_focus()
                    edit.click_input()
                    edit.type_keys(str(value), with_spaces=True)
                    log(f"[/] กรอก {label_text} สำเร็จ (Found by Name)")
                    return True
            
            # 2. ถ้าหาจากชื่อ Edit ไม่เจอ ลองหา Text Label แล้วกด Tab
            labels = [c for c in window.descendants(control_type="Text") if label_text in c.window_text() and c.is_visible()]
            if labels:
                log(f"[/] เจอ Label '{label_text}' -> กำลังกด Tab เพื่อเข้าช่องกรอก")
                labels[0].click_input() # คลิกที่ข้อความก่อน
                window.type_keys("{TAB}") # กด Tab เพื่อไปช่อง Input ถัดไป
                time.sleep(0.2)
                window.type_keys(str(value), with_spaces=True)
                return True

        except Exception as e:
            log(f"[!] Error finding input: {e}")

        # ถ้ายังไม่เจอ ให้เลื่อนจอ
        if i < scroll_times:
            log(f"[Rotate {i+1}] หาช่องไม่เจอ... กำลังเลื่อนหน้าจอลง...")
            force_scroll_down(window, scroll_dist=-5)
            time.sleep(1)

    log(f"[X] หมดความพยายามในการหาช่อง '{label_text}'")
    return False

def smart_next(window):
    """กดถัดไป หรือ Enter"""
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

def process_sender_info(window, phone_number):
    """
    [UPDATED] ฟังก์ชันจัดการหน้าผู้ฝากส่ง (อ่านบัตร -> กรอกเบอร์ -> ถัดไป)
    """
    log("...เช็คหน้า Popup ผู้ฝากส่ง...")
    # เช็คว่ามีปุ่มอ่านบัตรประชาชนหรือไม่ (ถ้ามีแสดงว่าอยู่หน้าผู้ฝากส่ง)
    if smart_click(window, "อ่านบัตรประชาชน", timeout=5, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> กดอ่านบัตรเรียบร้อย")
        time.sleep(1) # รอข้อมูลบัตรขึ้น
        
        # [แก้ไข] กรอกเบอร์โทรศัพท์ก่อนกดถัดไป
        smart_input_with_scroll(window, "หมายเลขโทรศัพท์", phone_number)
        
        # [แก้ไข] เมื่อกรอกเสร็จแล้ว ค่อยกดถัดไป
        log("...ข้อมูลครบถ้วน กดถัดไป...")
        smart_next(window)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง -> ข้ามไปขั้นตอนต่อไป")

def wait_for_text(window, text, timeout=10):
    log(f"...รอข้อความ '{text}'...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    return True
        except: pass
        time.sleep(0.5)
    return False

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        # [แก้ไข] ดึงข้อมูลจาก Config ให้ถูกหมวด (TEST_DATA สำหรับเบอร์โทร)
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678') # ดึงจาก TEST_DATA
        
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except Exception as e: 
        log(f"[Error] Config ผิดพลาด: {e}")
        return

    log(f"\n--- เริ่มต้น Scenario (Smart Mode) Phone: {phone} ---")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # --- [UPDATED] ขั้นตอนผู้ฝากส่ง (รวม Read ID + Phone + Enter ไว้ในฟังก์ชันเดียว) ---
    process_sender_info(main_window, phone)
    time.sleep(step_delay)

    # 2. ซองจดหมาย (รูปร่าง)
    if not smart_click(main_window, "ซองจดหมาย"): return
    time.sleep(step_delay)

    # 3. ซองจดหมาย (หมวดหมู่) --> Enter ผ่าน
    log("STEP 3: กด Enter ผ่านหมวดหมู่")
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # 4. น้ำหนัก
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    
    wait_for_text(main_window, "รหัสไปรษณีย์")
    time.sleep(0.5) 

    # 5. รหัสไปรษณีย์
    log(f"...กรอกรหัสไปรษณีย์: {postal}")
    try:
        edits = [e for e in main_window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(postal))
        else:
            main_window.type_keys(str(postal), with_spaces=True)
    except:
        main_window.type_keys(str(postal), with_spaces=True)
    
    smart_next(main_window)
    time.sleep(step_delay)

    # 6. จบงาน
    log("STEP 6: จบงาน")
    if smart_click(main_window, "ดำเนินการ", timeout=3, optional=True):
        log("[/] กดปุ่ม 'ดำเนินการ' สำเร็จ")
    
    final_buttons = ["เสร็จสิ้น", "Settle", "ยืนยัน", "ตกลง"]
    smart_click(main_window, final_buttons, timeout=3, optional=True)
    main_window.type_keys("{ENTER}")

    log("\n[SUCCESS] จบการทำงาน")

# ================= 5. Execution =================
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