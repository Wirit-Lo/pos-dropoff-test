import configparser
import os
import time
import datetime
from pywinauto.application import Application
# เอา mouse ออก เพราะเราจะไม่ใช้แล้ว
# from pywinauto import mouse 

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
    """ฟังก์ชันช่วยเลื่อนหน้าจอลงโดยใช้ปุ่ม PageDown (ไม่ใช้เมาส์)"""
    log(f"...กดปุ่ม PageDown เพื่อเลื่อนหน้าจอ...")
    try:
        window.type_keys("{PGDN}")
        time.sleep(0.5)
    except Exception as e:
        log(f"[!] Keyboard scroll failed: {e}")

def smart_click(window, criteria_list, timeout=5, optional=False):
    """
    คลิกปุ่มโดยใช้ UIA Invoke Pattern (ไม่ขยับเมาส์)
    หรือใช้ Hotkey ถ้าจำเป็น
    """
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    # หา Element ที่มองเห็นและชื่อตรง
                    if child.is_visible() and criteria in child.window_text():
                        try:
                            # [NEW] ใช้ invoke() แทน click_input() 
                            # invoke คือการสั่งให้ปุ่มทำงานโดยตรงผ่าน Code (เหมือนกด Enter ใส่ปุ่ม)
                            # วิธีนี้เมาส์จะไม่ขยับ และไม่กดพลาดไปโดน Header
                            child.invoke()
                            log(f"[/] สั่งงานปุ่ม '{criteria}' สำเร็จ (Invoke)")
                            return True
                        except:
                            # ถ้า invoke ไม่ได้ (บางปุ่มไม่รองรับ) ให้ลอง select หรือกด Spacebar ใส่
                            try:
                                child.select()
                                log(f"[/] เลือกปุ่ม '{criteria}' สำเร็จ (Select)")
                                return True
                            except:
                                # Fallback สุดท้าย: set focus แล้วเคาะ Enter
                                child.set_focus()
                                child.type_keys("{ENTER}")
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
    """กรอกข้อมูลโดยใช้การ Tab หาช่อง (ไม่ใช้เมาส์คลิก)"""
    log(f"...กำลังพยายามกรอก '{label_text}': {value}")
    
    # 1. พยายามหา Edit Box แล้ว Focus
    try:
        edits = window.descendants(control_type="Edit")
        for edit in edits:
            if edit.is_visible() and (label_text in edit.element_info.name or label_text in edit.window_text()):
                edit.set_focus()
                edit.type_keys(str(value), with_spaces=True)
                return True
    except: pass

    # 2. ถ้าหาไม่เจอ ให้ลองกด Tab ไล่หา (วิธีแบบ Keyboard User)
    # วิธีนี้อาจจะต้องปรับจำนวน Tab ตามหน้าจอจริง
    # แต่เบื้องต้นลองหา Label แล้ว Tab 1 ที
    try:
        labels = [c for c in window.descendants(control_type="Text") if label_text in c.window_text() and c.is_visible()]
        if labels:
            # แค่ Focus ไปที่ Label (ถ้าทำได้) หรือสมมติว่า Cursor อยู่ใกล้ๆ
            # ในกรณี UIA อาจจะยากถ้าระบบไม่อนุญาตให้ Focus text
            pass 
    except: pass
    
    # Fallback: พิมพ์ลงไปเลยถ้าคิดว่า Cursor อยู่ถูกที่
    # window.type_keys(str(value), with_spaces=True)
    return False

# ================= 3. Main Scenario (เฉพาะส่วนบริการหลัก) =================
def run_smart_scenario(main_window, config):
    try:
        # Load Config
        add_insurance = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('InsuranceAmount', '0')
    except: return

    log(f"\n--- เริ่มต้นทดสอบ (Test Mode: Keyboard Only) ---")
    log("กรุณาตรวจสอบว่าเปิดหน้า 'บริการหลัก' รอไว้แล้ว")
    time.sleep(2)

    # =========================================================
    # --- STEP: เลือกบริการ (EMS) ด้วย Hotkey ---
    # =========================================================
    log("STEP: ใช้ Hotkey เลือกบริการ EMS")
    
    # ตรวจสอบเบื้องต้น
    if not check_exists(main_window, "บริการหลัก"):
        log("[Warning] ไม่พบข้อความ 'บริการหลัก' (อาจจะอยู่ผิดหน้า)")

    # ลองกด E (ตามที่คุณแจ้งว่ามี Hotkey)
    # การกดคีย์บอร์ดแม่นยำกว่าการคลิกตำแหน่งแน่นอน
    log("...กดปุ่ม 'E' บนคีย์บอร์ดเพื่อเลือก EMS")
    main_window.type_keys("e") 
    time.sleep(1)
    main_window.type_keys("E") # กดซ้ำเผื่อเป็น Case sensitive หรือกันพลาด
    time.sleep(2)

    # กด Enter เพื่อยืนยัน (เหมือนการกดปุ่ม 'ถัดไป')
    log("...กด Enter เพื่อยืนยันรายการ")
    main_window.type_keys("{ENTER}")
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
        log("[!] หน้าจอยังไม่เปลี่ยน... ลองกด Hotkey อื่น (เช่น F12 หรือ Tab->Enter)")
        
        # ลองกด F12 (ปุ่ม Next มาตรฐานของหลายโปรแกรม POS)
        # main_window.type_keys("{F12}") 
        
        # หรือลองกด Tab เพื่อเลื่อน Focus แล้ว Enter
        # main_window.type_keys("{TAB}")
        # main_window.type_keys("{ENTER}")

        if check_exists(main_window, "บริการหลัก"):
             log("\n[FAIL] ยังติดอยู่ที่หน้าบริการหลัก -> Hotkey E อาจจะไม่ทำงาน หรือต้องกดปุ่มอื่น")
             return

    # --- ส่วนประกัน ---
    if is_success and add_insurance.lower() == 'true':
        log(f"...ตรวจสอบประกันภัย")
        # ใช้ smart_click แบบ invoke (ไม่ใช้เมาส์)
        if smart_click(main_window, ["+", "AddService", "รับประกัน"], timeout=3, optional=True):
            time.sleep(1)
            # กรอกวงเงิน
            try:
                # ลองพิมพ์ตัวเลขเลย เพราะ Popup เด้งมา Cursor มักจะรออยู่แล้ว
                main_window.type_keys(str(insurance_amt))
            except: pass
            
            # กด Enter เพื่อตกลง (แทนการหาปุ่ม OK)
            main_window.type_keys("{ENTER}")

    log("\n[TEST COMPLETED] จบการทดสอบแบบไม่ใช้เมาส์")

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