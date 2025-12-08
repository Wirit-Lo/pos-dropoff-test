import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Configuration Management =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename):
        print(f"[ERROR] ไม่พบไฟล์ {filename}")
        return None
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

# ================= 2. Helper Functions =================
def print_window_controls(window):
    """ฟังก์ชัน Debug: ปริ้นท์ชื่อ Element ทั้งหมดในหน้าจอ"""
    log("\n[DEBUG] --- รายชื่อปุ่มที่ระบบมองเห็น (Visible Elements) ---")
    try:
        # ดึง element ลูกๆ ทั้งหมด
        descendants = window.descendants()
        for i, child in enumerate(descendants):
            # ดึงชื่อและประเภท
            name = child.window_text()
            control_type = child.element_info.control_type
            
            # ปริ้นท์เฉพาะที่มีชื่อและมองเห็นได้
            if name and child.is_visible():
                print(f"  {i+1}. Name: '{name}' | Type: {control_type}")
    except Exception as e:
        print(f"  [Error displaying controls]: {e}")
    log("[DEBUG] ------------------------------------------------\n")

def wait_and_find(root_window, criteria, timeout, control_type=None, parent_step="Unknown"):
    """ฟังก์ชันช่วยค้นหาปุ่มหรือข้อความ"""
    try:
        if control_type:
            element = root_window.child_window(title=criteria, control_type=control_type)
        else:
            element = root_window.child_window(title=criteria)
        
        element.wait('exists', timeout=timeout)
        return element
    except Exception:
        # ไม่ต้อง Log Error ที่นี่ เดี๋ยวไปจัดการข้างนอกเพื่อให้ Code สะอาดขึ้น
        return None

def click_next_button(window, timeout):
    """ฟังก์ชันกดปุ่ม 'ถัดไป' (Next)"""
    log("...กำลังหาปุ่ม 'ถัดไป'...")
    # ลองหาทั้งแบบ Button และ Text
    btn = wait_and_find(window, "ถัดไป", timeout, control_type="Button", parent_step="ClickNext")
    if not btn:
         btn = wait_and_find(window, "ถัดไป", timeout, control_type="Text", parent_step="ClickNext_Retry")

    if btn:
        btn.click_input()
        log("[/] กดปุ่ม 'ถัดไป' สำเร็จ")
        return True
    else:
        log("[!] หาปุ่มถัดไปไม่เจอ (อาจจะเปลี่ยนหน้าเอง หรือต้องกด Enter)")
        return False

# ================= 3. Deposit Scenario Logic =================
def deposit_envelope_scenario(main_window, config):
    # ดึงค่าจาก Config Section ใหม่ [DEPOSIT_ENVELOPE]
    try:
        weight_val = config['DEPOSIT_ENVELOPE']['Weight']
        postal_code_val = config['DEPOSIT_ENVELOPE']['PostalCode']
    except KeyError:
        log("[ERROR] ไม่พบค่าใน Config กรุณาเช็คหัวข้อ [DEPOSIT_ENVELOPE]")
        return
    
    # ค่า Setting ทั่วไป
    timeout_val = int(config['SETTINGS']['ElementWaitTimeout'])
    step_delay = int(config['SETTINGS']['StepDelay'])

    log(f"\n--- เริ่มต้น Scenario: รับฝากสิ่งของ (ซองจดหมาย) ---")
    log(f"ข้อมูลทดสอบ: น้ำหนัก {weight_val}g / ปณ. {postal_code_val}")
    time.sleep(1)

    # 1. กดเมนู "รับฝากสิ่งของ"
    log("STEP 1: เลือกเมนู 'รับฝากสิ่งของ'")
    
    # พยายามหาหลายๆ รูปแบบ (Button, ListItem, Text)
    btn_step1 = None
    search_types = ["ListItem", "Text", "Button", None] # None คือหาแบบไม่ระบุประเภท
    
    for c_type in search_types:
        btn_step1 = wait_and_find(main_window, "รับฝากสิ่งของ", timeout=3, control_type=c_type, parent_step="Step1")
        if btn_step1:
            log(f"[/] เจอเมนู 'รับฝากสิ่งของ' (Type: {c_type})")
            break
            
    if btn_step1:
        btn_step1.click_input()
    else:
        log("[X] ไม่เจอเมนู 'รับฝากสิ่งของ' เลยสักรูปแบบ")
        # *** เรียกใช้ฟังก์ชัน Debug เพื่อดูชื่อปุ่มจริง ***
        print_window_controls(main_window)
        return
        
    time.sleep(step_delay)

    # 2. กดเลือก "ซองจดหมาย" (ครั้งที่ 1 - รูปร่าง)
    log("STEP 2: เลือกรูปร่าง 'ซองจดหมาย'")
    btn_step2 = None
    for c_type in ["ListItem", "Text", "Button", "Image"]: # เพิ่ม Image เผื่อเป็นรูปภาพ
        btn_step2 = wait_and_find(main_window, "ซองจดหมาย", timeout=3, control_type=c_type, parent_step="Step2")
        if btn_step2:
            log(f"[/] เจอตัวเลือก 'ซองจดหมาย' (Type: {c_type})")
            break
            
    if btn_step2:
        try:
            btn_step2.click_input()
        except:
             # บางทีคลิกครั้งแรกไม่ติด ให้ลอง Double Click
             btn_step2.click_input(double=True)
    else:
        log("[X] ไม่เจอตัวเลือก 'ซองจดหมาย' (Step 2)")
        print_window_controls(main_window) # Debug
        return
    time.sleep(step_delay)

    # 3. กดเลือก "ซองจดหมาย" (ครั้งที่ 2 - หมวดหมู่)
    log("STEP 3: เลือกหมวดหมู่ 'ซองจดหมาย' อีกครั้ง")
    btn_step3 = wait_and_find(main_window, "ซองจดหมาย", timeout_val, parent_step="Step3")
    if btn_step3:
        try:
            btn_step3.click_input()
        except:
            pass 
    else:
        log("[!] ไม่เจอตัวเลือก 'ซองจดหมาย' ใน Step 3 (อาจจะข้ามขั้นตอนนี้?)")
    
    time.sleep(step_delay)

    # 4. ใส่น้ำหนัก
    log(f"STEP 4: กรอกน้ำหนัก ({weight_val} กรัม)")
    # หาช่องกรอกน้ำหนัก (หา Edit ตัวแรก หรือชื่อ 'น้ำหนัก')
    weight_input = None
    
    # ลองหาจากชื่อก่อน
    weight_input = wait_and_find(main_window, "น้ำหนัก", 3, control_type="Edit", parent_step="Step4")
    
    # ถ้าไม่เจอชื่อ ให้หา Edit Box ตัวแรกที่ว่างอยู่ หรือตัวแรกสุด
    if not weight_input:
        try:
             all_edits = main_window.descendants(control_type="Edit")
             if all_edits:
                 weight_input = all_edits[0] # เอาตัวแรกเลย
                 log("...ใช้ Edit Box ตัวแรกสำหรับการกรอกน้ำหนัก...")
        except: pass

    if weight_input:
        try:
            weight_input.set_focus()
            weight_input.type_keys(weight_val)
            log("[/] กรอกน้ำหนักเรียบร้อย")
            click_next_button(main_window, timeout_val)
        except Exception as e:
            log(f"[X] กรอกน้ำหนักไม่ได้: {e}")
    else:
        log("[X] หาช่องกรอกน้ำหนักไม่เจอ")
        print_window_controls(main_window)
        return
    
    time.sleep(step_delay)

    # 5. ใส่รหัสไปรษณีย์
    log(f"STEP 5: กรอกรหัสไปรษณีย์ ({postal_code_val})")
    postal_input = None
    
    # ลองหา Edit Box
    try:
        # ในหน้านี้ Edit Box ตัวแรกมักจะเป็นช่องรหัสไปรษณีย์
        # แต่เพื่อความชัวร์ ลองหา Edit ที่ Active อยู่
        all_edits = main_window.descendants(control_type="Edit")
        if all_edits:
            postal_input = all_edits[0] 
    except: pass

    if postal_input:
        try:
            postal_input.set_focus()
            postal_input.type_keys(postal_code_val)
            log("[/] กรอกรหัสไปรษณีย์เรียบร้อย")
            click_next_button(main_window, timeout_val)
        except:
             log("[X] พิมพ์รหัสไปรษณีย์ไม่ได้")
    else:
        log("[X] หาช่องรหัสไปรษณีย์ไม่เจอ")
        return

    time.sleep(step_delay)

    # 6. กด "ดำเนินการ"
    log("STEP 6: กดปุ่ม 'ดำเนินการ'")
    process_btn = wait_and_find(main_window, "ดำเนินการ", timeout_val, control_type="Button", parent_step="Step6")
    
    if process_btn:
        process_btn.click_input()
        log("[SUCCESS] กดปุ่มดำเนินการสำเร็จ! จบ Scenario")
    else:
        log("[!] ไม่เจอปุ่ม 'ดำเนินการ'")
        main_window.type_keys("{ENTER}")

# ================= 4. Main Execution =================
if __name__ == "__main__":
    config = load_config()
    if config:
        window_title = config['APP']['WindowTitle']
        timeout = int(config['SETTINGS']['ConnectTimeout'])

        log("กำลังเชื่อมต่อกับ Application...")
        try:
            app = Application(backend="uia").connect(title_re=window_title, timeout=timeout)
            main_window = app.top_window()
            main_window.set_focus()
            
            deposit_envelope_scenario(main_window, config)

        except Exception as e:
            log(f"[Error] เชื่อมต่อไม่ได้: {e}")