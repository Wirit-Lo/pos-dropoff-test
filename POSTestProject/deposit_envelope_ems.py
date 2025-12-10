import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    """
    อ่าน Config ให้ตรงกับโครงสร้างในภาพที่คุณส่งมา
    """
    config = configparser.ConfigParser()
    if not os.path.exists(filename): 
        print(f"[Warning] ไม่พบไฟล์ {filename} -> กำลังใช้ค่า Default (จำลองตามภาพ)")
        return {
            'APP': {'WindowTitle': '.*Riposte POS Application.*'},
            'TEST_DATA': {'PhoneNumber': '0899998888'},
            'SETTINGS': {
                'ElementWaitTimeout': '15',
                'ConnectTimeout': '10',
                'ScrollDistance': '-20',
                'StepDelay': '3'
            },
            'DEPOSIT_ENVELOPE': {
                'Weight': '25',
                'PostalCode': '10220',
                'SpecialOptions': 'LQ, FR, LI',
                'AddInsurance': 'True',
                'InsuranceAmount': '1000'
            }
        }
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Helper Functions =================
def force_scroll_down(window, scroll_dist=-20):
    """เลื่อนหน้าจอลง (รับค่าระยะจาก Config)"""
    log(f"...Scrolling Down ({scroll_dist})...")
    try:
        rect = window.rectangle()
        center_x = rect.left + 300
        center_y = rect.top + 300
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.5)
        mouse.scroll(coords=(center_x, center_y), wheel_dist=int(scroll_dist))
        time.sleep(1)
    except:
        window.type_keys("{PGDN}")

def smart_click(window, criteria_list, timeout=5, optional=False):
    """
    คลิกปุ่ม โดยค้นหาจากชื่อ (Text) หรือ Automation ID
    """
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    
    start = time.time()
    while time.time() - start < float(timeout):
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if not child.is_visible(): continue
                    
                    # เช็ค 1: ชื่อตรงไหม?
                    text_match = criteria in child.window_text()
                    # เช็ค 2: Automation ID ตรงไหม?
                    id_match = criteria == child.element_info.automation_id
                    
                    if text_match or id_match:
                        try:
                            child.draw_outline(colour='red') 
                            child.click_input()
                            log(f"[/] Clicked: '{criteria}'")
                            return True
                        except:
                            child.click_input(double=True)
                            log(f"[/] Double Clicked: '{criteria}'")
                            return True
            except: pass
        time.sleep(0.5)

    if not optional:
        log(f"[X] หาปุ่ม {criteria_list} ไม่เจอ (Timeout {timeout}s)")
    return False

# ================= 3. Smart Input Functions =================
def smart_input_weight(window, value, timeout=5):
    log(f"...Input Weight: {value}")
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(value), with_spaces=True)
            return True
    except: pass
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_input_with_scroll(window, label_text, value, scroll_dist=-20):
    log(f"...Input '{label_text}': {value}")
    for i in range(3): 
        # 1. หา Edit Box โดยตรง
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if edit.is_visible() and label_text in edit.window_text():
                    edit.click_input()
                    edit.type_keys(str(value), with_spaces=True)
                    return True
        except: pass

        # 2. หา Label แล้วกด Tab
        try:
            labels = [c for c in window.descendants(control_type="Text") if label_text in c.window_text() and c.is_visible()]
            if labels:
                labels[0].click_input()
                window.type_keys("{TAB}")
                time.sleep(0.2)
                window.type_keys(str(value), with_spaces=True)
                return True
        except: pass
        
        if i < 2:
            force_scroll_down(window, scroll_dist)

    log(f"[X] Failed to input: {label_text}")
    return False

def smart_next(window, timeout=5):
    if not smart_click(window, ["ถัดไป", "Next"], timeout=timeout, optional=True):
        window.type_keys("{ENTER}")

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    # --- 1. Load Variables from Config ---
    # SETTINGS
    step_delay = int(config['SETTINGS'].get('StepDelay', '3'))
    wait_timeout = int(config['SETTINGS'].get('ElementWaitTimeout', '15'))
    scroll_dist = int(config['SETTINGS'].get('ScrollDistance', '-20'))
    
    # DATA
    phone = config['TEST_DATA'].get('PhoneNumber', '0899998888')
    
    # ENVELOPE DETAILS
    c_env = config['DEPOSIT_ENVELOPE']
    weight = c_env.get('Weight', '25')
    postal = c_env.get('PostalCode', '10220')
    options_str = c_env.get('SpecialOptions', '')
    options = [x.strip() for x in options_str.split(',')] if options_str else []
    
    add_insurance = c_env.getboolean('AddInsurance', fallback=False)
    insurance_amt = c_env.get('InsuranceAmount', '0')

    log(f"--- Start Scenario: Phone={phone}, Opts={options}, Ins={add_insurance} ---")
    time.sleep(1)

    # --- 2. Start Process ---
    if not smart_click(main_window, "รับฝากสิ่งของ", timeout=wait_timeout): return
    time.sleep(step_delay)

    # --- 3. Sender Info ---
    # เช็ค Popup ผู้ฝากส่ง
    if smart_click(main_window, "อ่านบัตรประชาชน", timeout=5, optional=True):
        log("[Popup] Sender Info Detected")
        time.sleep(1)
        smart_input_with_scroll(main_window, "หมายเลขโทรศัพท์", phone, scroll_dist)
        smart_next(main_window, timeout=wait_timeout)
    else:
        log("[Popup] No Sender Info popup")

    # --- 4. Select Type ---
    if not smart_click(main_window, "ซองจดหมาย", timeout=wait_timeout): return
    time.sleep(step_delay)

    # --- 5. Special Options ---
    if options:
        log(f"...Selecting Options: {options}")
        for opt in options:
            # ใช้ optional=True เพื่อไม่ให้ error ถ้าหาไม่เจอ
            smart_click(main_window, opt, timeout=3, optional=True)
            time.sleep(0.5)

    # --- 6. Insurance (ประกัน) ---
    if add_insurance:
        log(f"...Adding Insurance: {insurance_amt} Baht")
        # กดปุ่ม + หรือปุ่มที่สื่อถึงการเพิ่มบริการเสริม
        # หมายเหตุ: คุณอาจต้องเปลี่ยน "+" เป็น ID จริงถ้าหาไม่เจอ
        if smart_click(main_window, ["+", "AddService", "รับประกัน"], timeout=3, optional=True):
            time.sleep(1)
            # กรอกวงเงินรับประกัน
            smart_input_with_scroll(main_window, "วงเงิน", insurance_amt, scroll_dist)
            # กดตกลงใน Popup ประกัน (ถ้ามี)
            smart_click(main_window, ["ตกลง", "OK"], timeout=2, optional=True)
        else:
            log("[!] หาปุ่มเพิ่มประกันไม่เจอ")

    # กด Enter/Next เพื่อผ่านหน้านี้
    log("...Proceeding to Weight...")
    main_window.type_keys("{ENTER}") 
    time.sleep(step_delay)

    # --- 7. Weight ---
    smart_input_weight(main_window, weight, timeout=wait_timeout)
    smart_next(main_window, timeout=wait_timeout)
    
    # --- 8. Postal Code ---
    time.sleep(1)
    smart_input_with_scroll(main_window, "รหัสไปรษณีย์", postal, scroll_dist)
    smart_next(main_window, timeout=wait_timeout)
    time.sleep(step_delay)

    # --- 9. Finish ---
    log("...Finishing...")
    if smart_click(main_window, ["ดำเนินการ", "Process"], timeout=wait_timeout, optional=True):
        log("Processing...")
    
    smart_click(main_window, ["เสร็จสิ้น", "Settle", "ตกลง", "Confirm"], timeout=wait_timeout, optional=True)
    main_window.type_keys("{ENTER}")
    log("[SUCCESS] Job Done.")

# ================= 5. Execution =================
if __name__ == "__main__":
    conf = load_config()
    
    # อ่านค่า Window Title จาก Config
    app_title_regex = conf['APP'].get('WindowTitle', '.*Riposte POS Application.*')
    connect_timeout = int(conf['SETTINGS'].get('ConnectTimeout', '10'))

    log(f"Connecting to: '{app_title_regex}' (Timeout {connect_timeout}s)...")
    try:
        app = Application(backend="uia").connect(title_re=app_title_regex, found_index=0, timeout=connect_timeout)
        win = app.top_window()
        win.set_focus()
        
        run_smart_scenario(win, conf)
        
    except Exception as e:
        log(f"[Error] Connect Failed: {e}")
        log("Tip: โปรดตรวจสอบว่าเปิดโปรแกรม POS แล้ว และชื่อ Title ตรงกับ Regex ใน Config")