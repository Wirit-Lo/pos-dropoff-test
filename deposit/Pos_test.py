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

def click_scroll_arrow_smart(window, direction='right'):
    """
    ฟังก์ชันกดปุ่มเลื่อนหน้าจอ (Smart Click)
    รองรับ:
     - direction='right' : เลื่อนไปทางขวา
     - direction='left'  : เลื่อนไปทางซ้าย
    """
    try:
        # 1. ค้นหากล่องรายการสินค้า
        target_group = window.descendants(automation_id="ShippingServiceList")
        
        # --- กรณีหา ID กล่องไม่เจอ (Fallback) ---
        if not target_group:
            win_rect = window.rectangle()
            fallback_y = win_rect.top + int(win_rect.height() * 0.50)
            
            if direction == 'right':
                fallback_x = win_rect.left + int(win_rect.width() * 0.95) # 95% ขวา
            else: 
                fallback_x = win_rect.left + int(win_rect.width() * 0.05) # 5% ซ้าย
                
            window.click_input(coords=(fallback_x, fallback_y))
            return True

        # --- กรณีเจอกล่อง (คำนวณแม่นยำ) ---
        container = target_group[0]
        rect = container.rectangle()
        target_y = (rect.top + rect.bottom) // 2

        if direction == 'right':
            # เลื่อนขวา: ขอบขวาสุด - 45 pixel
            target_x = rect.right - 45
            log(f"   [Scroll Action] เลื่อนขวา -> คลิก ({target_x}, {target_y})")
        else:
            # เลื่อนซ้าย: ขอบซ้ายสุด + 45 pixel
            target_x = rect.left + 45
            log(f"   [Scroll Action] เลื่อนซ้าย -> คลิก ({target_x}, {target_y})")
        
        window.click_input(button='left', coords=(target_x, target_y), double=False)
        return True

    except Exception as e:
        log(f"   [Error] Scroll {direction} Failed: {e}")
        return False

def find_and_click_with_rotate_logic(window, target_id, max_scrolls=7):
    """
    ค้นหาปุ่มบริการแบบอัจฉริยะ (Bidirectional Search)
    1. กวาดหาทางขวา (Right Sweep)
    2. ถ้าไม่เจอ -> กวาดหาทางซ้าย (Left Sweep) เพื่อย้อนกลับ
    """
    log(f"...กำลังค้นหาปุ่มบริการ ID: '{target_id}'...")

    def attempt_click_in_current_view():
        """ฟังก์ชันย่อย: ลองหาและกดปุ่มในหน้าจอตอนนี้"""
        found_elements = [c for c in window.descendants() if str(c.element_info.automation_id) == target_id and c.is_visible()]
        if not found_elements:
            return "NOT_FOUND" # ไม่เจอปุ่ม

        target = found_elements[0]
        rect = target.rectangle()
        win_rect = window.rectangle()
        
        # Safe Zone Check (70% ของจอ)
        safe_limit = win_rect.left + (win_rect.width() * 0.70) 
        
        if rect.right < safe_limit:
            log(f"   ✅ เจอปุ่มใน Safe Zone -> กดเลย")
            try:
                target.click_input()
            except:
                target.set_focus()
                window.type_keys("{ENTER}")
            return "CLICKED"
        else:
            log(f"   ⚠️ เจอปุ่มแต่อยู่ขวาสุด (โดนบัง) -> ต้องเลื่อนขวาอีกนิด")
            return "BLOCKED" # เจอปุ่มแต่กดลำบาก

    # --- Phase 1: กวาดหาทางขวา (Right Sweep) ---
    log("--- [Phase 1] ค้นหาและเลื่อนขวา ---")
    for i in range(1, max_scrolls + 1):
        result = attempt_click_in_current_view()
        
        if result == "CLICKED":
            return True
        elif result == "BLOCKED":
            # ถ้าโดนบัง ให้เลื่อนขวาเพื่อดึงปุ่มเข้ามา
            click_scroll_arrow_smart(window, direction='right')
            time.sleep(1.5)
            # ลองกดอีกทีหลังเลื่อน
            if attempt_click_in_current_view() == "CLICKED": return True
            continue 
        
        # ถ้าไม่เจอเลย (NOT_FOUND) -> เลื่อนขวาไปหน้าถัดไป
        log(f"   [{i}/{max_scrolls}] ไม่เจอ -> เลื่อนขวา...")
        if not click_scroll_arrow_smart(window, direction='right'):
             window.type_keys("{RIGHT}")
        time.sleep(1.5)

    # --- Phase 2: ถ้ายังไม่เจอ -> กวาดหาทางซ้าย (Left Sweep) ---
    # เผื่อว่าเราเลื่อนเลย หรือปุ่มมันอยู่หน้าแรกๆ
    log("--- [Phase 2] ไม่เจอทางขวา -> ลองเลื่อนกลับทางซ้าย (Reverse Search) ---")
    # เพิ่มรอบการค้นหาตอนถอยกลับ (บวกเพิ่มเพื่อให้แน่ใจว่ากลับไปถึงต้นทาง)
    reverse_scrolls = max_scrolls + 3 
    
    for i in range(1, reverse_scrolls + 1):
        result = attempt_click_in_current_view()
        
        if result == "CLICKED":
            return True
        
        # ไม่ว่าจะ BLOCKED หรือ NOT_FOUND ในเฟสนี้ เราจะเลื่อนซ้ายอย่างเดียวเพื่อย้อนกลับ
        log(f"   [Reverse {i}/{reverse_scrolls}] ไม่เจอ/ย้อนกลับ -> เลื่อนซ้าย...")
        if not click_scroll_arrow_smart(window, direction='left'):
             window.type_keys("{LEFT}")
        time.sleep(1.5)

    log(f"[X] หมดความพยายามในการหาปุ่ม '{target_id}' (หาทั้งไปและกลับแล้ว)")
    return False

# ================= 3. Main Logic (เหมือนเดิม) =================
def test_process(main_window, config):
    log("--- เริ่มการทำงาน ---")
    
    # [STEP 1] เลือกบริการ
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