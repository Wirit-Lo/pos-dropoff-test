import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import Desktop, mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): return None
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Inspector Mode (โหมดดึงค่า ID จากเมาส์) =================
def run_hover_inspector():
    """
    โหมดโหด: ดึง ID จากตำแหน่งที่เมาส์ชี้อยู่ (ไม่ต้องคลิก ไม่ต้องเดา)
    """
    log("\n" + "="*50)
    log("       โหมดดึง ID ด้วยการชี้เมาส์ (Mouse Hover)       ")
    log("="*50)
    log("คำแนะนำ: เตรียมเอาเมาส์ไปชี้ที่ปุ่ม 'บริการ EMS' หรือปุ่มที่ต้องการ")
    log("ระบบจะนับถอยหลัง 5 วินาที... เริ่ม!")

    # นับถอยหลังให้เวลาผู้ใช้เลื่อนเมาส์
    for i in range(5, 0, -1):
        log(f"... {i} ...")
        time.sleep(1)

    log("\n[CAPTURE] กำลังดึงข้อมูลตรงจุดที่เมาส์ชี้...")
    
    try:
        # 1. ดึงพิกัดเมาส์ปัจจุบัน
        x, y = mouse.get_cursor_pos()
        log(f"พิกัดเมาส์: ({x}, {y})")

        # 2. เจาะจง Element ตรงนั้นโดยตรง (Backend UIA)
        # ใช้วิธีนี้จะแม่นยำที่สุดเพราะได้สิ่งที่อยู่ใต้เมาส์จริงๆ
        element = Desktop(backend="uia").from_point(x, y)

        # 3. แสดงผลลัพธ์
        log("\n" + "-"*30)
        log("   ข้อมูลปุ่มที่เจอ (Element Info)   ")
        log("-"*30)
        
        # วาดกรอบสีเขียวรอบๆ เพื่อยืนยันว่าจับถูกตัว
        try:
            element.draw_outline(colour='green', thickness=3)
        except: pass

        # ดึงค่าต่างๆ
        wrapper = element.wrapper_object()
        print(f"Text (ชื่อที่แสดง)    : '{wrapper.window_text()}'")
        print(f"Control Type        : '{wrapper.element_info.control_type}'")
        print(f"Automation ID       : '{wrapper.element_info.automation_id}'  <-- ตัวนี้สำคัญ!")
        print(f"Class Name          : '{wrapper.element_info.class_name}'")
        
        # 4. ดึงข้อมูลตัวแม่ (Parent) เผื่อว่า ID อยู่ที่กล่องครอบ
        parent = wrapper.parent()
        if parent:
            print("\n--- ข้อมูลตัวแม่ (Parent Container) ---")
            print(f"Parent Type         : '{parent.element_info.control_type}'")
            print(f"Parent Text         : '{parent.window_text()}'")
            print(f"Parent ID           : '{parent.element_info.automation_id}'")
            try:
                parent.draw_outline(colour='yellow', thickness=2)
            except: pass
        
        log("\n" + "="*50)
        log("วิธีใช้: นำค่า Automation ID ที่ได้ ไปใส่ใน smart_click แทนชื่อปุ่ม")
        log("ตัวอย่าง: smart_click(window, ['AutomationID_ที่เจอ'])")
        log("="*50)

    except Exception as e:
        log(f"[Error] เกิดข้อผิดพลาด: {e}")
        log("ลองรันใหม่อีกครั้ง และตรวจสอบว่าหน้าต่างโปรแกรม Active อยู่")

# ================= 3. Execution =================
if __name__ == "__main__":
    # ไม่ต้อง Connect แอพ แค่รันฟังก์ชัน Inspector เลย
    # เพราะ Desktop().from_point ทำงานระดับ Global
    run_hover_inspector()