import configparser
import os
import time
import datetime
from pywinauto.application import Application

# ================= 1. Config & Setup =================
# ใช้ Config เดียวกับไฟล์หลัก หรือกำหนดเองตรงนี้
APP_TITLE_REGEX = ".*Escher Retail.*"  # หรือชื่อที่ตรงกับ Title Bar ของคุณ

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

def inspect_ui_elements(window):
    log("--- เริ่มตรวจสอบ Element บนหน้าจอ (Debug Mode) ---")
    
    # 1. ค้นหา ListItem (การ์ดบริการมักจะเป็นประเภทนี้)
    log("\n[Group A] ค้นหาประเภท 'ListItem' (รายการเมนู/การ์ด):")
    list_items = window.descendants(control_type="ListItem")
    
    if not list_items:
        log("   [!] ไม่พบ ListItem เลย")
    else:
        for i, item in enumerate(list_items):
            try:
                # ดึงข้อมูลสำคัญ
                text = item.window_text()
                rect = item.rectangle()
                auto_id = item.element_info.automation_id
                class_name = item.element_info.class_name
                
                # เช็คว่ามองเห็นไหม
                visible_status = "Visible" if item.is_visible() else "Hidden"
                
                if item.is_visible():
                    print(f"   Index [{i}] : Text='{text}' | ID='{auto_id}' | Class='{class_name}' | Pos=({rect.left}, {rect.top})")
                else:
                    # ถ้าซ่อนอยู่ ไม่ต้องโชว์ให้รก หรือโชว์แบบย่อ
                    pass 
            except:
                print(f"   Index [{i}] : <Error reading info>")

    # 2. ค้นหา Button (เผื่อเป็นปุ่มธรรมดา)
    log("\n[Group B] ค้นหาประเภท 'Button' (ปุ่มกด):")
    buttons = window.descendants(control_type="Button")
    
    visible_buttons = [b for b in buttons if b.is_visible()]
    for i, btn in enumerate(visible_buttons):
        try:
            text = btn.window_text()
            rect = btn.rectangle()
            auto_id = btn.element_info.automation_id
            print(f"   Button [{i}] : Text='{text}' | ID='{auto_id}' | Pos=({rect.left}, {rect.top})")
        except: pass

    log("\n------------------------------------------------")
    log("คำแนะนำ: มองหา Index หรือ ID ของปุ่มที่มีพิกัด (Pos) อยู่ตรงกลางหน้าจอ")
    log("Index 0 มักจะเป็นเมนูด้านซ้าย (Home/Lock) ให้ลอง Index ถัดๆ ไป")

# ================= 2. Main Execution =================
if __name__ == "__main__":
    log("Connecting to application...")
    try:
        # เชื่อมต่อกับหน้าต่างที่เปิดอยู่แล้ว
        app = Application(backend="uia").connect(title_re=APP_TITLE_REGEX, timeout=10)
        win = app.top_window()
        win.set_focus()
        
        # สั่งตรวจสอบทันที
        inspect_ui_elements(win)
        
        # (Optional) ถ้าอยากลองเทสกด Index ไหน ให้แก้เลขตรงนี้แล้ว Uncomment
        # test_index = 4  # <--- ลองเปลี่ยนเลขนี้ตามที่เห็นใน Log
        # log(f"\n...Test Click ListItem Index {test_index}...")
        # items = win.descendants(control_type="ListItem")
        # visible_items = [x for x in items if x.is_visible()]
        # if len(visible_items) > test_index:
        #     visible_items[test_index].click_input()
        #     log("Click Done.")
        
    except Exception as e:
        log(f"Error: {e}")
        log("หาหน้าต่างโปรแกรมไม่เจอ หรือชื่อ Title ไม่ตรง")