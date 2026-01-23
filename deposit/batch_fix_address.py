"""
Batch script to apply Address List fix to all Customsize*.py files
Fix 1: Check ListItem has text content before selecting
Fix 2: Auto-switch to Manual Mode when Error Popup is detected
"""
import os
import re
import glob

# Directory containing the files
base_dir = r"d:\EWT\Automate POS\deposit"

# Pattern for Fix 1: Original code block in process_receiver_address_selection
OLD_PATTERN_1 = '''                    if visible_items:
                        # *** เลือกตัวแรกสุด (Index 0) ***
                        target_item = visible_items[0]
                        log(
                            f"[/] เจอ ID 'AddressResult' และรายการย่อย {len(visible_items)} รายการ -> ล็อคเป้าตัวแรก")
                        break
            except:
                pass

            # 3. [Fallback] แผนสำรอง: เผื่อหา ID ไม่เจอ ให้หากว้างๆ แบบเดิม (แต่ลดเงื่อนไขความสูงลง)
            if not target_item:
                try:
                    list_items = [i for i in window.descendants(
                        control_type="ListItem") if i.is_visible()]
                    # เอาแค่ Top > 80 (เผื่อจอเล็กมาก Header บัง)
                    valid_items = [
                        i for i in list_items if i.rectangle().top > 80]
                    if valid_items:
                        valid_items.sort(key=lambda x: x.rectangle().top)
                        target_item = valid_items[0]
                        log("[/] เจอ ListItem (Fallback Mode) -> ล็อคเป้าตัวแรก")
                        break
                except:
                    pass

            time.sleep(0.25)'''

NEW_PATTERN_1 = '''                    # [FIX] ตรวจสอบว่ารายการมี text content จริงๆ (ไม่ใช่แค่ element ว่างเปล่า)
                    valid_with_text = []
                    for item in visible_items:
                        try:
                            item_text = item.window_text().strip()
                            # เช็คว่ามี text ที่มีความหมาย (ยาวพอ = มีที่อยู่จริง)
                            if item_text and len(item_text) > 5:
                                valid_with_text.append(item)
                        except:
                            pass

                    if valid_with_text:
                        # *** เลือกตัวแรกสุดที่มี text จริง ***
                        target_item = valid_with_text[0]
                        log(
                            f"[/] เจอ ID 'AddressResult' และรายการย่อย {len(valid_with_text)} รายการ (มี text) -> ล็อคเป้าตัวแรก")
                        break
                    elif visible_items:
                        # เจอ ListItem แต่ไม่มี text = รายการว่าง -> ไม่ใช่ผลลัพธ์จริง
                        log("[WARN] เจอ AddressResult container แต่รายการไม่มี text -> ข้ามไป")
            except:
                pass

            # 3. [Fallback] แผนสำรอง: เผื่อหา ID ไม่เจอ ให้หากว้างๆ แบบเดิม (แต่ลดเงื่อนไขความสูงลง)
            if not target_item:
                try:
                    list_items = [i for i in window.descendants(
                        control_type="ListItem") if i.is_visible()]
                    # เอาแค่ Top > 80 (เผื่อจอเล็กมาก Header บัง)
                    valid_items = [
                        i for i in list_items if i.rectangle().top > 80]
                    
                    # [FIX] กรองเฉพาะรายการที่มี text จริงๆ
                    valid_with_text = []
                    for item in valid_items:
                        try:
                            item_text = item.window_text().strip()
                            if item_text and len(item_text) > 5:
                                valid_with_text.append(item)
                        except:
                            pass

                    if valid_with_text:
                        valid_with_text.sort(key=lambda x: x.rectangle().top)
                        target_item = valid_with_text[0]
                        log(f"[/] เจอ ListItem (Fallback Mode) {len(valid_with_text)} รายการ -> ล็อคเป้าตัวแรก")
                        break
                except:
                    pass

            time.sleep(0.25)'''

# Pattern for Fix 2: Original code block in process_receiver_details_form
OLD_PATTERN_2 = '''def process_receiver_details_form(window, fname, lname, phone, is_manual_mode, manual_data):
    """
    หน้ากรอกรายละเอียด: กรอกข้อมูลตามลำดับ 1-8 ที่ระบุมา
    """
    log("--- หน้า: รายละเอียดผู้รับ ---")
    log("...รอหน้าจอโหลด (พร้อมตรวจสอบ Popup Error)...")

    # วนลูปเช็ค Popup และรอหน้าจอ
    for _ in range(30):
        if check_error_popup(window, delay=0):
            log("...ปิด Popup แล้ว -> รอโหลดฟอร์มต่อ...")
            time.sleep(1.0)

        # ลองเช็คว่ามีช่องชื่อโผล่มาหรือยัง
        found = False
        for child in window.descendants():
            if "ชื่อ" in child.window_text() or "CustomerFirstName" in str(child.element_info.automation_id):
                found = True
                break
        if found:
            break
        time.sleep(0.5)'''

NEW_PATTERN_2 = '''def process_receiver_details_form(window, fname, lname, phone, is_manual_mode, manual_data):
    """
    หน้ากรอกรายละเอียด: กรอกข้อมูลตามลำดับ 1-8 ที่ระบุมา
    """
    log("--- หน้า: รายละเอียดผู้รับ ---")
    log("...รอหน้าจอโหลด (พร้อมตรวจสอบ Popup Error)...")

    # [FIX] ตัวแปรเพื่อติดตามว่าเจอ Error Popup หรือไม่
    found_error_popup = False

    # วนลูปเช็ค Popup และรอหน้าจอ
    for _ in range(30):
        if check_error_popup(window, delay=0):
            log("...ปิด Popup แล้ว -> รอโหลดฟอร์มต่อ...")
            found_error_popup = True  # [FIX] บันทึกว่าเจอ Error
            time.sleep(1.0)

        # ลองเช็คว่ามีช่องชื่อโผล่มาหรือยัง
        found = False
        for child in window.descendants():
            if "ชื่อ" in child.window_text() or "CustomerFirstName" in str(child.element_info.automation_id):
                found = True
                break
        if found:
            break
        time.sleep(0.5)

    # [FIX] ถ้าเจอ Error Popup = ที่อยู่ที่เลือกไม่ถูกต้อง -> บังคับเข้า Manual Mode
    if found_error_popup and not is_manual_mode:
        log("[FIX] เจอ Error Popup หลังเลือกที่อยู่ -> เปลี่ยนเป็น Manual Mode อัตโนมัติ")
        is_manual_mode = True'''

def apply_fixes(file_path):
    """Apply both fixes to a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_applied = []
        
        # Apply Fix 1 (Address list text check)
        if OLD_PATTERN_1 in content:
            content = content.replace(OLD_PATTERN_1, NEW_PATTERN_1)
            fixes_applied.append("Fix1")
        
        # Apply Fix 2 (Error popup -> Manual mode)
        if OLD_PATTERN_2 in content:
            content = content.replace(OLD_PATTERN_2, NEW_PATTERN_2)
            fixes_applied.append("Fix2")
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, fixes_applied
        else:
            return False, []
            
    except Exception as e:
        return False, [f"Error: {e}"]

def main():
    # Find all Customsize*.py files (excluding Customsize1.py which is already fixed)
    files = glob.glob(os.path.join(base_dir, "Customsize*.py"))
    
    success_count = 0
    skip_count = 0
    error_files = []
    
    print(f"=== Address List Fix Batch Script ===")
    print(f"Found {len(files)} Customsize files")
    print()
    
    for file_path in sorted(files):
        filename = os.path.basename(file_path)
        
        # Skip Customsize1.py (already fixed)
        if filename == "Customsize1.py":
            print(f"[SKIP] {filename} (already fixed)")
            skip_count += 1
            continue
        
        success, fixes = apply_fixes(file_path)
        
        if success:
            print(f"[OK] {filename} - Applied: {', '.join(fixes)}")
            success_count += 1
        elif fixes:
            print(f"[ERR] {filename} - {fixes}")
            error_files.append(filename)
        else:
            print(f"[SKIP] {filename} (pattern not found or already fixed)")
            skip_count += 1
    
    print()
    print(f"=== Summary ===")
    print(f"Fixed: {success_count} files")
    print(f"Skipped: {skip_count} files")
    print(f"Errors: {len(error_files)} files")
    
    if error_files:
        print(f"Error files: {', '.join(error_files)}")

if __name__ == "__main__":
    main()
