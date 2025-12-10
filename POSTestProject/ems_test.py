import configparser
import os
import time
import ctypes
from pywinauto.application import Application

# โหลด Config เพื่อหาชื่อหน้าต่าง
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): return None
    config.read(filename, encoding='utf-8')
    return config

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_mouse_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def run_coordinate_finder():
    conf = load_config()
    if not conf:
        print("ไม่พบไฟล์ config.ini")
        return

    print("Connecting...")
    try:
        # เชื่อมต่อเพื่อหาตำแหน่งหน้าต่างหลัก
        app = Application(backend="uia").connect(title_re=conf['APP']['WindowTitle'], timeout=10)
        win = app.top_window()
        win.set_focus()
        
        # ดึงตำแหน่งหน้าต่างหลัก
        rect = win.rectangle()
        win_w = rect.width()
        win_h = rect.height()
        
        print(f"\n[INFO] หน้าต่างโปรแกรมอยู่ที่: {rect}")
        print(f"[INFO] ขนาดหน้าต่าง: กว้าง={win_w}, สูง={win_h}")
        
        print("\n" + "="*50)
        print("   เครื่องมือหาพิกัดปุ่ม (Coordinate Finder V2)   ")
        print("="*50)
        print("คำแนะนำ: เอาเมาส์ไปชี้ที่ 'กึ่งกลางปุ่ม EMS' แล้วอยู่นิ่งๆ")
        print("นับถอยหลัง 5 วินาที...")
        
        for i in range(5, 0, -1):
            print(f"... {i} ...")
            time.sleep(1)
            
        # จับพิกัดเมาส์
        mx, my = get_mouse_pos()
        
        # คำนวณ Offset (ระยะห่างจากมุมซ้ายบนของหน้าต่าง)
        offset_x = mx - rect.left
        offset_y = my - rect.top
        
        # [NEW] คำนวณเป็นเปอร์เซ็นต์ (Ratio) เพื่อความยืดหยุ่น
        ratio_x = offset_x / win_w
        ratio_y = offset_y / win_h
        
        print("\n" + ">"*10 + " ผลลัพธ์ (CAPTURE) " + "<"*10)
        print(f"พิกัดเมาส์จริง : ({mx}, {my})")
        print(f"พิกัดสัมพัทธ์  : (x={offset_x}, y={offset_y})")
        print(f"สัดส่วน (Ratio): (x={ratio_x:.4f}, y={ratio_y:.4f})")
        print("-" * 50)
        
        print(f"วิธีที่ 1 (แบบ Fix พิกัด - พังถ้าจอเปลี่ยนขนาด):")
        print(f"   click_at_offset(main_window, {offset_x}, {offset_y})")
        
        print(f"\nวิธีที่ 2 (แบบ Ratio - รองรับการย่อขยายจอ):")
        print(f"   # แปะฟังก์ชันนี้ไว้ในไฟล์หลัก")
        print(f"   def click_at_ratio(window, rx, ry):")
        print(f"       rect = window.rectangle()")
        print(f"       target_x = rect.left + int(rect.width() * rx)")
        print(f"       target_y = rect.top + int(rect.height() * ry)")
        print(f"       mouse.click(coords=(target_x, target_y))")
        print(f"\n   # เรียกใช้ด้วยโค้ดนี้:")
        print(f"   click_at_ratio(main_window, {ratio_x:.4f}, {ratio_y:.4f})")
        print("-" * 50)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_coordinate_finder()