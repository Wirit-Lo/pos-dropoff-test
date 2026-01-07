import configparser
import os
import time
from pywinauto.application import Application

# --- ดึงฟังก์ชันจากไฟล์ helpers.py มาใช้ ---
from helpers import (
    log,
    wait_for_text,
    wait_until_id_appears,
    smart_click,
    click_element_by_id,
    find_and_fill_smart,
    smart_next,
    wait_for_text,
    fill_receiver_details_with_sms,
    find_and_click_with_rotate_logic,
    handle_sms_step,
    fill_amount_and_destination
)

def load_config(filename='config.ini'):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    config = configparser.ConfigParser()
    if not os.path.exists(file_path): 
        print(f"[Error] ไม่พบไฟล์ Config ที่: {file_path}")
        return None
    config.read(file_path, encoding='utf-8')
    return config

# ================= 3. Business Logic Functions (Updated) =================

def process_sender_info_popup(window, phone, sender_postal):
    """จัดการหน้าข้อมูลผู้ส่งแบบ Safe Mode (รอจนกว่าจะพร้อม)"""
    
    # 1. รอให้หน้า Popup ขึ้นมาก่อน (สังเกตจากคำว่า 'ที่อยู่' หรือ 'รหัสไปรษณีย์')
    wait_for_text(window, ["ที่อยู่", "รหัสไปรษณีย์", "ข้อมูลผู้ส่ง"])
    
    # กดปุ่มอ่านบัตรประชาชน
    if smart_click(window, "อ่านบัตรประชาชน", timeout=5): 
        # รอให้ระบบอ่านบัตร (เพิ่มเวลาตรงนี้เผื่อเครื่องช้า)
        log("...กำลังอ่านบัตรและโหลดข้อมูล (รอ 5s)...")
        time.sleep(5.0) 

        # 1. กรอกรหัสไปรษณีย์ (ฟังก์ชันนี้จะวนรอจนกว่าช่องจะโผล่และพิมพ์ได้)
        find_and_fill_smart(window, "รหัสไปรษณีย์", "PostalCode", sender_postal)
        
        # 2. กรอกเบอร์โทรศัพท์ (ฟังก์ชันนี้จะวนรอจนกว่าช่องจะโผล่)
        if not find_and_fill_smart(window, "เบอร์โทรศัพท์", "PhoneNumber", phone):
            # Fallback
            find_and_fill_smart(window, "หมายเลขโทรศัพท์", "Phone", phone, timeout=5)
        
        # รอให้แน่ใจว่าข้อมูลลงครบ
        time.sleep(1.0)
        smart_next(window)

def process_payment(window, payment_method, received_amount):
    """
    ฟังก์ชันชำระเงินแบบ Fast Cash (ไม่มีเงินทอน)
    - ปรับปรุง: เพิ่มระบบรอปุ่ม (Wait) เพื่อความแม่นยำ
    """
    # ใช้ตัวแปร log เพื่อให้ Python รู้ว่าเราใช้ค่าที่ส่งมาแล้ว (กันสีจาง/Error)
    log(f"--- ขั้นตอนการชำระเงิน: วิธี '{payment_method}' | ยอด: '{received_amount}' (โหมด Fast Cash) ---")
    
    # 1. กดรับเงิน (หน้าหลัก)
    log("...กำลังค้นหาปุ่ม 'รับเงิน'...")
    
    wait_for_text(window, "รับเงิน")
    time.sleep(1.0) # รอ Animation นิ่งสนิท
    
    # กดปุ่ม
    if smart_click(window, "รับเงิน"):
        log("...กดปุ่มรับเงินสำเร็จ -> รอโหลดหน้าชำระเงิน...")
        
        # รอให้ปุ่ม Fast Cash (ID: EnableFastCash) 
        if not wait_until_id_appears(window, "EnableFastCash"):
            log("[WARN] รอนานเกินไป หน้าชำระเงินไม่โหลด")
            return
            
        time.sleep(1.0) 
    else:
        log("[WARN] หาปุ่ม 'รับเงิน' ไม่เจอ")
        return

    # 2. กดปุ่ม Fast Cash (ID: EnableFastCash)
    log("...กำลังกดปุ่ม Fast Cash (อันที่ 2 แบบไม่มีเงินทอน)...")
    
    # ใช้ ID: EnableFastCash 
    if click_element_by_id(window, "EnableFastCash", timeout=5):
        log("[/] กดปุ่ม Fast Cash สำเร็จ -> ระบบตัดเงินทันที")
    else:
        log("[WARN] กดปุ่ม Fast Cash ไม่ติด -> ลองกด Enter ช่วย")
        window.type_keys("{ENTER}")

    # 3. จบรายการ
    log("...รอหน้าสรุป/เงินทอน -> กด Enter ปิดรายการ...")
    time.sleep(2.0) # รอ Animation ใบเสร็จเด้ง
    window.type_keys("{ENTER}")
    time.sleep(1)

def process_sender_info_popup(window, phone, sender_postal):
    """จัดการหน้าข้อมูลผู้ส่ง: กดอ่านบัตร -> เติมรหัสปณ. -> เติมเบอร์โทร"""
    
    # กดปุ่มอ่านบัตรประชาชนเพื่อดึงข้อมูล (หรือเพื่อให้แน่ใจว่าโฟกัสหน้านี้)
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3): 
        time.sleep(1.5) 

        # 1. กรอกรหัสไปรษณีย์ (ถ้ายังว่างอยู่)
        # ใช้ find_and_fill_smart ช่วยหาทั้ง "รหัสไปรษณีย์" หรือ ID ที่เกี่ยวข้อง
        find_and_fill_smart(window, "รหัสไปรษณีย์", "PostalCode", sender_postal)

        # 2. กรอกเบอร์โทรศัพท์ [จุดที่แก้ไข]
        # เปลี่ยนคำค้นหาเป็น "เบอร์โทรศัพท์" ตามที่ปรากฏในรูปภาพ
        if not find_and_fill_smart(window, "เบอร์โทรศัพท์", "PhoneNumber", phone):
            # Fallback: ถ้าหาไม่เจอ ลองหาคำว่า "โทรศัพท์" หรือ "หมายเลขโทรศัพท์" เผื่อไว้
            if not find_and_fill_smart(window, "โทรศัพท์", "Phone", phone):
                find_and_fill_smart(window, "หมายเลขโทรศัพท์", "Phone", phone)
        
        # กดถัดไป
        smart_next(window)

def process_payment(window, payment_method, received_amount):
    """(แก้ไข) รับ Argument ให้ครบ 3 ตัว ตามที่เรียกใช้"""
    log("--- ขั้นตอนการชำระเงิน (โหมด Fast Cash) ---")
    
    # รอจนกว่าปุ่ม 'รับเงิน' จะโผล่มา
    wait_for_text(window, "รับเงิน")
    time.sleep(1.0) # รอ Animation หยุด
    
    if smart_click(window, "รับเงิน"):
        # รอเข้าหน้า Fast Cash
        wait_until_id_appears(window, "EnableFastCash")
        time.sleep(1.0)
    else:
        log("[WARN] หาปุ่ม 'รับเงิน' ไม่เจอ")
        return

    log("...กดปุ่ม Fast Cash...")
    if click_element_by_id(window, "EnableFastCash", timeout=5):
        log("[/] ชำระเงินสำเร็จ")
    else:
        window.type_keys("{ENTER}")

    # รอหน้าสรุป
    time.sleep(2.0)
    window.type_keys("{ENTER}")
    time.sleep(1)

# ================= 4. Workflow Main (Safe Mode) =================
def run_smart_scenario(main_window, config):
    try:
        # อ่าน Config (ส่วนเดิม)
        sender_postal = config['TEST_DATA'].get('SenderPostalCode', '10110')
        sender_phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        mo_config = config['MONEY_ORDER'] if 'MONEY_ORDER' in config else {}
        raw_sms = mo_config.get('SendSMS', 'No').lower()
        send_sms = True if raw_sms in ['yes', 'true', '1', 'on'] else False
        receiver_phone = mo_config.get('ReceiverPhone', '')
        amount = mo_config.get('Amount', '100')
        dest_postal = mo_config.get('DestinationPostalCode', '10110')
        rcv_fname = mo_config.get('ReceiverFirstName', 'TestName')
        rcv_lname = mo_config.get('ReceiverLastName', 'TestLast')
        options_str = mo_config.get('Options', '')
        pay_method = config['PAYMENT'].get('Method', 'เงินสด') if 'PAYMENT' in config else 'เงินสด'
        pay_amount = config['PAYMENT'].get('ReceivedAmount', '1000') if 'PAYMENT' in config else '1000'
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))
    except Exception as e: 
        log(f"[Error] อ่าน Config ไม่สำเร็จ: {e}")
        return

    log("--- เริ่มต้นการทำงาน (โหมดปลอดภัย: รอทุกขั้นตอน) ---")
    time.sleep(1.0)

    # Step 1: เลือกเมนู "ธนาณัติในประเทศ"
    # ใช้ smart_click ซึ่งมีระบบรออยู่แล้ว (timeout=5)
    if not smart_click(main_window, "ธนาณัติในประเทศ"): 
        log("[Error] หาเมนูไม่เจอ")
        return
    time.sleep(step_delay)

    # Step 2: เลือกเมนู "รับฝากธนาณัติ"
    if not smart_click(main_window, "รับฝากธนาณัติ"): return
    time.sleep(step_delay)

    # Step 3: เลือกบริการ
    # Step 3: เลือกบริการ
    target_service_id = "PayOutDomesticSendMoneyExpress401"
    
    # [แก้ไข] เปลี่ยนจากรอ ShippingServiceList เป็นรอปุ่มบริการโดยตรง
    # จะได้ไม่รอเก้อ 10 วินาที ถ้าปุ่มมาแล้วก็กดเลย
    wait_until_id_appears(main_window, target_service_id)
    
    if not find_and_click_with_rotate_logic(main_window, target_service_id):
        log(f"[Error] ไม่เจอปุ่มบริการ {target_service_id}")
        return
    time.sleep(step_delay)

    # Step 4: Popup ข้อมูลผู้ส่ง
    # (ใช้ฟังก์ชันใหม่ที่เขียนรอไว้แล้ว)
    process_sender_info_popup(main_window, sender_phone, sender_postal)
    
    # Step 5
    if not fill_amount_and_destination(main_window, amount, dest_postal):
        return # ถ้ากรอกไม่สำเร็จ (False) ให้หยุดโปรแกรมทันที

    # กดถัดไป
    smart_next(main_window)
    time.sleep(step_delay)

   # Step 6: หน้ายอดเงินที่ส่ง กดถัดไป
    handle_sms_step(main_window, send_sms)
    # กดถัดไป
    smart_next(main_window)
    time.sleep(step_delay)

    # Step 7: หน้าข้อมูลผู้ส่ง (ยืนยัน)
    # รอให้ Header ขึ้น
    wait_for_text(main_window, ["ผู้ฝากส่ง", "ข้อมูลผู้ส่ง"])
    smart_next(main_window)
    time.sleep(step_delay)

    # Step 8: หน้าข้อมูลผู้รับ
    fill_receiver_details_with_sms(main_window, rcv_fname, rcv_lname, send_sms, receiver_phone)
    smart_next(main_window)
    time.sleep(step_delay)

    # Step 9-10: รับเงิน (ใช้ฟังก์ชันที่เขียนรอไว้แล้ว)
    process_payment(main_window, pay_method, pay_amount)

    log("\n[SUCCESS] จบการทำงานธนาณัติครบทุกขั้นตอน")

# ================= 5. Start App =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app_title = conf['APP']['WindowTitle']
            log(f"Connecting to Title: {app_title} (Wait: {wait}s)")
            app = Application(backend="uia").connect(title_re=app_title, timeout=wait)
            main_window = app.top_window()
            if main_window.exists():
                if main_window.get_show_state() == 2: main_window.restore()
                main_window.set_focus()
            run_smart_scenario(main_window, conf)
        except Exception as e:
            log(f"Error: {e}")
            print("คำแนะนำ: ตรวจสอบว่าเปิดโปรแกรม POS ไว้หรือยัง")
    input("\n>>> กด Enter เพื่อปิดโปรแกรม... <<<")