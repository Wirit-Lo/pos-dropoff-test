"""
Comprehensive script to apply Address List fix to ALL Python files in folder
Fixes any file that has process_receiver_address_selection or process_receiver_details_form
"""
import os
import re
import glob

# Directory containing the files
base_dir = r"d:\EWT\Automate POS\deposit"

def apply_fix_1_flexible(content):
    """Apply Fix 1: Check ListItem has text content (flexible matching)"""
    
    # Pattern to find the code block that needs fixing
    # Looking for the section with visible_items check
    pattern = re.compile(
        r'(\s+)(visible_items\s*=\s*\[\s*\n\s*i for i in children_items if i\.is_visible\(\)\])\s*\n\s*\n'
        r'\s*if visible_items:\s*\n'
        r'\s*#[^\n]*\n'  # Comment line
        r'\s*target_item = visible_items\[0\]\s*\n'
        r'\s*log\(\s*\n'
        r'\s*f?"?\[.+?\].*?AddressResult.*?{len\(visible_items\)}',
        re.MULTILINE | re.DOTALL
    )
    
    replacement = r'''\1\2

\1# [FIX] ตรวจสอบว่ารายการมี text content จริงๆ (ไม่ใช่แค่ element ว่างเปล่า)
\1valid_with_text = []
\1for item in visible_items:
\1    try:
\1        item_text = item.window_text().strip()
\1        # เช็คว่ามี text ที่มีความหมาย (ยาวพอ = มีที่อยู่จริง)
\1        if item_text and len(item_text) > 5:
\1            valid_with_text.append(item)
\1    except:
\1        pass

\1if valid_with_text:
\1    # *** เลือกตัวแรกสุดที่มี text จริง ***
\1    target_item = valid_with_text[0]
\1    log(
\1        f"[/] เจอ ID 'AddressResult' และรายการย่อย {len(valid_with_text)} รายการ (มี text)'''
    
    if pattern.search(content):
        content = pattern.sub(replacement, content, count=1)
        return content, True
    
    return content, False

def apply_fix_2_flexible(content):
    """Apply Fix 2: Auto-switch to Manual Mode on Error Popup (flexible matching)"""
    
    # Look for the function definition and the loop
    pattern = re.compile(
        r'(def process_receiver_details_form\([^)]+\):.*?\n'
        r'.*?log\("--- หน้า: รายละเอียดผู้รับ ---"\).*?\n'
        r'.*?log\("\.\.\.รอหน้าจอโหลด \(พร้อมตรวจสอบ Popup Error\)\.\.\."\).*?\n\s*\n)'
        r'(\s*# วนลูปเช็ค Popup และรอหน้าจอ\s*\n'
        r'\s*for _ in range\(\d+\):\s*\n'
        r'\s*if check_error_popup\(window, delay=\d+\):\s*\n'
        r'\s*log\("\.\.\.ปิด Popup แล้ว [^\n]+"\)\s*\n)'
        r'(\s*time\.sleep\([^)]+\))',
        re.MULTILINE | re.DOTALL
    )
    
    def replacement(match):
        indent = '    '
        return (
            match.group(1) +
            f'{indent}# [FIX] ตัวแปรเพื่อติดตามว่าเจอ Error Popup หรือไม่\n'
            f'{indent}found_error_popup = False\n\n' +
            match.group(2) +
            f'{indent * 3}found_error_popup = True  # [FIX] บันทึกว่าเจอ Error\n' +
            match.group(3)
        )
    
    new_content = pattern.sub(replacement, content, count=1)
    
    if new_content != content:
        # Also add the check after the loop
        check_pattern = re.compile(
            r'(^\s*if found:\s*\n\s*break\s*\n\s*time\.sleep\([^)]+\)\s*\n\s*\n)'
            r'(\s*# เริ่มกรอกข้อมูลตามลำดับที่ขอ)',
            re.MULTILINE
        )
        
        indent = '    '
        check_replacement = (
            r'\1' +
            f'{indent}# [FIX] ถ้าเจอ Error Popup = ที่อยู่ที่เลือกไม่ถูกต้อง -> บังคับเข้า Manual Mode\n'
            f'{indent}if found_error_popup and not is_manual_mode:\n'
            f'{indent * 2}log("[FIX] เจอ Error Popup หลังเลือกที่อยู่ -> เปลี่ยนเป็น Manual Mode อัตโนมัติ")\n'
            f'{indent * 2}is_manual_mode = True\n\n' +
            r'\2'
        )
        
        new_content = check_pattern.sub(check_replacement, new_content, count=1)
        return new_content, True
    
    return content, False

def apply_fallback_fix(content):
    """Apply fix to Fallback mode section (for valid_items check)"""
    
    pattern = re.compile(
        r'(\s+valid_items\s*=\s*\[\s*\n\s*i for i in list_items if i\.rectangle\(\)\.top\s*[>]\s*\d+\])\s*\n'
        r'\s*if valid_items:\s*\n'
        r'\s*valid_items\.sort\(key=lambda x: x\.rectangle\(\)\.top\)\s*\n'
        r'\s*target_item = valid_items\[0\]\s*\n'
        r'\s*log\(',
        re.MULTILINE | re.DOTALL
    )
    
    replacement = r'''\1
                    
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
                        log('''
    
    if pattern.search(content):
        content = pattern.sub(replacement, content, count=1)
        return content, True
    
    return content, False

def fix_file_smart(file_path):
    """Smart fix that handles various code patterns"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if doesn't have the relevant functions
        if 'process_receiver_address_selection' not in content and 'process_receiver_details_form' not in content:
            return False, ['No relevant functions']
        
        original = content
        fixes = []
        
        # Try direct pattern replacement first (exact match)
        if '# *** เลือกตัวแรกสุด (Index 0) ***' in content and 'valid_with_text' not in content:
            # Simple string replacement for exact patterns
            old_block = '''                    if visible_items:
                        # *** เลือกตัวแรกสุด (Index 0) ***
                        target_item = visible_items[0]
                        log(
                            f"[/] เจอ ID 'AddressResult' และรายการย่อย {len(visible_items)} รายการ -> ล็อคเป้าตัวแรก")
                        break'''
            
            new_block = '''                    # [FIX] ตรวจสอบว่ารายการมี text content จริงๆ (ไม่ใช่แค่ element ว่างเปล่า)
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
                        log("[WARN] เจอ AddressResult container แต่รายการไม่มี text -> ข้ามไป")'''
            
            if old_block in content:
                content = content.replace(old_block, new_block)
                fixes.append('Fix1-AddressResult')
        
        # Fix fallback mode
        if 'if valid_items:' in content and '[/] เจอ ListItem (Fallback Mode) -> ล็อคเป้าตัวแรก' in content:
            old_fallback = '''                    if valid_items:
                        valid_items.sort(key=lambda x: x.rectangle().top)
                        target_item = valid_items[0]
                        log("[/] เจอ ListItem (Fallback Mode) -> ล็อคเป้าตัวแรก")
                        break'''
            
            new_fallback = '''                    # [FIX] กรองเฉพาะรายการที่มี text จริงๆ
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
                        break'''
            
            if old_fallback in content:
                content = content.replace(old_fallback, new_fallback)
                fixes.append('Fix1-Fallback')
        
        # Fix 2: Error popup detection
        if 'process_receiver_details_form' in content and 'found_error_popup' not in content:
            old_func_start = '''def process_receiver_details_form(window, fname, lname, phone, is_manual_mode, manual_data):
    """
    หน้ากรอกรายละเอียด: กรอกข้อมูลตามลำดับ 1-8 ที่ระบุมา
    """
    log("--- หน้า: รายละเอียดผู้รับ ---")
    log("...รอหน้าจอโหลด (พร้อมตรวจสอบ Popup Error)...")

    # วนลูปเช็ค Popup และรอหน้าจอ
    for _ in range(30):
        if check_error_popup(window, delay=0):
            log("...ปิด Popup แล้ว -> รอโหลดฟอร์มต่อ...")
            time.sleep(1.0)'''
            
            new_func_start = '''def process_receiver_details_form(window, fname, lname, phone, is_manual_mode, manual_data):
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
            time.sleep(1.0)'''
            
            if old_func_start in content:
                content = content.replace(old_func_start, new_func_start)
                
                # Add the check after loop
                old_after_loop = '''        if found:
            break
        time.sleep(0.5)

    # เริ่มกรอกข้อมูลตามลำดับที่ขอ'''
                
                new_after_loop = '''        if found:
            break
        time.sleep(0.5)

    # [FIX] ถ้าเจอ Error Popup = ที่อยู่ที่เลือกไม่ถูกต้อง -> บังคับเข้า Manual Mode
    if found_error_popup and not is_manual_mode:
        log("[FIX] เจอ Error Popup หลังเลือกที่อยู่ -> เปลี่ยนเป็น Manual Mode อัตโนมัติ")
        is_manual_mode = True

    # เริ่มกรอกข้อมูลตามลำดับที่ขอ'''
                
                if old_after_loop in content:
                    content = content.replace(old_after_loop, new_after_loop)
                    fixes.append('Fix2-ErrorPopup')
        
        # Save if changed
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, fixes
        else:
            return False, []
            
    except Exception as e:
        return False, [f'Error: {e}']

def main():
    # Find all .py files
    all_py_files = glob.glob(os.path.join(base_dir, "*.py"))
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    print(f"=== Comprehensive Address List Fix ===")
    print(f"Found {len(all_py_files)} Python files")
    print()
    
    for file_path in sorted(all_py_files):
        filename = os.path.basename(file_path)
        
        # Skip this script itself
        if filename == "batch_fix_address.py" or filename == "batch_fix_all.py":
            continue
        
        success, fixes = fix_file_smart(file_path)
        
        if success:
            print(f"[OK] {filename} - Applied: {', '.join(fixes)}")
            success_count += 1
        elif fixes and 'Error' in str(fixes):
            print(f"[ERR] {filename} - {fixes}")
            error_count += 1
        else:
            skip_count += 1
    
    print()
    print(f"=== Summary ===")
    print(f"Fixed: {success_count} files")
    print(f"Skipped: {skip_count} files")
    print(f"Errors: {error_count} files")

if __name__ == "__main__":
    main()
