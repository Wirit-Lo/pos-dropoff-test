import time
import datetime
import sys
import ctypes # ใช้สำหรับวาดรูปและหาเมาส์

# ตรวจสอบและ Import library ที่จำเป็น
try:
    from pywinauto import uia_element_info
except ImportError:
    print("Error: ไม่พบไลบรารี pywinauto กรุณาติดตั้ง: pip install pywinauto")
    sys.exit(1)

# --- ส่วนจัดการเมาส์และหน้าจอ (Windows API) ---
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_mouse_pos():
    """หาตำแหน่งเมาส์ด้วย Windows API"""
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def draw_red_border(rect):
    """วาดกรอบสีแดงทับหน้าจอตรงตำแหน่ง Rect"""
    if not rect: return
    
    # ดึง Device Context ของทั้งหน้าจอ (Desktop)
    dc = ctypes.windll.user32.GetWindowDC(0)
    
    # สร้างปากกาสีแดง (Style=0(Solid), Width=5, Color=0x0000FF(Red in BGR))
    pen = ctypes.windll.gdi32.CreatePen(0, 5, 0x0000FF) 
    # เลือก Brush แบบโปร่งใส (Stock Object 5 = NULL_BRUSH)
    brush = ctypes.windll.gdi32.GetStockObject(5) 

    # เลือกอุปกรณ์วาดเขียนเข้า DC
    old_pen = ctypes.windll.gdi32.SelectObject(dc, pen)
    old_brush = ctypes.windll.gdi32.SelectObject(dc, brush)

    # วาดสี่เหลี่ยม (Rectangle)
    ctypes.windll.gdi32.Rectangle(dc, rect.left, rect.top, rect.right, rect.bottom)

    # คืนค่าและล้างหน่วยความจำ
    ctypes.windll.gdi32.SelectObject(dc, old_pen)
    ctypes.windll.gdi32.SelectObject(dc, old_brush)
    ctypes.windll.gdi32.DeleteObject(pen)
    ctypes.windll.user32.ReleaseDC(0, dc)

def get_current_element_info():
    """ดึงข้อมูล Element ณ ตำแหน่งเมาส์ปัจจุบัน"""
    x, y = 0, 0
    try:
        x, y = get_mouse_pos()
        elem = uia_element_info.UIAElementInfo.from_point(x, y)
        return x, y, elem
    except Exception as e:
        return x, y, None

def print_separator():
    print("-" * 60)

def main():
    print("============================================================")
    print("   UI INSPECTOR (HIGHLIGHT + PAUSE)")
    print("   1. นับถอยหลัง 5 วิ -> ชี้เมาส์ที่ปุ่ม")
    print("   2. เมื่อครบเวลา จะมี 'กรอบสีแดง' ขึ้นที่หน้าจอ")
    print("   3. โปรแกรมจะ 'หยุด' ให้คุณดูค่า จนกว่าจะกด Enter")
    print("   (กด Ctrl+C เพื่อออกจากโปรแกรม)")
    print("============================================================")
    print("")

    try:
        while True:
            # --- 1. ส่วนนับถอยหลัง ---
            for i in range(5, 0, -1):
                print(f"   ⏳ กำลังจะจับภาพในอีก {i} วินาที... (เตรียมชี้เมาส์)", end='\r')
                time.sleep(1)
            
            print(" " * 60, end='\r') # ล้างบรรทัดนับเวลา
            
            # --- 2. ส่วนบันทึกและวาดรูป ---
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            x, y, elem = get_current_element_info()

            # วาดกรอบสีแดงทันทีถ้าเจอ Element
            if elem and getattr(elem, 'rectangle', None):
                draw_red_border(elem.rectangle)

            print(f"[{timestamp}] 📸 บันทึกข้อมูลที่พิกัด ({x}, {y})")
            print_separator()

            if elem:
                name = getattr(elem, 'name', '')
                auto_id = getattr(elem, 'automation_id', '')
                control_type = getattr(elem, 'control_type', '')
                class_name = getattr(elem, 'class_name', '')
                rect = getattr(elem, 'rectangle', None)

                # แสดง ID เด่นๆ
                if auto_id:
                    print(f"   🔑 Automation ID :  '{auto_id}'")
                else:
                    print(f"   🔑 Automation ID :  (ไม่มี)")

                print(f"   🏷️  Name (Text)   :  '{name}'")
                print(f"   📦 Control Type  :  {control_type}")
                
                if rect:
                    print(f"   🔲 Rectangle     :  W={rect.width()}, H={rect.height()}")
                    # วาดซ้ำอีกทีเผื่อหาย (บางแอป Refresh จอบ่อย)
                    draw_red_border(rect)

                # --- แสดง Children ---
                try:
                    children = elem.children()
                    if children:
                        print(f"\n   📂 พบ {len(children)} รายการข้างใน (Children):")
                        print("   --------------------------------------------------")
                        for i, child in enumerate(children[:15]): 
                            c_name = getattr(child, 'name', '')
                            c_id = getattr(child, 'automation_id', '')
                            c_type = getattr(child, 'control_type', '')
                            
                            info_str = f"[{c_type}]"
                            if c_id: info_str += f" ID:'{c_id}'"
                            if c_name: info_str += f" Name:'{c_name}'"
                            print(f"      {i+1}. {info_str}")
                        
                        if len(children) > 15:
                            print(f"      ... (และอีก {len(children)-15} รายการ)")
                except:
                    print("\n   ⚠️ ไม่สามารถดึง Children ได้")

            else:
                print("   ❌ ไม่พบ UI Element")
            
            print_separator()
            
            # --- 3. ส่วนหยุดรอ (Pause) ---
            # วาดกรอบย้ำอีกทีก่อนรอ input
            if elem and getattr(elem, 'rectangle', None):
                draw_red_border(elem.rectangle)

            input("\n   ⏸️  ดูข้อมูลเสร็จแล้ว กด [Enter] เพื่อเริ่มสแกนใหม่...")
            print("\n" * 2)

    except KeyboardInterrupt:
        print("\n--- จบการทำงาน ---")

if __name__ == "__main__":
    main()