import os
import zipfile
import shutil
from collections import defaultdict

def process_directory():
    # 获取当前工作目录
    base_dir = os.getcwd()
    
    # 创建目标目录a和b
    dir_a = os.path.join(base_dir, 'a')
    dir_b = os.path.join(base_dir, 'b')
    os.makedirs(dir_a, exist_ok=True)
    os.makedirs(dir_b, exist_ok=True)
    
    # 用于记录末端文件夹和待处理文件
    leaf_folders = set()
    orphan_files = defaultdict(list)  # 存储非末端文件夹中的文件
    
    # 第一次遍历：识别末端文件夹（避开a和b目录）
    for root, dirs, files in os.walk(base_dir):
        # 跳过输出目录a和b
        if 'a' in dirs:
            dirs.remove('a')
        if 'b' in dirs:
            dirs.remove('b')
            
        # 如果是末端文件夹（没有子目录）且不在a/b目录中
        if not dirs and not root.startswith(dir_a) and not root.startswith(dir_b):
            leaf_folders.add(root)
    
    # 第二次遍历：收集非末端文件夹中的文件（避开a和b目录）
    for root, dirs, files in os.walk(base_dir):
        # 跳过输出目录a和b
        if 'a' in dirs:
            dirs.remove('a')
        if 'b' in dirs:
            dirs.remove('b')
            
        # 跳过根目录、末端文件夹和a/b目录
        if root == base_dir or root in leaf_folders or root.startswith(dir_a) or root.startswith(dir_b):
            continue
            
        # 如果有文件存在，记录相对路径
        if files:
            rel_path = os.path.relpath(root, base_dir)
            orphan_files[rel_path] = files
    
    # 处理末端文件夹（压缩文件）
    for folder in leaf_folders:
        folder_name = os.path.basename(folder)
        zip_path = os.path.join(dir_a, f"{folder_name}.zip")
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                if os.path.isfile(item_path):
                    # 将文件添加到ZIP（不保留目录结构）
                    zipf.write(item_path, arcname=item)
    
    # 处理非末端文件夹中的文件（复制到目录b）
    for rel_path, files in orphan_files.items():
        src_dir = os.path.join(base_dir, rel_path)
        dest_dir = os.path.join(dir_b, rel_path)
        
        # 创建目标目录结构
        os.makedirs(dest_dir, exist_ok=True)
        
        # 复制文件
        for file in files:
            src = os.path.join(src_dir, file)
            dest = os.path.join(dest_dir, file)
            shutil.copy2(src, dest)  # 保留文件元数据

if __name__ == "__main__":
    process_directory()
    print("操作完成！结果保存在目录 'a' 和 'b' 中")