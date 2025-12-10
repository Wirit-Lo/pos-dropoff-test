import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): return None
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Helper Functions =================
def force_scroll_down(window, scroll_dist=-5):
    """ฟังก์ชันช่วยเลื่อนหน้าจอลงโดยใช้ Mouse Wheel"""
    log(f"...กำลังเลื่อนหน้าจอลง (Mouse Wheel {scroll_dist})...")
    try:
        rect = window.rectangle()
        center_x = rect.left + 300
        center_y = rect.top + 300
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.5)
        mouse.scroll(coords=(center_x, center_y), wheel_dist=scroll_dist)
        time.sleep(1)
    except Exception as e:
        log(f"[!] Mouse scroll failed: {e}")
        window.type_keys("{PGDN}")

def smart_click(window, criteria_list, timeout=5, optional=False):
    """คลิกปุ่มตามรายการชื่อ"""
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text():
                        try:
                            # วาดกรอบสีแดงให้เห็นว่ากำลังจะกดปุ่มไหน
                            child.draw_outline(colour='red')
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

def check_exists(window, text):
    """เช็คว่ามีข้อความปรากฏบนหน้าจอหรือไม่"""
    try:
        for child in window.descendants():
            if child.is_visible() and text in child.window_text():
                return True
    except: pass
    return False

def smart_input_with_scroll(window, label_text, value, scroll_times=2):
    log(f"...กำลังพยายามกรอก '{label_text}': {value}")
    for i in range(scroll_times + 1):
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if edit.is_visible() and (label_text in edit.element_info.name or label_text in edit.window_text()):
                    edit.set_focus()
                    edit.click_input()
                    edit.type_keys(str(value), with_spaces=True)
                    return True
            
            labels = [c for c in window.descendants(control_type="Text") if label_text in c.window_text() and c.is_visible()]
            if labels:
                labels[0].click_input()
                window.type_keys("{TAB}")
                time.sleep(0.2)
                window.type_keys(str(value), with_spaces=True)
                return True
        except: pass

        if i < scroll_times:
            force_scroll_down(window, scroll_dist=-5)
            time.sleep(1)
    return False

# ================= 3. Main Scenario (เฉพาะส่วนบริการหลัก) =================
def run_smart_scenario(main_window, config):
    try:
        # Load Config (โหลดเฉพาะที่จำเป็น)
        add_insurance = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('InsuranceAmount', '0')
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except: return

    log(f"\n--- เริ่มต้นทดสอบ (Test Mode: หน้าบริการหลัก -> กด EMS) ---")
    log("กรุณาตรวจสอบว่าเปิดหน้า 'บริการหลัก' รอไว้แล้ว")
    time.sleep(2)

    # =========================================================
    # --- STEP: เลือกบริการ (EMS) ---
    # =========================================================
    log("STEP: เริ่มค้นหาปุ่ม EMS")
    
    # ตรวจสอบเบื้องต้น (Optional)
    if not check_exists(main_window, "บริการหลัก"):
        log("[Warning] ไม่พบข้อความ 'บริการหลัก' บนหน้าจอ (อาจจะกดไม่ติดถ้าอยู่ผิดหน้า)")

    # วนลูปพยายามกดจนกว่าจะผ่าน (Retry Logic)
    max_retries = 3
    is_success = False

    for attempt in range(max_retries):
        log(f"...ความพยายามครั้งที่ {attempt+1}")
        
        # 1. กดที่การ์ด EMS
        # เพิ่ม Keyword ให้ครอบคลุมที่สุด
        ems_keywords = ["บริการอีเอ็มเอส", "EMS", "E", "บริการด่วนพิเศษ"]
        
        if smart_click(main_window, ems_keywords, timeout=5):
            log("[/] กดการ์ด EMS แล้ว")
        else:
            log("[!] หาปุ่ม EMS ไม่เจอในรอบนี้")
        
        # 2. [สำคัญ] กดปุ่ม "ถัดไป" หรือ "Enter" เพื่อยืนยันการเลือก
        log("...กำลังกดปุ่ม 'ถัดไป' หรือ 'Enter' เพื่อยืนยันการเลือก")
        if not smart_click(main_window, ["ถัดไป", "Next", "ดำเนินการ"], timeout=3, optional=True):
            main_window.type_keys("{ENTER}")
        
        time.sleep(3) # รอโหลดหน้าใหม่

        # 3. เช็คว่าเปลี่ยนหน้าสำเร็จไหม?
        # หน้าใหม่ต้องมีคำว่า: "EMS ในประเทศ" (ในรายการขวา), "รับประกัน", "เพิ่ม:", หรือ "Expected"
        success_markers = ["EMS ในประเทศ", "รับประกัน", "1-2 วันทำการ", "เพิ่ม:", "Expected", "ข้อมูลเพิ่มเติม"]
        
        for marker in success_markers:
            if check_exists(main_window, marker):
                is_success = True
                log(f"[/] สำเร็จ! พบข้อความ '{marker}' -> หน้าจอเปลี่ยนแล้ว")
                break
        
        if is_success:
            break # ออกจากลูป Retry ถ้าสำเร็จแล้ว
        else:
            log("[!] หน้าจอยังไม่เปลี่ยน... ลองใหม่")
            
            # ถ้ายังเห็นคำว่า "บริการหลัก" แสดงว่ายังอยู่ที่เดิม
            if check_exists(main_window, "บริการหลัก"):
                log("    -> ยังติดอยู่ที่หน้าบริการหลัก")
            else:
                log("    -> หน้าจออาจจะเปลี่ยนแล้วแต่หาข้อความยืนยันไม่เจอ?")

    if not is_success:
        log("\n[FAIL] ไม่สามารถเข้าสู่หน้า EMS ได้หลังจากพยายามหลายครั้ง")
        return # หยุดการทำงานถ้าไปต่อไม่ได้

    # --- ส่วนประกัน (ทำงานต่อเมื่อหน้าจอเปลี่ยนสำเร็จแล้ว) ---
    # ใส่ไว้เผื่อคุณต้องการเทสว่าหลังกด E แล้วกดประกันต่อได้ไหม
    if add_insurance.lower() == 'true':
        log(f"...ตรวจสอบประกันภัย (วงเงิน: {insurance_amt})")
        if smart_click(main_window, ["+", "AddService", "รับประกัน"], timeout=3, optional=True):
            time.sleep(1)
            smart_input_with_scroll(main_window, "วงเงิน", insurance_amt)
            smart_click(main_window, ["ตกลง", "OK"], timeout=2, optional=True)

    log("\n[TEST COMPLETED] จบการทดสอบส่วนกด E")

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