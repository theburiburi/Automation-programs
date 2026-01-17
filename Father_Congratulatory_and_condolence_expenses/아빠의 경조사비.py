import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Label, Entry, Radiobutton, Button, StringVar, LEFT
import pandas as pd
import re
from collections import defaultdict 
try:
    import pytesseract
    from PIL import Image
except ImportError:
    messagebox.showerror("라이브러리 오류", "pytesseract 또는 pillow가 설치되지 않았습니다.\n'pip3 install pytesseract pillow'를 실행하세요.")
    exit()

# --- 1. 메인 창을 먼저 생성! ---
root = tk.Tk()
root.title("경조사비 정산 프로그램 v2.0 (새 항목 추가)")
root.geometry("1200x800") 

# --- 2. Tkinter 변수 선언 ---
selected_mode = tk.StringVar(value=" (엑셀을 먼저 선택하세요) ")
file_paths = { 
    "excel": "", 
    "images": [], 
    "new_excel": "" 
}

# --- 3. 헬퍼(Helper) 함수들 (실제 로직) ---

# --- (v1.9와 동일) ---
# '축의금' 시트는 '조회용'이므로 '이름'을 인덱스로 읽는 것이 맞습니다.
def load_guest_map(excel_file):
    """(로직 1) '축의금' 시트를 읽어 기준 정보(이름:관계 맵)와 '항목'(열)을 만듭니다."""
    print("Helper 1: '축의금' 시트에서 기준 정보를 로드합니다...")
    try:
        # '이름' 열을 인덱스(행 이름)로 지정
        df_base = pd.read_excel(excel_file, sheet_name='축의금', index_col='이름', engine='openpyxl')
        
        guest_map = defaultdict(list)
        for name, row in df_base.iterrows():
            for col in df_base.columns:
                if pd.notna(row[col]) and row[col] > 0:
                    guest_map[name].append(col)
        
        guest_map = dict(guest_map)
        print(f"기준 정보 로드 완료: {guest_map}")
        categories = list(df_base.columns)
        print(f"기준 항목(열) 로드 완료: {categories}")
        
        return guest_map, categories
        
    except Exception as e:
        messagebox.showerror("엑셀 읽기 오류", f"'축의금' 시트를 읽는 중 오류 발생:\n{e}")
        return None, None

# --- (v1.9와 동일) ---
def extract_info_from_image(image_file, guest_names, categories):
    """(로직 2 - OCR) OCR로 이미지에서 이름과 금액을 추출합니다."""
    print(f"Helper 2: '{image_file}'에서 OCR을 실행합니다...")
    try:
        ocr_text = pytesseract.image_to_string(Image.open(image_file), lang='kor')
        print(f"--- OCR ({image_file.split('/')[-1]}) ---")
        print(ocr_text)
        print("---------------------------------")
        
        found_name = None
        found_amount = 0
        amount_position = 0 
        
        amount_match = re.search(r"([\d,]+)\s*원", ocr_text)
        if not amount_match:
            print("OCR 결과에서 금액('...원')을 찾지 못했습니다.")
        else:
            found_amount = int(amount_match.group(1).replace(",", ""))
            amount_position = amount_match.start()
            print(f"금액 찾음: {found_amount} (at pos {amount_position})")

        all_names_found = []
        for name in guest_names:
            for match in re.finditer(re.escape(name), ocr_text):
                all_names_found.append( (name, match.start()) )
        for match in re.finditer(r"([가-힣]{2,4})", ocr_text):
            name = match.group(1)
            if name not in guest_names:
                 all_names_found.append( (name, match.start()) )

        closest_name = None
        closest_distance = float('inf')
        
        for name, name_pos in all_names_found:
            if amount_match: 
                if name_pos < amount_position: 
                    distance = amount_position - name_pos
                    if distance < closest_distance:
                        if (name not in categories) and (name != "비고"):
                            closest_distance = distance
                            closest_name = name
            else: 
                if (name not in categories) and (name != "비고"):
                    closest_name = name
                    break 

        if closest_name:
            found_name = closest_name
            print(f"가장 근접한 이름 찾음: {found_name}")
        else:
            print("유효한 이름을 찾지 못했습니다.")

        return found_name, found_amount
    except Exception as e:
        print(f"OCR 오류: {e}")
        return None, 0

# --- (★수정됨 v2.0★: 시트별로 인덱스 저장 여부 다르게) ---
def save_excel_file(excel_file, dfs):
    """(로직 3) 모든 시트(dfs)를 엑셀 파일에 '한 번만' 덮어쓰기 저장합니다."""
    print(f"Helper 3: '{excel_file}' 파일에 모든 변경사항을 저장합니다...")
    try:
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            for sheet, df in dfs.items():
                # (★v2.0★) 
                # '축의금' 시트는 '이름' 인덱스가 있으므로 'index=True'
                # 나머지 시트('부의금' 등)는 인덱스가 없으므로 'index=False'
                if sheet == '축의금':
                    df.to_excel(writer, sheet_name=sheet, index=True)
                else:
                    df.to_excel(writer, sheet_name=sheet, index=False)
        return True
    except Exception as e:
        messagebox.showerror("엑셀 쓰기 오류", f"엑셀 파일 저장 중 오류 발생:\n{e}\n\n(혹시 엑셀 파일이 열려있지 않은지 확인해주세요)")
        return False

# --- (v1.9와 동일) ---
def open_correction_popup(parent, title_info, ocr_name, ocr_amount, possible_relations, all_categories, popup_result):
    """(로직 4) 수동 확인/수정 팝업창을 엽니다."""
    
    popup = Toplevel(parent)
    popup.title("수동 확인/수정")
    popup.geometry("500x550") 
    popup.grab_set() 
    
    name_var = StringVar(value=ocr_name if ocr_name else "")
    amount_var = StringVar(value=str(ocr_amount) if ocr_amount > 0 else "")
    relation_var = StringVar()
    
    font_large = ("Helvetica", 14)
    font_medium = ("Helvetica", 12)
    font_bold = ("Helvetica", 12, "bold")
    
    Label(popup, text=f"입력: {title_info}", font=("Helvetica", 11, "italic")).pack(pady=(10,5))
    
    if not ocr_name or ocr_amount == 0:
        Label(popup, text="OCR 인식 실패. 직접 입력해주세요.", fg="red", font=font_bold).pack(pady=(5,10))
    elif len(possible_relations) > 1:
         Label(popup, text="동명이인입니다. 관계를 선택해주세요.", fg="blue", font=font_bold).pack(pady=(5,10))
    elif not possible_relations:
        Label(popup, text="신규 인원입니다. 저장할 항목을 선택해주세요.", fg="green", font=font_bold).pack(pady=(5,10))
    else:
        Label(popup, text="OCR 결과입니다. 확인 또는 수정해주세요.", fg="gray", font=font_bold).pack(pady=(5,10))

    Label(popup, text="이름:", font=font_large).pack()
    Entry(popup, textvariable=name_var, font=font_large, width=30).pack(pady=(5,10), ipady=5)
    Label(popup, text="금액:", font=font_large).pack()
    Entry(popup, textvariable=amount_var, font=font_large, width=30).pack(pady=(5,20), ipady=5)
    Label(popup, text="관계 (저장할 열):", font=font_large).pack(pady=(0,5))
    
    display_categories = [cat for cat in all_categories if cat != '비고']
    
    for rel in display_categories:
        Radiobutton(popup, text=rel, variable=relation_var, value=rel, font=font_medium).pack(anchor="w", padx=100)
    
    Radiobutton(popup, text="비고 (신규 인원)", variable=relation_var, value="비고", font=font_medium).pack(anchor="w", padx=100, pady=(5,0))
    
    if possible_relations:
        relation_var.set(possible_relations[0])
    else:
        relation_var.set("비고")

    def on_ok():
        try:
            name = name_var.get().strip()
            amount = int(amount_var.get().replace(",", ""))
            column = relation_var.get()
            if not name or amount == 0 or not column:
                messagebox.showwarning("입력 오류", "이름, 금액, 관계를 모두 입력/선택해야 합니다.", parent=popup)
                return
            popup_result["action"] = "ok"
            popup_result["name"] = name
            popup_result["amount"] = amount
            popup_result["column"] = column
            popup.destroy()
        except ValueError:
            messagebox.showwarning("입력 오류", "금액은 숫자만 입력해야 합니다 (예: 100000)", parent=popup)
        except Exception as e:
            messagebox.showerror("오류", f"오류 발생: {e}", parent=popup)
            
    def on_skip():
        popup_result["action"] = "skip"
        popup.destroy()

    button_frame = tk.Frame(popup)
    button_frame.pack(pady=(20, 10))
    
    Button(button_frame, text="확인", font=font_bold, bg="lightblue", command=on_ok).pack(side=LEFT, expand=True, fill="x", padx=30, ipady=5)
    Button(button_frame, text="건너뛰기", font=font_bold, command=on_skip).pack(side=LEFT, expand=True, fill="x", padx=30, ipady=5)
    popup_result["window"] = popup


# --- 4. 버튼 클릭 함수 (GUI 이벤트 핸들러) --- 
# --- (v1.9와 동일) ---
def select_excel_file():
    """'1. 기준 엑셀 파일 선택' 버튼 클릭 시"""
    filepath = filedialog.askopenfilename(title="1. '축의금'/'부의금' 시트가 있는 원본 엑셀 선택", filetypes=[("Excel files", "*.xlsx")])
    if not filepath: return
    file_paths["excel"] = filepath
    excel_path_label.config(text=f"엑셀 파일: {filepath.split('/')[-1]}")
    file_paths["images"] = []
    file_paths["new_excel"] = ""
    image_path_label.config(text="이미지 파일: (선택되지 않음)")
    excel_input_path_label.config(text="새 엑셀 파일: (선택되지 않음)")
    try:
        xls = pd.ExcelFile(filepath, engine='openpyxl')
        sheet_names = xls.sheet_names
        menu = mode_dropdown["menu"]; menu.delete(0, "end")
        for sheet in sheet_names:
            menu.add_command(label=sheet, command=tk._setit(selected_mode, sheet))
        if sheet_names:
            selected_mode.set(sheet_names[0]); mode_dropdown.config(state="normal")
        else:
            selected_mode.set(" (시트 없음)"); mode_dropdown.config(state="disabled")
    except Exception as e:
        messagebox.showerror("엑셀 읽기 오류", f"엑셀 파일을 읽는 중 오류가 발생했습니다:\n{e}")
        selected_mode.set(" (파일 읽기 오류)"); mode_dropdown.config(state="disabled")

def select_image_file():
    """'2a. 스크린샷 선택' 버튼 클릭 시"""
    filepaths = filedialog.askopenfilenames(title="2a. 송금 내역 스크린샷 '여러 개' 선택 가능", filetypes=[("Image files", "*.png *.jpg *.jpeg")])
    if filepaths:
        file_paths["images"] = filepaths
        image_path_label.config(text=f"{len(filepaths)}개의 이미지 파일 선택됨")
        file_paths["new_excel"] = ""
        excel_input_path_label.config(text="새 엑셀 파일: (선택되지 않음)")

def select_new_excel_file():
    """'2b. 새 엑셀(입금목록) 파일 선택' 버튼 클릭 시"""
    filepath = filedialog.askopenfilename(title="2b. '이름'과 '금액' 열이 있는 새 엑셀 파일 선택", filetypes=[("Excel files", "*.xlsx")])
    if filepath:
        file_paths["new_excel"] = filepath
        excel_input_path_label.config(text=f"새 엑셀 파일: {filepath.split('/')[-1]}")
        file_paths["images"] = []
        image_path_label.config(text="이미지 파일: (선택되지 않음)")


# --- 5. 메인 함수 (★ 실행 ★ 버튼 클릭 시) ---
# --- (★수정됨 v2.0★: '새 항목 추가' 로직) ---
def start_processing():
    """'★ 실행 ★' 버튼 클릭 시: 선택된 입력 방식에 따라 일괄 처리"""
    
    mode = selected_mode.get()
    excel_file = file_paths["excel"]
    image_files = file_paths["images"]
    new_excel_file = file_paths["new_excel"]

    if not excel_file or (not image_files and not new_excel_file) or (mode.startswith(" (") and mode.endswith(")")):
        messagebox.showwarning("입력 오류", "1. 기준 엑셀\n2. 입력 파일 (스크린샷 *또는* 새 엑셀)\n3. 유효한 시트(모드)\n\n위 3가지를 모두 선택해야 합니다.")
        return

    print(f"--- (v2.0) 일괄 처리 시작 ---")
    print(f"대상 파일: {excel_file}, 목표 시트: {mode}")
    try:
        # (v2.0) '축의금'(조회용) 맵과 항목(열) 이름을 로드
        guest_map, categories = load_guest_map(excel_file)
        if guest_map is None: return
        
        # (★v2.0★) 
        # '모든' 시트를 메모리로 로드.
        # '축의금' 시트만 '이름'을 인덱스로 사용하고,
        # '부의금' 같은 나머지 시트(거래 장부)는 '인덱스 없이' (index_col=None) 로드
        
        # 1. 엑셀 파일의 모든 시트 이름을 먼저 읽음
        xls = pd.ExcelFile(excel_file, engine='openpyxl')
        sheet_names = xls.sheet_names
        
        # 2. 시트별로 다르게 로드
        dfs = {}
        for sheet in sheet_names:
            if sheet == '축의금':
                # '축의금'은 기준 정보이므로 '이름'을 인덱스로 로드
                dfs[sheet] = pd.read_excel(xls, sheet_name=sheet, index_col='이름', engine='openpyxl')
            else:
                # '부의금' 등 나머지 시트는 '새 항목 추가'를 위해 인덱스 없이 로드
                dfs[sheet] = pd.read_excel(xls, sheet_name=sheet, index_col=None, engine='openpyxl')
        
        success_count = 0
        failed_items = []
        
        # (v1.9와 동일)
        if image_files:
            # --- (A) OCR (스크린샷) 모드 (v1.6 '무조건 팝업' 방식) ---
            print(f"모드: (A) OCR 처리. 총 {len(image_files)}개 이미지.")
            for image_file in image_files:
                image_name = image_file.split('/')[-1]
                print(f"\n--- {image_name} 처리 중 (OCR) ---")
                found_name, found_amount = extract_info_from_image(image_file, guest_map.keys(), categories)
                relations = guest_map.get(found_name, [])
                
                popup_result = {"action": "skip"}
                open_correction_popup(root, f"이미지: {image_name}", found_name, found_amount, relations, categories, popup_result)
                root.wait_window(popup_result["window"])
                
                if popup_result["action"] == "ok":
                    name_to_save, amount_to_save, column_to_update = popup_result["name"], popup_result["amount"], popup_result["column"]
                    
                    # (★v2.0★) .loc (덮어쓰기) 대신 '새 항목 추가' 로직
                    new_row = {'이름': name_to_save, column_to_update: amount_to_save}
                    # (★v2.0★) 대상 시트(dfs[mode])의 열(columns)을 기준으로 새 DataFrame 생성
                    new_row_df = pd.DataFrame([new_row], columns=dfs[mode].columns)
                    dfs[mode] = pd.concat([dfs[mode], new_row_df], ignore_index=True)
                    
                    print(f"새 항목 추가: [{mode}] 시트, 행='{name_to_save}', 열='{column_to_update}', 값={amount_to_save}")
                    success_count += 1
                else:
                    failed_items.append(f"이미지: {image_name} (수동으로 건너뜀)")
            
        # (v1.9와 동일)
        elif new_excel_file:
            # --- (B) 새 엑셀 모드 (v1.7 '문제시 팝업' 방식) ---
            print(f"모드: (B) 새 엑셀 처리. 파일: {new_excel_file.split('/')[-1]}")
            df_input = pd.read_excel(new_excel_file)
            
            if '이름' not in df_input.columns or '금액' not in df_input.columns:
                 messagebox.showerror("새 엑셀 오류", "'새 엑셀 파일'에는 '이름' 열과 '금액' 열이 반드시 포함되어야 합니다.")
                 return
            
            for index, row in df_input.iterrows():
                found_name = str(row['이름']).strip()
                found_amount = row['금액']
                print(f"\n--- {index+1}번째 행 처리 중 (Excel): {found_name}, {found_amount} ---")
                
                relations = guest_map.get(found_name, [])
                is_new_guest = (len(relations) == 0)
                is_duplicate = (len(relations) > 1)

                name_to_save = found_name
                amount_to_save = found_amount
                column_to_update = None
                
                if is_duplicate or is_new_guest:
                    print(f"!! 문제 발생: {'동명이인' if is_duplicate else '신규 인원'}. 수동 확인 팝업을 띄웁니다.")
                    popup_result = {"action": "skip"}
                    open_correction_popup(root, f"엑셀 행: {found_name}", found_name, found_amount, relations, categories, popup_result)
                    root.wait_window(popup_result["window"])
                    
                    if popup_result["action"] == "ok":
                        name_to_save, amount_to_save, column_to_update = popup_result["name"], popup_result["amount"], popup_result["column"]
                    else:
                        failed_items.append(f"엑셀 행: {found_name} (수동으로 건너뜀)")
                        continue
                else:
                    column_to_update = relations[0]
                
                # (★v2.0★) .loc (덮어쓰기) 대신 '새 항목 추가' 로직
                new_row = {'이름': name_to_save, column_to_update: amount_to_save}
                # (★v2.0★) 대상 시트(dfs[mode])의 열(columns)을 기준으로 새 DataFrame 생성
                new_row_df = pd.DataFrame([new_row], columns=dfs[mode].columns)
                dfs[mode] = pd.concat([dfs[mode], new_row_df], ignore_index=True)
                
                print(f"새 항목 추가: [{mode}] 시트, 행='{name_to_save}', 열='{column_to_update}', 값={amount_to_save}")
                success_count += 1
        
        # (공통) 최종 저장
        if success_count > 0:
            if not save_excel_file(excel_file, dfs): # <- v2.0 수정된 저장 함수 호출
                return
        
        result_message = f"총 {success_count}개 항목 처리에 성공했습니다."
        if failed_items:
            result_message += "\n\n[실패/건너뛴 항목]\n" + "\n".join(failed_items)
        
        messagebox.showinfo("일괄 처리 완료", result_message)
        print("--- 일괄 처리 완료 ---")

    except Exception as e:
        messagebox.showerror("전역 오류", f"처리 중 예상치 못한 오류가 발생했습니다:\n{e}")
    finally:
        print("--- 처리 완료 ---")


# --- 6. GUI 위젯 배치 (창에 보이는 요소들) ---
# --- (v1.9와 동일) ---

font_title = ("Helvetica", 24, "bold")
font_button = ("Helvetica", 16)
font_label = ("Helvetica", 12)
font_dropdown = ("Helvetica", 14)
font_main_button = ("Helvetica", 18, "bold")

pad_x = 40
pad_y_outer = 15
pad_y_inner = 5
pad_y_section = 25
pad_y_main_button = 40
ipad_y_button = 10 

title_label = tk.Label(root, text="경조사비 자동 정산", font=font_title)
title_label.pack(pady=pad_y_section)

excel_button = tk.Button(root, text="1. 기준 엑셀 파일 선택 (.xlsx)", command=select_excel_file, font=font_button)
excel_button.pack(pady=(pad_y_outer, pad_y_inner), padx=pad_x, fill="x", ipady=ipad_y_button)
excel_path_label = tk.Label(root, text="엑셀 파일: (선택되지 않음)", font=font_label)
excel_path_label.pack(pady=pad_y_inner)

separator1 = tk.Frame(root, height=2, bd=1, relief="sunken")
separator1.pack(fill="x", padx=pad_x, pady=pad_y_section)

image_button = tk.Button(root, text="2a. 스크린샷 선택 (OCR 방식)", command=select_image_file, font=font_button)
image_button.pack(pady=(pad_y_outer, pad_y_inner), padx=pad_x, fill="x", ipady=ipad_y_button)
image_path_label = tk.Label(root, text="이미지 파일: (선택되지 않음)", font=font_label)
image_path_label.pack(pady=pad_y_inner)

excel_input_button = tk.Button(root, text="2b. 새 엑셀 파일 선택 (목록 방식)", command=select_new_excel_file, font=font_button)
excel_input_button.pack(pady=(pad_y_outer, pad_y_inner), padx=pad_x, fill="x", ipady=ipad_y_button)
excel_input_path_label = tk.Label(root, text="새 엑셀 파일: (선택되지 않음)", font=font_label)
excel_input_path_label.pack(pady=pad_y_inner)

separator2 = tk.Frame(root, height=2, bd=1, relief="sunken")
separator2.pack(fill="x", padx=pad_x, pady=pad_y_section)

mode_label = tk.Label(root, text="3. 어떤 내역을 추가할까요?", font=font_button)
mode_label.pack(pady=(pad_y_outer, pad_y_inner))
mode_dropdown = tk.OptionMenu(root, selected_mode, " (엑셀을 먼저 선택하세요) ")
mode_dropdown.config(font=font_dropdown, width=30)
mode_dropdown.pack(pady=pad_y_inner, ipady=5)

process_button = tk.Button(
    root, text="★ 일괄 처리 시작 ★", 
    font=font_main_button, 
    bg="lightblue", 
    command=start_processing
)
process_button.pack(pady=pad_y_main_button, padx=pad_x, fill="x", ipady=ipad_y_button + 5) 

# --- 7. 프로그램 창 실행 ---
root.mainloop()