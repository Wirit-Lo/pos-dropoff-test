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

def click_scroll_arrow_smart(window, direction='right', repeat=5):
    """
    ฟังก์ชันเลื่อนหน้าจอแบบ Drag (ลาก/ปัดหน้าจอ) แบบ Speed
    - repeat: ค่าเริ่มต้นปรับเป็น 5 รอบ เพื่อให้เลื่อนไปได้ไกลขึ้นมาก
    - ตัด delay ทิ้งเพื่อให้ทำงานต่อเนื่องทันที
    """
    try:
        # 1. ค้นหากล่องรายการสินค้า
        target_group = window.descendants(automation_id="ShippingServiceList")
        
        # กำหนดพื้นที่ที่จะทำการลาก (Rect)
        if target_group:
            rect = target_group[0].rectangle()
        else:
            rect = window.rectangle()

        # คำนวณจุดกึ่งกลางแนวตั้ง (แกน Y)
        center_y = (rect.top + rect.bottom) // 2
        
        # ปรับ Margin ให้น้อยที่สุด (20px) เพื่อให้ระยะลากกว้างที่สุดเท่าที่จะทำได้
        margin = 20

        start_x = 0
        end_x = 0

        if direction == 'right':
            # ต้องการดูข้อมูลทางขวา -> ลากจาก "ขวาสุด" ไป "ซ้ายสุด"
            start_x = rect.right - margin
            end_x = rect.left + margin
        else:
            # ต้องการดูข้อมูลทางซ้าย -> ลากจาก "ซ้ายสุด" ไป "ขวาสุด"
            start_x = rect.left + margin
            end_x = rect.right - margin

        # เริ่มทำการลาก (Loop ตามจำนวน repeat)
        for i in range(repeat):
            # drag_mouse_input: ลากเมาส์ (เกิดแถบคลุมดำ)
            # ตัด delay ออกเพื่อให้ลากต่อเนื่องทันที
            window.drag_mouse_input(dst=(end_x, center_y), src=(start_x, center_y))
            
            # ไม่มีการ Sleep เพื่อความไวสูงสุด

        return True

    except Exception as e:
        print(f"Scroll Error: {e}")
        return False

def find_and_click_with_rotate_logic(window, target_id, max_rotations=10):
    """
    ค้นหาปุ่มบริการแบบวนลูป (Search -> Click -> If Not Found -> Scroll)
    """
    log(f"...กำลังค้นหาปุ่มบริการ ID: '{target_id}'...")
    
    for i in range(1, max_rotations + 1):
        # 1. สแกนหาปุ่มเป้าหมายในหน้าจอปัจจุบัน
        found_elements = [c for c in window.descendants() if str(c.element_info.automation_id) == target_id and c.is_visible()]
        
        should_scroll = False # ตัวแปรควบคุมการเลื่อน

        if found_elements:
            target = found_elements[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            
            # [แก้ไข] Safe Zone Check: ปรับลดระยะปลอดภัยเหลือ 70% ของจอ
            # เพื่อป้องกันปุ่มที่อยู่ขวาสุด (ใต้ Panel) ไม่ให้ถูกกด
            safe_limit = win_rect.left + (win_rect.width() * 0.70) 
            
            # ตรวจสอบว่า "ขอบขวาของปุ่ม" เกินระยะปลอดภัยหรือไม่
            if rect.right < safe_limit:
                 log(f"   [{i}] ✅ เจอปุ่มใน Safe Zone (Right={rect.right} < {int(safe_limit)}) -> กำลังกด...")
                 try:
                    target.click_input()
                 except:
                    # กรณี Click ปกติไม่ติด (เช่น ติด Animation) ให้ลอง Focus+Enter
                    target.set_focus()
                    window.type_keys("{ENTER}")
                 return True
            else:
                 # ถ้าเจอปุ่ม แต่อยู่เกินระยะ Safe Zone ให้สั่งเลื่อน
                 log(f"   [{i}] ⚠️ เจอปุ่มแต่โดนบัง/อยู่ขวาสุด (Right={rect.right}) -> ต้องเลื่อนให้เข้ามากลางจอ")
                 should_scroll = True
        else:
            log(f"   [{i}] ไม่เจอปุ่มในหน้านี้ -> เลื่อนขวา...")
            should_scroll = True
        
        # 2. สั่งเลื่อนหน้าจอ (ถ้าไม่เจอ หรือ เจอปุ่มแต่โดนบัง)
        if should_scroll:
            if not click_scroll_arrow_smart(window):
                # ถ้าฟังก์ชัน Smart Click พังจริงๆ ให้กดปุ่มลูกศรขวาที่คีย์บอร์ดแทน
                log("   [Fallback] Smart Click ไม่ทำงาน -> ใช้ปุ่มลูกศรขวาบนคีย์บอร์ด")
                window.type_keys("{RIGHT}")
            
            time.sleep(1.5) # รอ Animation เลื่อน (สำคัญมาก)
        
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