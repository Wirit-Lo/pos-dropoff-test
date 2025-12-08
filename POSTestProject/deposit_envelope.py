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
        log(f"[Wait] ยังไม่เจอ '{criteria}' (Step: {parent_step}) - กำลังรอ...")
        return None

def click_next_button(window, timeout):
    """ฟังก์ชันกดปุ่ม 'ถัดไป' (Next)"""
    log("...กำลังหาปุ่ม 'ถัดไป'...")
    btn = wait_and_find(window, "ถัดไป", timeout, control_type="Button", parent_step="ClickNext")
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
    weight_val = config['DEPOSIT_ENVELOPE']['Weight']
    postal_code_val = config['DEPOSIT_ENVELOPE']['PostalCode']
    
    # ค่า Setting ทั่วไป
    timeout_val = int(config['SETTINGS']['ElementWaitTimeout'])
    step_delay = int(config['SETTINGS']['StepDelay'])

    log(f"\n--- เริ่มต้น Scenario: รับฝากสิ่งของ (ซองจดหมาย) ---")
    log(f"ข้อมูลทดสอบ: น้ำหนัก {weight_val}g / ปณ. {postal_code_val}")
    time.sleep(1)

    # 1. กดเมนู "รับฝากสิ่งของ"
    log("STEP 1: เลือกเมนู 'รับฝากสิ่งของ'")
    btn_step1 = wait_and_find(main_window, "รับฝากสิ่งของ", timeout_val, parent_step="Step1")
    if btn_step1:
        btn_step1.click_input()
    else:
        log("[X] ไม่เจอเมนู 'รับฝากสิ่งของ' -> จบการทำงาน")
        return
    time.sleep(step_delay)

    # 2. กดเลือก "ซองจดหมาย" (ครั้งที่ 1 - รูปร่าง)
    log("STEP 2: เลือกรูปร่าง 'ซองจดหมาย'")
    btn_step2 = wait_and_find(main_window, "ซองจดหมาย", timeout_val, parent_step="Step2")
    if btn_step2:
        btn_step2.click_input()
    else:
        log("[X] ไม่เจอตัวเลือก 'ซองจดหมาย' (Step 2)")
        return
    time.sleep(step_delay)

    # 3. กดเลือก "ซองจดหมาย" (ครั้งที่ 2 - หมวดหมู่)
    log("STEP 3: เลือกหมวดหมู่ 'ซองจดหมาย' อีกครั้ง")
    # บางทีชื่อซ้ำกัน อาจต้องระบุ control_type หรือ index ถ้าโค้ดสับสน แต่ลองหาแบบปกติดูก่อน
    btn_step3 = wait_and_find(main_window, "ซองจดหมาย", timeout_val, parent_step="Step3")
    if btn_step3:
        # อาจต้อง Double Click หรือคลิกตัวใหม่ที่เพิ่งโผล่มา
        try:
            btn_step3.click_input()
        except:
            pass # ถ้าคลิกแล้ว error แสดงว่าอาจเป็น element เดิม ให้ปล่อยผ่านไป
    else:
        log("[!] ไม่เจอตัวเลือก 'ซองจดหมาย' ใน Step 3 (อาจจะข้ามขั้นตอนนี้?)")
    
    # มักจะมีปุ่ม "ถัดไป" หรือมันจะเปลี่ยนหน้าเอง ลองรอก่อน
    time.sleep(step_delay)

    # 4. ใส่น้ำหนัก
    log(f"STEP 4: กรอกน้ำหนัก ({weight_val} กรัม)")
    # หาช่องกรอกน้ำหนัก (มักจะเป็น Edit Box ตัวแรก หรือชื่อ 'น้ำหนัก')
    weight_input = main_window.child_window(control_type="Edit") 
    # หรือถ้ามีชื่อเฉพาะ: main_window.child_window(title="น้ำหนัก", control_type="Edit")
    
    if weight_input.exists(timeout=timeout_val):
        weight_input.set_focus()
        weight_input.type_keys(weight_val)
        log("[/] กรอกน้ำหนักเรียบร้อย")
        
        # กดถัดไป เพื่อไปหน้า รหัสไปรษณีย์
        click_next_button(main_window, timeout_val)
    else:
        log("[X] หาช่องกรอกน้ำหนักไม่เจอ")
        return
    
    time.sleep(step_delay)

    # 5. ใส่รหัสไปรษณีย์
    log(f"STEP 5: กรอกรหัสไปรษณีย์ ({postal_code_val})")
    # หาช่องกรอก (เดาว่าเป็น Edit Box ที่โผล่มาใหม่)
    # ในหน้านี้อาจจะมี Edit Box ตัวเดียวที่ Active
    postal_input = None
    
    # ลองหาจากชื่อ "รหัสไปรษณีย์" ก่อน (ถ้าแอปตั้งชื่อไว้)
    temp_input = wait_and_find(main_window, "รหัสไปรษณีย์", 3, control_type="Edit", parent_step="Step5_FindName")
    
    if temp_input:
        postal_input = temp_input
    else:
        # ถ้าหาชื่อไม่เจอ ให้หา Edit Box ตัวแรกในหน้านี้แทน
        log("...หาชื่อไม่เจอ ลองหา Edit Box ช่องแรก...")
        postal_input = main_window.child_window(control_type="Edit")

    if postal_input and postal_input.exists(timeout=timeout_val):
        postal_input.set_focus()
        postal_input.type_keys(postal_code_val)
        log("[/] กรอกรหัสไปรษณีย์เรียบร้อย")
        
        # กดถัดไป หรือ Enter เพื่อให้ Popup เด้ง (ถ้ามี)
        click_next_button(main_window, timeout_val)
    else:
        log("[X] หาช่องรหัสไปรษณีย์ไม่เจอ")
        return

    time.sleep(step_delay)

    # 6. กด "ดำเนินการ" (ใน Popup หรือปุ่มสุดท้าย)
    log("STEP 6: กดปุ่ม 'ดำเนินการ'")
    
    # รอ Popup หรือปุ่มดำเนินการ
    process_btn = wait_and_find(main_window, "ดำเนินการ", timeout_val, control_type="Button", parent_step="Step6")
    
    if process_btn:
        process_btn.click_input()
        log("[SUCCESS] กดปุ่มดำเนินการสำเร็จ! จบ Scenario")
    else:
        log("[!] ไม่เจอปุ่ม 'ดำเนินการ' (อาจไม่มี Popup แจ้งเตือนทับซ้อน?)")
        # ลองกด Enter เผื่อปิดงาน
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