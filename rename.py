import os
import re
import shutil
import sys
from pathlib import Path

def get_user_input():
    """获取用户输入的正则表达式和重命名模板"""
    print("=" * 50)
    print("漫画文件批量重命名工具")
    print("=" * 50)
    print("请按照提示输入信息，可以随时输入 'exit' 退出程序\n")
    
    # 获取文件扩展名
    while True:
        file_ext = input("请输入要处理的文件扩展名 (如 cbz, zip, epub): ").strip().lower()
        if file_ext == "exit":
            sys.exit(0)
        if not file_ext:
            print("错误: 扩展名不能为空")
            continue
        if file_ext.startswith("."):
            file_ext = file_ext[1:]
        break
    
    # 获取卷号匹配正则表达式
    while True:
        print("\n请输入正则表达式来匹配卷号:")
        print("示例: 'vol\.(\d+)' 会匹配文件名中的 'vol.01', 'vol.02' 等")
        print("       '第(\d+)卷' 会匹配 '第01卷', '第02卷' 等")
        print("       '(\d+)' 会匹配文件名中的第一个数字序列")
        regex_pattern = input("> ").strip()
        
        if regex_pattern == "exit":
            sys.exit(0)
        
        if not regex_pattern:
            print("错误: 正则表达式不能为空")
            continue
            
        try:
            re.compile(regex_pattern)
            break
        except re.error as e:
            print(f"正则表达式错误: {str(e)}")
            continue
    
    # 获取重命名模板
    while True:
        print("\n请输入重命名模板 (使用 {vol} 表示卷号):")
        print("示例: '炎拳_Vol_{vol}' 会生成 '炎拳_Vol_01', '炎拳_Vol_02'")
        print("       '漫画_{vol:03d}' 会生成 '漫画_001', '漫画_002'")
        print("       'Series_{vol:02d}' 会生成 'Series_01', 'Series_02'")
        template = input("> ").strip()
        
        if template == "exit":
            sys.exit(0)
            
        if not template:
            print("错误: 模板不能为空")
            continue
            
        if "{vol" not in template:
            print("警告: 模板中未包含 {vol} 或 {vol:格式}，卷号将不会被格式化")
            
        break
    
    # 获取起始卷号
    start_vol = 1
    while True:
        start_input = input("\n请输入起始卷号 (默认为1): ").strip()
        if start_input == "exit":
            sys.exit(0)
        if not start_input:
            break
        try:
            start_vol = int(start_input)
            if start_vol <= 0:
                print("错误: 卷号必须大于0")
                continue
            break
        except ValueError:
            print("错误: 请输入有效的数字")
    
    return file_ext, regex_pattern, template, start_vol

def find_files(file_ext):
    """查找匹配的文件"""
    current_dir = Path.cwd()
    files = sorted([f for f in current_dir.glob(f"*.{file_ext}") if f.is_file()])
    
    if not files:
        print(f"\n错误: 当前目录下未找到 .{file_ext} 文件")
        sys.exit(1)
    
    print(f"\n找到 {len(files)} 个 .{file_ext} 文件:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")
    
    return files

def preview_rename(files, regex_pattern, template, start_vol):
    """预览重命名结果"""
    print("\n重命名预览:")
    print("-" * 60)
    print(f"{'原文件名':<40} {'新文件名':<40}")
    print("-" * 60)
    
    rename_plan = []
    current_vol = start_vol
    
    for file in files:
        filename = file.stem  # 不含扩展名
        new_name = None
        
        # 尝试匹配卷号
        match = re.search(regex_pattern, filename)
        if match:
            try:
                # 尝试提取卷号
                vol_str = match.group(1)
                vol_num = int(vol_str) if vol_str.isdigit() else current_vol
            except (IndexError, ValueError):
                vol_num = current_vol
        else:
            vol_num = current_vol
        
        # 格式化新文件名
        try:
            # 尝试格式化卷号
            if "{vol:" in template:
                new_name = template.format(vol=vol_num)
            else:
                new_name = template.format(vol=str(vol_num).zfill(2))
        except KeyError:
            # 如果格式化失败，直接替换 {vol}
            new_name = template.replace("{vol}", str(vol_num).zfill(2))
        
        # 添加扩展名
        new_filename = f"{new_name}.{file.suffix[1:]}"
        
        # 保存重命名计划
        rename_plan.append((file, file.parent / new_filename))
        
        # 显示预览
        orig_display = filename[:37] + "..." if len(filename) > 40 else filename
        new_display = new_name[:37] + "..." if len(new_name) > 40 else new_name
        print(f"{orig_display:<40} -> {new_display:<40}")
        
        current_vol += 1
    
    print("-" * 60)
    return rename_plan

def confirm_and_rename(rename_plan):
    """确认并执行重命名"""
    while True:
        choice = input("\n是否执行重命名? (y=执行, n=重新输入, p=预览, c=检查冲突, x=退出): ").lower()
        
        if choice == 'y':
            break
        elif choice == 'n':
            return False
        elif choice == 'x':
            sys.exit(0)
        elif choice == 'p':
            print("\n重命名预览:")
            print("-" * 60)
            print(f"{'原文件名':<40} {'新文件名':<40}")
            print("-" * 60)
            for old, new in rename_plan:
                old_display = old.name[:37] + "..." if len(old.name) > 40 else old.name
                new_display = new.name[:37] + "..." if len(new.name) > 40 else new.name
                print(f"{old_display:<40} -> {new_display:<40}")
            print("-" * 60)
        elif choice == 'c':
            check_conflicts(rename_plan)
        else:
            print("无效选择，请重新输入")
    
    # 检查冲突
    conflict = check_conflicts(rename_plan)
    if conflict:
        print("存在冲突，无法执行重命名")
        return False
    
    # 执行重命名
    print("\n正在重命名文件...")
    for old, new in rename_plan:
        try:
            old.rename(new)
            print(f"  已重命名: {old.name} -> {new.name}")
        except Exception as e:
            print(f"  重命名失败 {old.name}: {str(e)}")
    
    print("\n重命名完成!")
    return True

def check_conflicts(rename_plan):
    """检查重命名冲突"""
    conflict = False
    
    # 检查重复目标文件名
    target_names = [new.name for _, new in rename_plan]
    duplicates = set([name for name in target_names if target_names.count(name) > 1])
    
    if duplicates:
        conflict = True
        print("\n发现冲突 - 多个文件将重命名为相同名称:")
        for dup in duplicates:
            print(f"  冲突: {dup}")
    
    # 检查文件是否已存在
    existing_files = []
    for old, new in rename_plan:
        if new.exists() and old != new:
            existing_files.append(new.name)
    
    if existing_files:
        conflict = True
        print("\n发现冲突 - 目标文件已存在:")
        for file in existing_files:
            print(f"  文件已存在: {file}")
    
    return conflict

def main():
    while True:
        # 获取用户输入
        file_ext, regex_pattern, template, start_vol = get_user_input()
        
        # 查找文件
        files = find_files(file_ext)
        
        # 预览重命名
        rename_plan = preview_rename(files, regex_pattern, template, start_vol)
        
        # 确认并执行重命名
        success = confirm_and_rename(rename_plan)
        if success:
            break
        
        # 询问是否继续
        while True:
            choice = input("\n是否继续? (y=继续, n=退出): ").lower()
            if choice == 'n':
                sys.exit(0)
            elif choice == 'y':
                break
            else:
                print("无效选择，请输入 'y' 或 'n'")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已中止")
        sys.exit(0)