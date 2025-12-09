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

def debug_current_screen(window):
    """
    [NEW] ฟังก์ชันช่วย Debug ดูว่าตอนนี้หน้าจอมีข้อความอะไรบ้าง
    จะทำงานเมื่อสคริปต์หาทางไปต่อไม่เจอ
    """
    log("!!! DEBUG: สคริปต์หยุดทำงาน - ตรวจสอบหน้าจอปัจจุบัน !!!")
    try:
        # ดึงข้อความทั้งหมดที่มองเห็นได้บนหน้าจอ
        texts = [child.window_text() for child in window.descendants(control_type="Text") if child.is_visible() and child.window_text()]
        # แสดงผลแค่ 20 ตัวแรกเพื่อไม่ให้รกเกินไป
        log(f"ข้อความที่พบบนหน้าจอ (บางส่วน): {texts[:20]}...")
        log("---------------------------------------------------")
    except Exception as e:
        log(f"Debug Error: {e}")

# ================= 2. Helper Functions (Scroll & Search) =================
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
    log(f"...กำลังกรอกน้ำหนัก: {value}")
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(value), with_spaces=True)
            log(f"[/] เจอ Edit Box และกรอก '{value}' สำเร็จ")
            return True
    except: pass
    window.type_keys(str(value), with_spaces=True)
    return True

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
                    log(f"[/] กรอก {label_text} สำเร็จ (Found by Name)")
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

def smart_next(window):
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

def process_sender_info(window, phone_number):
    log("...เช็คหน้า Popup ผู้ฝากส่ง...")
    if smart_click(window, "อ่านบัตรประชาชน", timeout=5, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> กดอ่านบัตรเรียบร้อย")
        time.sleep(1)
        smart_input_with_scroll(window, "หมายเลขโทรศัพท์", phone_number)
        log("...ข้อมูลครบถ้วน กดถัดไป...")
        smart_next(window)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง -> ข้ามไปขั้นตอนต่อไป")

def wait_for_text(window, text, timeout=10):
    """รอให้ข้อความปรากฏ"""
    log(f"...กำลังรอหน้า: '{text}'...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    log(f"[/] เจอข้อความ '{text}' แล้ว")
                    return True
        except: pass
        time.sleep(0.5)
    log(f"[!] ไม่เจอข้อความ '{text}' (Timeout)")
    return False

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        # Load Config
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        
        # [Config] ประกัน
        add_insurance = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False').lower() == 'true'
        insurance_amount = config['DEPOSIT_ENVELOPE'].get('InsuranceAmount', '0')

        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except Exception as e: 
        log(f"[Error] Config ผิดพลาด: {e}")
        return

    log(f"\n--- เริ่มต้น Scenario (Options: {special_options_str}, Insurance: {add_insurance}) ---")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # ผู้ฝากส่ง
    process_sender_info(main_window, phone)
    time.sleep(step_delay)

    # 2. ซองจดหมาย (รูปร่าง)
    if not smart_click(main_window, "ซองจดหมาย"): return
    time.sleep(step_delay)

    # 3. เลือกหมวดหมู่ / ลักษณะเฉพาะ
    log("STEP 3: เลือกหมวดหมู่/ลักษณะเฉพาะ")
    if special_options_str.strip():
        options = [opt.strip() for opt in special_options_str.split(',')]
        for opt in options:
            if opt:
                smart_click(main_window, opt, timeout=2, optional=True)
                time.sleep(0.5)
    
    log("...กด Enter เพื่อไปหน้าถัดไป")
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
    # เพิ่ม Wait นิดหน่อยหลังจากกดถัดไป ก่อนจะเช็ค Popup
    time.sleep(2)

    # --- [UPDATED] เช็ค Popup รหัสไปรษณีย์ทับซ้อน ---
    if smart_click(main_window, "ดำเนินการ", timeout=2, optional=True):
        log("[Popup] รหัสไปรษณีย์ทับซ้อน -> กด 'ดำเนินการ' สำเร็จ")
        time.sleep(1)
    else:
        try:
            if main_window.child_window(title__contains="ทับซ้อน").exists(timeout=1):
                log("[Popup] เจอป๊อปอัพทับซ้อน -> กด Enter")
                main_window.type_keys("{ENTER}")
                time.sleep(1)
        except: pass

    # STEP 6: บริการหลัก (Service Selection) - [Key Press Only]
    if wait_for_text(main_window, "บริการหลัก", timeout=10):
        log("...รอหน้าจอพร้อม 2 วินาที...")
        time.sleep(2)
        
        # 1. บังคับ Focus ที่หน้าต่างหลัก
        main_window.set_focus()

        # 2. วนลูปกด E จนกว่าจะไป
        ems_selected = False
        for attempt in range(5): # ลอง 5 รอบ
            
            # เช็คก่อนว่าเข้าหน้า EMS หรือยัง (เผื่อรอบก่อนหน้ากดติด)
            if wait_for_text(main_window, "EMS ในประเทศ", timeout=0.5):
                ems_selected = True
                log("[/] ตรวจพบหน้า 'EMS ในประเทศ' เรียบร้อย")
                break
            
            # กด E
            log(f"[Attempt {attempt+1}] กด E...")
            main_window.type_keys("E")
            time.sleep(1.5) # รอผลลัพธ์นานขึ้นนิดนึง
            
            # ถ้ากด E แล้วยังไม่ไป ลองกด Enter (เผื่อ E แค่เลือก)
            if not wait_for_text(main_window, "EMS ในประเทศ", timeout=0.5):
                 log(f"[Attempt {attempt+1}] ...หน้าจอยังไม่เปลี่ยน -> ลองกด Enter ย้ำ...")
                 main_window.type_keys("{ENTER}")
                 time.sleep(1.5)

        if not ems_selected:
            # เช็คครั้งสุดท้าย
            if wait_for_text(main_window, "EMS ในประเทศ", timeout=2):
                log("[/] (Late Check) ตรวจพบหน้า 'EMS ในประเทศ'")
            else:
                log("[X] ไม่สามารถเลือกบริการ EMS ได้ด้วยคีย์บอร์ด")
                debug_current_screen(main_window)
                return # หยุดทำงานถ้าเข้าไม่ได้

        # 3. เลือกประเภทส่ง (กด 0)
        log("STEP 6.5: เข้าหน้า EMS แล้ว -> กด 0")
        main_window.type_keys("0")
        time.sleep(step_delay)
    else:
        log("[!] หาหน้าบริการหลักไม่เจอ (ข้ามการกด E)")

    # --- STEP 7: เพิ่มประกัน (Insurance) ---
    if add_insurance:
        log(f"STEP 7: เพิ่มราคารับประกัน ({insurance_amount} บาท)")
        
        # 1. กดปุ่ม +
        if not smart_click(main_window, ["+", "เพิ่ม", "Add"], timeout=5, optional=True):
             log("[!] หาปุ่มเพิ่มประกัน (+) ไม่เจอ - ลองกดปุ่มบนคีย์บอร์ดแทน")
             main_window.type_keys("+")

        # 2. [Check] รอ Popup 'วงเงินประกัน' เด้งขึ้นมา
        if wait_for_text(main_window, "วงเงินประกัน", timeout=5):
            log("[/] Popup 'วงเงินประกัน' เด้งขึ้นมาแล้ว")
            time.sleep(0.5)
            
            # 3. พิมพ์จำนวนเงิน
            log(f"...พิมพ์จำนวนเงิน: {insurance_amount}")
            main_window.type_keys(str(insurance_amount))
            time.sleep(1)
            
            # 4. กดปุ่ม 'ถัดไป' หรือ 'Enter'
            if smart_click(main_window, ["ถัดไป", "Next", "Enter"], timeout=3, optional=True):
                log("[/] กดปุ่ม 'ถัดไป' บน Popup สำเร็จ")
            else:
                log("...กด Enter (เพื่อปิด Popup)")
                main_window.type_keys("{ENTER}")
            
            time.sleep(2)
        else:
            log("[X] ไม่เจอ Popup 'วงเงินประกัน' - หยุดการทำงานเพื่อตรวจสอบ")
            debug_current_screen(main_window)
            return 
             
    else:
        log("STEP 7: ไม่เพิ่มประกัน (ข้าม)")

    # Transition to Special Service
    log("...กำลังจะไปหน้าบริการพิเศษ (กด Enter)...")
    main_window.type_keys("{ENTER}")
    
    # --- STEP 8: บริการพิเศษ ---
    if wait_for_text(main_window, "บริการพิเศษ", timeout=10):
        log("STEP 8: บริการพิเศษ (เจอหน้าแล้ว -> กด A)")
        main_window.type_keys("A")
        time.sleep(step_delay)
    else:
        log("[X] หมดเวลา! ไม่เจอหน้า 'บริการพิเศษ' (ติดอยู่ที่หน้าเดิม?)")
        debug_current_screen(main_window)
        return 

    # --- STEP 9: จบงาน ---
    log("STEP 9: จบงาน (ยังไม่กด Z ตามคำสั่ง)")
    # main_window.type_keys("Z")

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