import configparser
import os
import time
import datetime
from pywinauto.application import Application
# ใช้ send_keys เพื่อจำลองการกดคีย์บอร์ดระดับ System (แม่นยำกว่า type_keys)
from pywinauto.keyboard import send_keys 
from pywinauto import mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): return None
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Helper Functions (Keyboard Only) =================
def force_scroll_down(window):
    """ฟังก์ชันช่วยเลื่อนหน้าจอลงโดยใช้ปุ่ม PageDown"""
    log(f"...กดปุ่ม PageDown เพื่อเลื่อนหน้าจอ...")
    try:
        window.set_focus()
        send_keys("{PGDN}")
        time.sleep(0.5)
    except Exception as e:
        log(f"[!] Keyboard scroll failed: {e}")

def ensure_focus(window):
    """ทำให้แน่ใจว่าหน้าจอ Focus อยู่"""
    try:
        window.set_focus()
        time.sleep(0.5)
        # คลิกกลางจอเบาๆ 1 ทีเพื่อเรียก Focus (เผื่อ set_focus ไม่ติด)
        rect = window.rectangle()
        center_x = rect.mid_point().x
        center_y = rect.mid_point().y
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.5)
    except: pass

def smart_click(window, criteria_list, timeout=5, optional=False):
    """
    คลิกปุ่มโดยใช้ UIA Invoke Pattern
    """
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text():
                        try:
                            child.invoke()
                            log(f"[/] สั่งงานปุ่ม '{criteria}' สำเร็จ (Invoke)")
                            return True
                        except:
                            try:
                                child.select()
                                log(f"[/] เลือกปุ่ม '{criteria}' สำเร็จ (Select)")
                                return True
                            except:
                                child.set_focus()
                                send_keys("{ENTER}")
                                log(f"[/] กด Enter ใส่ปุ่ม '{criteria}'")
                                return True
            except: pass
        time.sleep(0.5)

    if not optional:
        log(f"[X] หาปุ่ม {criteria_list} ไม่เจอ!")
    return False

def check_exists(window, text):
    """เช็คว่ามีข้อความปรากฏบนหน้าจอหรือไม่"""
    try:
        for child in window.descendants():
            if child.is_visible() and text in child.window_text():
                return True
    except: pass
    return False

def smart_input_with_keyboard(window, label_text, value):
    """กรอกข้อมูลโดยใช้การ Tab หาช่อง"""
    log(f"...กำลังพยายามกรอก '{label_text}': {value}")
    try:
        edits = window.descendants(control_type="Edit")
        for edit in edits:
            if edit.is_visible() and (label_text in edit.element_info.name or label_text in edit.window_text()):
                edit.set_focus()
                send_keys(str(value), with_spaces=True)
                return True
    except: pass
    return False

# ================= 3. Main Scenario (เฉพาะส่วนบริการหลัก) =================
def run_smart_scenario(main_window, config):
    try:
        add_insurance = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('InsuranceAmount', '0')
    except: return

    log(f"\n--- เริ่มต้นทดสอบ (Test Mode: Direct Keyboard Send) ---")
    log("กรุณาตรวจสอบว่าเปิดหน้า 'บริการหลัก' รอไว้แล้ว")
    time.sleep(2)

    # =========================================================
    # --- STEP: เลือกบริการ (EMS) ด้วย Hotkey (วิธีใหม่) ---
    # =========================================================
    log("STEP: ใช้ Hotkey เลือกบริการ EMS (วิธี Direct SendKeys)")
    
    if not check_exists(main_window, "บริการหลัก"):
        log("[Warning] ไม่พบข้อความ 'บริการหลัก' (อาจจะอยู่ผิดหน้า)")

    # 1. เรียก Focus ให้ชัวร์ที่สุด
    ensure_focus(main_window)
    
    # 2. กดปุ่ม E (ใช้ send_keys เหมือนกดคีย์บอร์ดจริง)
    log("...กดปุ่ม 'e' (System Level)")
    send_keys("e") 
    time.sleep(1)
    
    # กดซ้ำอีกทีเผื่อไม่ติด
    send_keys("e")
    time.sleep(1)

    # 3. กด Enter
    log("...กด Enter เพื่อยืนยัน")
    send_keys("{ENTER}")
    time.sleep(3) # รอโหลด

    # --- ตรวจสอบผลลัพธ์ ---
    success_markers = ["EMS ในประเทศ", "รับประกัน", "1-2 วันทำการ", "เพิ่ม:", "Expected", "ข้อมูลเพิ่มเติม"]
    is_success = False
    
    for marker in success_markers:
        if check_exists(main_window, marker):
            is_success = True
            log(f"[/] สำเร็จ! พบข้อความ '{marker}' -> หน้าจอเปลี่ยนแล้ว")
            break
    
    if not is_success:
        log("[!] หน้าจอยังไม่เปลี่ยน... ลองวิธีกดปุ่มลูกศร + Enter")
        
        # ลองกดลูกศรขวา (เผื่อ EMS เป็นตัวเลือกที่ 2) หรือกด Tab
        # send_keys("{RIGHT}")
        # time.sleep(0.5)
        # send_keys("{ENTER}")

        if check_exists(main_window, "บริการหลัก"):
             log("\n[FAIL] ยังติดอยู่ที่หน้าบริการหลัก -> Hotkey ไม่ทำงาน ลองตรวจสอบภาษาแป้นพิมพ์ (ต้องเป็น ENG)")
             return

    # --- ส่วนประกัน ---
    if is_success and add_insurance.lower() == 'true':
        log(f"...ตรวจสอบประกันภัย")
        if smart_click(main_window, ["+", "AddService", "รับประกัน"], timeout=3, optional=True):
            time.sleep(1)
            try:
                ensure_focus(main_window)
                send_keys(str(insurance_amt))
            except: pass
            
            send_keys("{ENTER}")

    log("\n[TEST COMPLETED] จบการทดสอบแบบ Direct Keys")

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