import configparser
import os
import time
import datetime
from pywinauto.application import Application
# ใช้ send_keys เพื่อจำลองการกดคีย์บอร์ดระดับ System
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

# ================= 2. Helper Functions =================
def ensure_focus(window):
    """ทำให้แน่ใจว่าหน้าจอ Focus อยู่"""
    try:
        window.set_focus()
        time.sleep(0.5)
        rect = window.rectangle()
        # คลิกที่มุมซ้ายบนที่เป็นพื้นที่ว่างๆ เพื่อ Reset Focus
        mouse.click(coords=(rect.left + 50, rect.top + 150))
    except: pass

# ================= 3. UI Inspector Mode (โหมดดึงค่า ID) =================
def run_ui_inspector(main_window):
    log(f"\n--- เริ่มต้นโหมด X-RAY (ค้นหา ID ปุ่ม) ---")
    log("กรุณาตรวจสอบว่าเปิดหน้า 'บริการหลัก' รอไว้แล้ว")
    time.sleep(2)

    ensure_focus(main_window)
    
    output_file = "UI_DUMP_SERVICE_PAGE.txt"
    log(f"...กำลังวิเคราะห์โครงสร้างหน้าจอ และบันทึกลงไฟล์ '{output_file}'...")
    log("(อาจใช้เวลาสักครู่ หน้าจออาจจะกะพริบหรือมีกรอบสีแดงขึ้น)")

    try:
        # 1. บันทึกโครงสร้างทั้งหมดลงไฟล์ (เผื่อไว้ดูละเอียด)
        main_window.print_control_identifiers(depth=None, filename=output_file)
        log(f"[/] บันทึกไฟล์สำเร็จ! ลองเปิด '{output_file}' ดูได้ครับ")

        # 2. ค้นหาและโชว์ ID ของปุ่มที่น่าจะเป็น EMS บนหน้าจอ Console เลย
        log("\n" + "="*50)
        log("    ผลการค้นหาปุ่ม EMS / E / บริการ บนหน้าจอ    ")
        log("="*50)
        
        found_candidate = False
        # วนลูปหาทุก Element ในหน้าต่าง
        for child in main_window.descendants():
            try:
                # ดึงค่าต่างๆ ของ Element
                text = child.window_text()
                auto_id = child.element_info.automation_id
                control_type = child.element_info.control_type
                
                # กรองเฉพาะสิ่งที่น่าจะเป็นปุ่มที่เราหา
                keywords = ["EMS", "E", "อีเอ็มเอส", "บริการ", "ด่วน", "Service"]
                is_match = False
                
                # เช็คว่ามี keyword อยู่ใน text หรือ id ไหม
                if text and any(k in text for k in keywords): is_match = True
                if auto_id and any(k in auto_id for k in keywords): is_match = True
                
                # ถ้าเจอที่น่าสนใจ ให้ปริ้นออกมา
                if is_match:
                    found_candidate = True
                    print(f"\n[เจอเป้าหมาย!] Type: {control_type}")
                    print(f"   Name (Text) : '{text}'")
                    print(f"   AutomationId: '{auto_id}'  <-- ลองใช้ค่านี้!")
                    
                    # วาดกรอบให้ดูด้วยว่าคือปุ่มไหนบนจอ
                    try:
                        child.draw_outline(colour='green', thickness=2)
                    except: pass
            except: pass

        if not found_candidate:
            log("[!] ไม่พบ Element ที่มีคำว่า EMS/E ในชื่อหรือ ID เลย")
            log("    ลองเปิดไฟล์ Text ที่สร้างขึ้นเพื่อไล่ดูด้วยตาอีกทีครับ")
        else:
            log("\n" + "="*50)
            log("วิธีใช้: นำค่า AutomationId ที่ได้ ไปใส่ในฟังก์ชัน smart_click")
            log("ตัวอย่าง: smart_click(window, 'ค่า_AutomationId_ที่เจอ')")
            log("="*50)

    except Exception as e:
        log(f"[Error] เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")

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
            
            # รันโหมดดึงค่า ID แทนโหมดเทสปกติ
            run_ui_inspector(win)
            
        except Exception as e:
            log(f"Error: {e}")