import configparser
import os
import time
import datetime
from pywinauto.application import Application

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    config = configparser.ConfigParser()
    if not os.path.exists(file_path): 
        # Dummy config สำหรับทดสอบถ้าไม่มีไฟล์
        return {'PRODUCT_QUANTITY': {'Quantity': '1'}, 'APP': {'WindowTitle': 'Escher Retail'}}
    config.read(file_path, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Core Functions (แก้ไขใหม่) =================

def click_scroll_arrow_smart(window):
    """
    ฟังก์ชันกดปุ่มเลื่อนขวาแบบเจาะจง (Smart Click)
    หลักการ: หา 'กล่องรายการสินค้า' (ShippingServiceList) แล้วกดที่ขอบขวาของมัน
    """
    try:
        # 1. ค้นหากล่องรายการสินค้าด้วย ID ที่ได้จาก Inspector
        # ใช้ descendants เพราะมันมักจะอยู่ใน Group ย่อย
        target_group = window.descendants(automation_id="ShippingServiceList")
        
        if not target_group:
            log("   [Warning] หา ID 'ShippingServiceList' ไม่เจอ -> จะลองกดที่ขอบจอขวาแทน")
            # Fallback: ถ้าหากล่องไม่เจอจริงๆ ให้กดที่ขอบขวาของหน้าจอ (75% ของความกว้าง)
            win_rect = window.rectangle()
            fallback_x = win_rect.left + int(win_rect.width() * 0.95) # 95% ไปทางขวา
            fallback_y = win_rect.top + int(win_rect.height() * 0.50) # กึ่งกลางแนวตั้ง
            window.click_input(coords=(fallback_x, fallback_y))
            return True

        # 2. คำนวณจุดคลิกจากกล่องที่เจอ
        container = target_group[0]
        rect = container.rectangle()
        
        # จุด X: เอาขอบขวาสุด ลบเข้ามา 35 pixel (เพื่อให้โดนปุ่มลูกศรพอดี)
        target_x = rect.right - 35
        # จุด Y: กึ่งกลางแนวตั้งของกล่อง
        target_y = (rect.top + rect.bottom) // 2

        log(f"   [Scroll] พบกล่องรายการสินค้า -> คลิกที่ขอบขวา ({target_x}, {target_y})")
        
        # 3. สั่งคลิก
        window.click_input(coords=(target_x, target_y))
        return True

    except Exception as e:
        log(f"   [Error] Scroll Failed: {e}")
        return False

def find_and_click_with_rotate_logic(window, target_id, max_rotations=10):
    """
    ค้นหาปุ่มบริการแบบวนลูป (Search -> Click -> If Not Found -> Scroll)
    """
    log(f"...กำลังค้นหาปุ่มบริการ ID: '{target_id}'...")
    
    for i in range(1, max_rotations + 1):
        # 1. สแกนหาปุ่มเป้าหมายในหน้าจอปัจจุบัน
        found_elements = [c for c in window.descendants() if str(c.element_info.automation_id) == target_id and c.is_visible()]
        
        if found_elements:
            target = found_elements[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            
            # Safe Zone Check: เช็คว่าปุ่มไม่ได้หลบมุมขวาจนกดไม่ได้
            safe_limit = win_rect.left + (win_rect.width() * 0.98) # ยอมให้อยู่ขวาสุดๆ ได้
            
            if rect.left < safe_limit:
                 log(f"   [{i}] ✅ เจอปุ่มแล้ว! -> กำลังกด...")
                 try:
                    target.click_input()
                 except:
                    # กรณี Click ปกติไม่ติด (เช่น ติด Animation) ให้ลอง Focus+Enter
                    target.set_focus()
                    window.type_keys("{ENTER}")
                 return True
            else:
                 log(f"   [{i}] เจอปุ่ม แต่อยู่ตกขอบจอ -> ต้องเลื่อนหาก่อน")
        else:
            log(f"   [{i}] ไม่เจอปุ่มในหน้านี้ -> เลื่อนขวา...")
        
        # 2. ถ้าไม่เจอ หรือกดไม่ได้ -> สั่งเลื่อนหน้าจอ
        if not click_scroll_arrow_smart(window):
            # ถ้าฟังก์ชัน Smart Click พังจริงๆ ให้กดปุ่มลูกศรขวาที่คีย์บอร์ดแทน
            window.type_keys("{RIGHT}")
            
        time.sleep(1.5) # รอ Animation เลื่อน (สำคัญ)
        
    log(f"[X] หมดความพยายามในการหาปุ่ม '{target_id}'")
    return False

# ================= 3. Main Logic (เหมือนเดิม) =================
def test_process(main_window, config):
    log("--- เริ่มการทำงาน ---")
    
    # [STEP 1] เลือกบริการ (แก้ไข ID ตรงนี้ถ้าเปลี่ยนบริการ)
    # สมมติใช้ ID เดิม หรือถ้าจะเทสอันอื่นก็เปลี่ยนได้เลย
    target_service_id = "ShippingService_2583" 
    
    if not find_and_click_with_rotate_logic(main_window, target_service_id):
        log("จบการทำงาน (หาปุ่มบริการไม่เจอ)")
        return

    # [STEP 2] จัดการ Popup (ถ้ามี)
    log("...รอ Popup ถัดไป...")
    time.sleep(1.0)
    
    # กด Enter เผื่อไว้กรณีต้อง confirm บริการ
    try: main_window.type_keys("{ENTER}")
    except: pass

    qty = config['PRODUCT_QUANTITY'].get('Quantity', '1') if 'PRODUCT_QUANTITY' in config else '1'
    log(f"...เตรียมใส่จำนวน: {qty}...")
    time.sleep(1.5)

    # หา Popup Window
    popup_window = None
    try:
        app = Application(backend="uia").connect(active_only=True)
        top = app.top_window()
        # เช็คว่าเป็น Popup จริงไหม (ดูจากชื่อ หรือ ขนาดที่เล็กกว่าจอหลัก)
        if top.element_info.control_type == "Window" and "Retail" not in top.window_text():
            popup_window = top
    except: pass
    
    if not popup_window:
        # ลองหาจากลูกของ Main Window
        children = main_window.children(control_type="Window")
        if children: popup_window = children[0]

    if popup_window:
        log(f"   [Popup] เจอหน้าต่าง: {popup_window.window_text()}")
        try:
            popup_window.set_focus()
            # พยายามหาช่องกรอกจำนวน (Edit Box)
            edits = popup_window.descendants(control_type="Edit")
            target_edit = None
            for e in edits:
                if e.is_visible() and e.rectangle().width() > 30:
                    target_edit = e
                    break
            
            if target_edit:
                target_edit.click_input()
                target_edit.type_keys("^a{DELETE}", pause=0) # Clear
                target_edit.type_keys(str(qty), with_spaces=True)
                popup_window.type_keys("{ENTER}")
                log("   [Success] กรอกจำนวนและยืนยันเรียบร้อย")
            else:
                # ถ้าหาช่องไม่เจอ พิมพ์ใส่ Window เลย (Blind Type)
                popup_window.type_keys(str(qty), with_spaces=True)
                popup_window.type_keys("{ENTER}")
                log("   [Success] (Blind Mode) กรอกจำนวนเรียบร้อย")
        except Exception as e:
            log(f"   [Error] Popup Error: {e}")
    else:
        log("   [Note] ไม่พบ Popup (อาจจะไม่มี หรือข้ามไปแล้ว)")

    log("--- จบการทำงาน ---")

# ================= 4. Run =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        try:
            app_title = conf['APP'].get('WindowTitle', 'Escher Retail')
            log(f"Connecting to: {app_title}")
            
            # เชื่อมต่อ Application
            try:
                app = Application(backend="uia").connect(title_re=app_title, timeout=10)
            except:
                log("Connect by Title failed, trying Active Window...")
                app = Application(backend="uia").connect(active_only=True)

            main_window = app.top_window()
            main_window.set_focus()
            
            test_process(main_window, conf)
            
        except Exception as e:
            log(f"Critical Error: {e}")