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
    
    try:
        dc = ctypes.windll.user32.GetWindowDC(0)
        pen = ctypes.windll.gdi32.CreatePen(0, 5, 0x0000FF) 
        brush = ctypes.windll.gdi32.GetStockObject(5) 
        old_pen = ctypes.windll.gdi32.SelectObject(dc, pen)
        old_brush = ctypes.windll.gdi32.SelectObject(dc, brush)
        ctypes.windll.gdi32.Rectangle(dc, rect.left, rect.top, rect.right, rect.bottom)
        ctypes.windll.gdi32.SelectObject(dc, old_pen)
        ctypes.windll.gdi32.SelectObject(dc, old_brush)
        ctypes.windll.gdi32.DeleteObject(pen)
        ctypes.windll.user32.ReleaseDC(0, dc)
    except:
        pass

def drill_down_element(elem, x, y):
    """
    ฟังก์ชันเจาะลึก: หา Element ที่เล็กที่สุดที่ตรงกับพิกัดเมาส์
    """
    current = elem
    while True:
        try:
            children = current.children()
            if not children:
                break
            
            candidates = []
            for child in children:
                rect = getattr(child, 'rectangle', None)
                if rect:
                    if (rect.left <= x < rect.right) and (rect.top <= y < rect.bottom):
                        candidates.append(child)
            
            if not candidates:
                break

            candidates.sort(key=lambda c: (c.rectangle.width() * c.rectangle.height()))
            best_candidate = candidates[0]

            if best_candidate == current:
                break
                
            current = best_candidate
        except Exception:
            break
    return current

def get_ancestors(elem, limit=3):
    """
    ฟังก์ชันย้อนหาพ่อแม่ (Parent) ขึ้นไปตามจำนวนชั้นที่กำหนด
    มีประโยชน์มากเวลากดโดนปุ่มลูก (Text/Image) แต่ ID อยู่ที่ปุ่มแม่ (Button)
    """
    ancestors = []
    try:
        current = elem
        for _ in range(limit):
            # uia_element_info บางเวอร์ชันใช้ .parent บางอันเป็น method
            parent = getattr(current, 'parent', None)
            if not parent:
                # ลองเรียกเป็น method เผื่อเป็นเวอร์ชันเก่า
                try: parent = current.get_parent()
                except: pass
                
            if not parent:
                break
                
            ancestors.append(parent)
            current = parent
    except:
        pass
    return ancestors

def get_current_element_info():
    x, y = 0, 0
    try:
        x, y = get_mouse_pos()
        elem = uia_element_info.UIAElementInfo.from_point(x, y)
        if elem:
            elem = drill_down_element(elem, x, y)
        return x, y, elem
    except Exception as e:
        return x, y, None

def print_separator():
    print("-" * 60)

def main():
    print("============================================================")
    print("   UI INSPECTOR (SMART HIERARCHY MODE)")
    print("   1. นับถอยหลัง 5 วิ -> ชี้เมาส์ที่ปุ่มเล็กๆ")
    print("   2. ระบบจะโชว์ข้อมูลของตัวที่ชี้ + ตัวพ่อแม่ (Parent)")
    print("      (ช่วยแก้ปัญหาชี้โดนรูปภาพแล้วไม่มี ID)")
    print("============================================================")
    print("")

    try:
        while True:
            # --- 1. ส่วนนับถอยหลัง ---
            for i in range(5, 0, -1):
                print(f"   ⏳ จับภาพในอีก {i} วินาที... ", end='\r')
                time.sleep(1)
            
            print(" " * 60, end='\r') 
            
            # --- 2. ส่วนบันทึกและวาดรูป ---
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            x, y, elem = get_current_element_info()

            if elem and getattr(elem, 'rectangle', None):
                draw_red_border(elem.rectangle)

            print(f"[{timestamp}] 📸 พิกัด ({x}, {y})")
            print_separator()

            if elem:
                name = getattr(elem, 'name', '')
                auto_id = getattr(elem, 'automation_id', '')
                control_type = getattr(elem, 'control_type', '')
                rect = getattr(elem, 'rectangle', None)

                # --- ส่วนแสดงผลตัวที่ชี้อยู่ (Target) ---
                print(f"🎯 TARGET (ตัวที่เมาส์ชี้):")
                if auto_id:
                    print(f"   🔑 ID    : '{auto_id}'")
                else:
                    print(f"   ⚠️ ID    : (ไม่มี - ลองดู Parent ด้านล่าง)")
                
                print(f"   🏷️  Name  : '{name}'")
                print(f"   📦 Type  : {control_type}")
                if rect:
                    print(f"   🔲 Size  : {rect.width()} x {rect.height()}")

                # --- ส่วนแสดงผลพ่อแม่ (Ancestors) [NEW Feature] ---
                ancestors = get_ancestors(elem)
                if ancestors:
                    print(f"\n⬆️  PARENTS (ตัวแม่ที่หุ้มอยู่ - มักจะมี ID ตรงนี้):")
                    for i, anc in enumerate(ancestors):
                        p_name = getattr(anc, 'name', '')
                        p_id = getattr(anc, 'automation_id', '')
                        p_type = getattr(anc, 'control_type', '')
                        
                        # สร้างข้อความแสดงผล
                        info = f"   Layer {i+1}: [{p_type}]"
                        if p_id: 
                            info += f" 🔑 ID='{p_id}'" # เน้น ID ถ้ามี
                        else:
                            info += f" (No ID)"
                        
                        if p_name: info += f" Name='{p_name}'"
                        print(info)

                # --- ส่วนแสดงลูกๆ (Children) ---
                try:
                    children = elem.children()
                    if children:
                        print(f"\n⬇️  CHILDREN (ไส้ใน - เผื่อตัวที่ชี้เป็นกล่องรวม):")
                        for i, child in enumerate(children[:10]): 
                            c_name = getattr(child, 'name', '')
                            c_id = getattr(child, 'automation_id', '')
                            c_type = getattr(child, 'control_type', '')
                            
                            c_info = f"   Child {i+1}: [{c_type}]"
                            if c_id: c_info += f" ID='{c_id}'"
                            if c_name: c_info += f" Name='{c_name}'"
                            print(c_info)
                except:
                    pass

            else:
                print("   ❌ ไม่พบ UI Element")
            
            print_separator()
            
            # Draw again before pause
            if elem and getattr(elem, 'rectangle', None):
                draw_red_border(elem.rectangle)

            input("\n   ⏸️  กด [Enter] เพื่อเริ่มสแกนใหม่...")
            print("\n" * 2)

    except KeyboardInterrupt:
        print("\n--- จบการทำงาน ---")

if __name__ == "__main__":
    main()