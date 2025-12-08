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
        descendants = window.descendants()
        for i, child in enumerate(descendants):
            name = child.window_text()
            control_type = child.element_info.control_type
            if name and child.is_visible():
                print(f"  {i+1}. Name: '{name}' | Type: {control_type}")
    except Exception as e:
        print(f"  [Error displaying controls]: {e}")
    log("[DEBUG] ------------------------------------------------\n")

def find_element_deep(window, text_criteria):
    """
    ค้นหาแบบเจาะลึก (Deep Search)
    วนลูปหาทุก Element ในหน้าจอว่ามีตัวไหนชื่อตรงกับ text_criteria ไหม
    """
    try:
        descendants = window.descendants()
        for child in descendants:
            if child.window_text() == text_criteria and child.is_visible():
                return child
    except:
        pass
    return None

def wait_and_find(root_window, criteria, timeout, control_type=None, parent_step="Unknown"):
    """ฟังก์ชันช่วยค้นหาปุ่มหรือข้อความ (รองรับทั้งแบบปกติและ Deep Search)"""
    start_time = time.time()
    element = None
    
    # 1. ลองหาแบบปกติ (Standard Search)
    while time.time() - start_time < timeout:
        try:
            if control_type:
                temp = root_window.child_window(title=criteria, control_type=control_type)
            else:
                temp = root_window.child_window(title=criteria)
            
            if temp.exists():
                element = temp
                break
        except:
            pass
        time.sleep(0.5)

    # 2. ถ้าไม่เจอ ลองหาแบบเจาะลึก (Deep Search)
    if not element:
        # log(f"...หาแบบปกติไม่เจอ กำลังลอง Deep Search หา '{criteria}'...")
        element = find_element_deep(root_window, criteria)

    return element

def click_next_button(window, timeout):
    """ฟังก์ชันกดปุ่ม 'ถัดไป' (Next)"""
    log("...กำลังหาปุ่ม 'ถัดไป'...")
    btn = wait_and_find(window, "ถัดไป", timeout, control_type="Button", parent_step="ClickNext")
    if not btn:
         btn = wait_and_find(window, "ถัดไป", timeout, control_type="Text", parent_step="ClickNext_Retry")

    if btn:
        btn.click_input()
        log("[/] กดปุ่ม 'ถัดไป' สำเร็จ")
        return True
    else:
        log("[!] หาปุ่มถัดไปไม่เจอ -> ลองกด Enter แทน")
        window.type_keys("{ENTER}")
        return False

# ================= 3. Deposit Scenario Logic (1-6 Steps) =================
def deposit_envelope_scenario(main_window, config):
    try:
        weight_val = config['DEPOSIT_ENVELOPE']['Weight']
        postal_code_val = config['DEPOSIT_ENVELOPE']['PostalCode']
    except KeyError:
        log("[ERROR] ไม่พบค่าใน Config (Section [DEPOSIT_ENVELOPE])")
        return
    
    timeout_val = int(config['SETTINGS']['ElementWaitTimeout'])
    step_delay = int(config['SETTINGS']['StepDelay'])

    log(f"\n--- เริ่มต้น Scenario: รับฝากสิ่งของ (ซองจดหมาย) ---")
    log(f"ข้อมูล: น้ำหนัก {weight_val}g | ปณ. {postal_code_val}")
    time.sleep(1)

    # ---------------------------------------------------------
    # 1. รับฝากสิ่งของ
    # ---------------------------------------------------------
    log("STEP 1: เลือกเมนู 'รับฝากสิ่งของ'")
    btn_step1 = wait_and_find(main_window, "รับฝากสิ่งของ", timeout=5, parent_step="Step1")
    
    if btn_step1:
        # คลิกปุ่ม
        try:
            btn_step1.click_input()
        except:
            # ถ้าคลิกตรงกลางไม่ได้ ลอง Double Click
            btn_step1.click_input(double=True)
        log("[/] เจอและกดเมนู 'รับฝากสิ่งของ' แล้ว")
    else:
        log("[X] ไม่เจอเมนู 'รับฝากสิ่งของ' (ลองเช็คชื่อปุ่ม หรือ Deep Search แล้วไม่พบ)")
        print_window_controls(main_window) # Debug ชื่อปุ่ม
        return
        
    time.sleep(step_delay)

    # ---------------------------------------------------------
    # 2. ซองจดหมาย (รูปร่าง)
    # ---------------------------------------------------------
    log("STEP 2: เลือกรูปร่าง 'ซองจดหมาย'")
    btn_step2 = wait_and_find(main_window, "ซองจดหมาย", timeout=5, parent_step="Step2")
    
    if btn_step2:
        try:
            btn_step2.click_input()
        except:
             btn_step2.click_input(double=True)
        log("[/] เลือกรูปร่าง 'ซองจดหมาย' สำเร็จ")
    else:
        log("[X] ไม่เจอตัวเลือก 'ซองจดหมาย' (Step 2)")
        print_window_controls(main_window)
        return
    time.sleep(step_delay)

    # ---------------------------------------------------------
    # 3. ซองจดหมาย (หมวดหมู่)
    # ---------------------------------------------------------
    log("STEP 3: เลือกหมวดหมู่ 'ซองจดหมาย' อีกครั้ง")
    # บางครั้งหน้าจออาจจะยังไม่เปลี่ยน หรือมี Element ชื่อเดิม
    # ลองหาซ้ำ (ถ้าหน้าจอเปลี่ยนแล้ว ID ของปุ่มใหม่จะต่างจากเดิม)
    btn_step3 = wait_and_find(main_window, "ซองจดหมาย", timeout=5, parent_step="Step3")
    
    if btn_step3:
        try:
            btn_step3.click_input()
            log("[/] เลือกหมวดหมู่ 'ซองจดหมาย' สำเร็จ")
        except:
            pass 
    else:
        log("[!] ไม่เจอตัวเลือก 'ซองจดหมาย' ใน Step 3 (อาจจะข้ามขั้นตอนนี้?)")
    
    time.sleep(step_delay)

    # ---------------------------------------------------------
    # 4. ใส่น้ำหนัก
    # ---------------------------------------------------------
    log(f"STEP 4: กรอกน้ำหนัก ({weight_val} กรัม)")
    weight_input = None
    
    # 4.1 หาจากชื่อ "น้ำหนัก"
    weight_input = wait_and_find(main_window, "น้ำหนัก", 3, control_type="Edit", parent_step="Step4")
    
    # 4.2 ถ้าไม่เจอชื่อ ให้หา Edit Box ตัวแรก
    if not weight_input:
        try:
             all_edits = main_window.descendants(control_type="Edit")
             # กรองเอาเฉพาะตัวที่มองเห็น (Visible)
             visible_edits = [e for e in all_edits if e.is_visible()]
             if visible_edits:
                 weight_input = visible_edits[0]
                 log("...ใช้ Edit Box ตัวแรกสำหรับการกรอกน้ำหนัก...")
        except: pass

    if weight_input:
        try:
            weight_input.set_focus()
            weight_input.type_keys(weight_val)
            log("[/] กรอกน้ำหนักเรียบร้อย")
            # กดถัดไปเพื่อไปหน้าต่อไป
            click_next_button(main_window, timeout_val)
        except Exception as e:
            log(f"[X] กรอกน้ำหนักไม่ได้: {e}")
    else:
        log("[X] หาช่องกรอกน้ำหนักไม่เจอ")
        return
    
    time.sleep(step_delay)

    # ---------------------------------------------------------
    # 5. รหัสไปรษณีย์
    # ---------------------------------------------------------
    log(f"STEP 5: กรอกรหัสไปรษณีย์ ({postal_code_val})")
    postal_input = None
    
    try:
        # หา Edit Box ตัวแรกในหน้านี้ (มักจะเป็นช่องป้อนรหัส)
        all_edits = main_window.descendants(control_type="Edit")
        visible_edits = [e for e in all_edits if e.is_visible()]
        if visible_edits:
            postal_input = visible_edits[0] 
    except: pass

    if postal_input:
        try:
            postal_input.set_focus()
            postal_input.type_keys(postal_code_val)
            log("[/] กรอกรหัสไปรษณีย์เรียบร้อย")
            # กดถัดไป
            click_next_button(main_window, timeout_val)
        except:
             log("[X] พิมพ์รหัสไปรษณีย์ไม่ได้")
    else:
        log("[X] หาช่องรหัสไปรษณีย์ไม่เจอ")
        return

    time.sleep(step_delay)

    # ---------------------------------------------------------
    # 6. ดำเนินการ (Enter)
    # ---------------------------------------------------------
    log("STEP 6: ดำเนินการ (กดปุ่ม หรือ Enter)")
    
    # พยายามหาปุ่ม "ดำเนินการ" ก่อน
    process_btn = wait_and_find(main_window, "ดำเนินการ", timeout=3, control_type="Button", parent_step="Step6")
    
    if process_btn:
        process_btn.click_input()
        log("[SUCCESS] กดปุ่ม 'ดำเนินการ' สำเร็จ")
    else:
        # ถ้าหาปุ่มไม่เจอ ให้กด Enter ตามที่ระบุมา
        log("[!] ไม่เจอปุ่ม 'ดำเนินการ' -> สั่งกด Enter")
        main_window.type_keys("{ENTER}")
        log("[SUCCESS] ส่งคำสั่ง Enter เรียบร้อย")

    log("\n[--- จบการทำงาน ---]")

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