import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Configuration Management =================
def load_config(filename='config.ini'):
    """โหลดค่าจาก Config File"""
    config = configparser.ConfigParser()
    # ตรวจสอบว่ามีไฟล์ config.ini อยู่จริงหรือไม่
    if not os.path.exists(filename):
        print(f"[ERROR] ไม่พบไฟล์ {filename} กรุณาสร้างไฟล์นี้ไว้ในโฟลเดอร์เดียวกับโปรแกรม")
        return None
    # อ่านไฟล์โดยรองรับภาษาไทย (utf-8)
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    """ฟังก์ชันช่วยปรินท์ Log พร้อมเวลาปัจจุบัน"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

# ================= 2. Helper Functions (ฟังก์ชันช่วยค้นหาและควบคุม) =================
def wait_and_find(root_window, criteria, timeout, control_type=None, parent_step="Unknown"):
    """
    ค้นหา Element บนหน้าจอ โดยมีการรอ (Wait) ตาม Timeout ที่กำหนดใน Config
    """
    try:
        if control_type:
            # ค้นหาโดยระบุประเภทของ Control (เช่น Button, Edit, ListItem)
            element = root_window.child_window(title=criteria, control_type=control_type)
        else:
            # ค้นหาจากชื่อ (Title) อย่างเดียว
            element = root_window.child_window(title=criteria)
        
        # รอให้ Element ปรากฏขึ้นมา
        element.wait('exists', timeout=timeout)
        return element
    except Exception:
        log(f"[X] หา Element '{criteria}' ไม่เจอในขั้นตอน '{parent_step}' (Timeout {timeout}s)")
        return None

def find_edit_by_name_manual(window, name_criteria):
    """
    ฟังก์ชันสำรอง: ค้นหาช่องกรอกข้อมูล (Edit Box) แบบวนลูปเช็คชื่อทีละตัว
    ใช้เมื่อการค้นหาปกติหาไม่เจอ
    """
    log(f"...กำลังสแกนหาช่องกรอกข้อมูลที่มีชื่อว่า '{name_criteria}'...")
    try:
        # ดึงรายการ Edit Box ทั้งหมดในหน้าจอ
        edits = window.descendants(control_type="Edit")
        if not edits:
            return None

        for i, edit in enumerate(edits):
            try:
                edit_name = edit.element_info.name
                # ถ้าชื่อตรงกับที่เราหา และช่องนั้นมองเห็นได้ (Visible)
                if edit_name and name_criteria in edit_name:
                    if edit.is_visible():
                        log(f"[/] เจอช่องที่ใช้งานได้! Edit Box ลำดับที่ {i+1} ชื่อ '{edit_name}'")
                        return edit
            except:
                continue
    except Exception as e:
        log(f"[X] Error while scanning descendants: {e}")
    return None

def force_scroll_down(window, scroll_dist):
    """
    ฟังก์ชันช่วยเลื่อนหน้าจอลง (Scroll) โดยใช้ Mouse Wheel
    ค่า scroll_dist ติดลบ = เลื่อนลง
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

# ================= 3. Main Scenario (ขั้นตอนการเทส) =================
def drop_off_scenario(main_window, config):
    """
    Scenario: Drop Off โดยอ่านค่า Parameter ต่างๆ จาก Config
    """
    # 1. ดึงค่า Setting ต่างๆ มาจากตัวแปร config
    phone_number = config['TEST_DATA']['PhoneNumber']
    timeout_val = int(config['SETTINGS']['ElementWaitTimeout'])
    scroll_val = int(config['SETTINGS']['ScrollDistance'])
    step_delay = int(config['SETTINGS']['StepDelay'])

    log(f"\n--- เริ่มต้น Scenario: Drop Off (Tel: {phone_number}) ---")
    time.sleep(1) 

    # --- STEP 1: กดปุ่ม Drop Off ---
    log("STEP 1: ค้นหาเมนู 'Drop Off'")
    # ลองหาแบบ ListItem ก่อน
    drop_off_btn = wait_and_find(main_window, "Drop Off", timeout=timeout_val, control_type="ListItem", parent_step="Step1")
    # ถ้าไม่เจอ ลองหาแบบ Text ธรรมดา
    if not drop_off_btn:
        drop_off_btn = wait_and_find(main_window, "Drop Off", timeout=timeout_val, control_type="Text", parent_step="Step1_Retry")

    if drop_off_btn:
        try:
            drop_off_btn.click_input()
            log("[/] กดปุ่ม Drop Off สำเร็จ")
        except:
            # ถ้าคลิกครั้งเดียวไม่ไป ลอง Double Click
            drop_off_btn.click_input(double=True)
            log(f"[/] (Retry) กดปุ่ม Drop Off สำเร็จ")
    else:
        log("[X] หาปุ่ม Drop Off ไม่เจอ -> จบการทำงาน")
        return 

    # รอหน่วงเวลาตาม Config
    time.sleep(step_delay)

    # --- STEP 2: กดปุ่ม อ่านบัตรประชาชน ---
    log("STEP 2: กดปุ่ม 'อ่านบัตรประชาชน'")
    read_id_btn = wait_and_find(main_window, "อ่านบัตรประชาชน", timeout=timeout_val, control_type="Button", parent_step="Step2")
    
    if read_id_btn:
        read_id_btn.click_input()
        log("[/] กดปุ่ม อ่านบัตรประชาชน สำเร็จ")
        time.sleep(2) 
    else:
        log("[!] ไม่เจอปุ่มอ่านบัตรประชาชน (โปรแกรมอาจจะข้ามขั้นตอนนี้ หรือหาปุ่มไม่เจอ)")

    # --- STEP 2.5: เลื่อนหน้าจอลง (Scroll) ---
    # บางครั้งช่องกรอกเบอร์อยู่ด้านล่าง ต้องเลื่อนจอก่อน
    log("STEP 2.5: เลื่อนหน้าจอลง")
    force_scroll_down(main_window, scroll_dist=scroll_val) 

    # --- STEP 3: กรอกเบอร์โทรศัพท์ ---
    log(f"STEP 3: ค้นหาช่องและกรอกเบอร์โทรศัพท์ '{phone_number}'")
    
    phone_input = None
    # วิธีที่ 1: หาตรงๆ ด้วย Title
    try:
        temp_input = main_window.child_window(title="หมายเลขโทรศัพท์", control_type="Edit")
        if temp_input.exists(timeout=2) and temp_input.is_visible():
            phone_input = temp_input
            log("[/] เจอช่องแบบปกติ (Visible)")
    except:
        pass
    
    # วิธีที่ 2: ถ้าหาไม่เจอ ใช้ฟังก์ชันช่วยสแกนหา
    if not phone_input:
        phone_input = find_edit_by_name_manual(main_window, "หมายเลขโทรศัพท์")

    if phone_input:
        try:
            phone_input.set_focus()
            phone_input.click_input()
            time.sleep(0.5)
            
            # พยายามกรอกข้อมูล
            try:
                # ลองใช้ set_text (เร็วและแม่นยำกว่า)
                phone_input.set_text(phone_number)
                log("[/] กรอกสำเร็จด้วย set_text")
            except:
                # ถ้าไม่ได้ ให้ใช้การพิมพ์ทีละตัว (type_keys)
                phone_input.type_keys(phone_number, with_spaces=True)
                log("[/] สั่งพิมพ์ type_keys เรียบร้อย")
        except Exception as e:
            log(f"[X] Error ตอนกรอกเบอร์: {e}")
    else:
        log("[X] หาช่อง 'หมายเลขโทรศัพท์' ไม่เจอ -> จบการทำงาน")
        return

    time.sleep(1)

    # --- STEP 4: กดปุ่ม ถัดไป ---
    log("STEP 4: กดปุ่ม 'ถัดไป'")
    next_btn = wait_and_find(main_window, "ถัดไป", timeout=timeout_val, control_type="Button", parent_step="Step4")

    if next_btn:
        next_btn.click_input()
        log("[/] กดปุ่ม 'ถัดไป' สำเร็จ")
    else:
        # ถ้าหาปุ่มไม่เจอ ลองกด Enter
        log("[!] หาปุ่ม 'ถัดไป' ไม่เจอ - ลองกด Enter")
        main_window.type_keys("{ENTER}")

    log("\n[SUCCESS] จบการทดสอบ Drop Off Scenario")

# ================= 4. Main Execution (จุดเริ่มต้นโปรแกรม) =================
if __name__ == "__main__":
    # 1. โหลด Config
    config = load_config()
    
    if config:
        # ดึงค่า Title และ Timeout จาก Config
        window_title_regex = config['APP']['WindowTitle']
        connect_timeout = int(config['SETTINGS']['ConnectTimeout'])

        log("กำลังเชื่อมต่อกับ Application...")
        try:
            # เชื่อมต่อกับแอปพลิเคชัน
            app = Application(backend="uia").connect(title_re=window_title_regex, timeout=connect_timeout)
            main_window = app.top_window()
            main_window.set_focus()
            
            log(f"[/] เชื่อมต่อสำเร็จ: {main_window.window_text()}")
            
            # เริ่มรัน Scenario
            drop_off_scenario(main_window, config)

        except Exception as e:
            log(f"[X] ไม่สามารถเชื่อมต่อกับโปรแกรมได้ (Title: {window_title_regex}): {e}")
            print("\nคำแนะนำ: ตรวจสอบชื่อ WindowTitle ในไฟล์ config.ini ให้ตรงกับ Title Bar ของโปรแกรม POS")