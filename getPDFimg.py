import fitz  # PyMuPDF
import os
import glob
import sys

# 获取当前目录下所有PDF文件
pdf_files = glob.glob("*.pdf")

if not pdf_files:
    print("当前目录下未找到PDF文件")
    sys.exit()

for pdf_file in pdf_files:
    # 创建输出文件夹（使用PDF文件名不含扩展名）
    output_folder = os.path.splitext(pdf_file)[0]
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"创建文件夹: {output_folder}")
    
    try:
        # 打开PDF
        doc = fitz.open(pdf_file)
        print(f"处理文件: {pdf_file} (共 {len(doc)} 页)")
        
        # 遍历每一页
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            
            # 获取本页所有图片
            image_list = page.get_images(full=True)
            
            # 遍历本页所有图片
            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]  # 图片的xref引用
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]  # 原始图片二进制数据
                image_ext = base_image["ext"]      # 图片原始格式扩展名
                
                # 保存图片
                image_filename = f"page_{page_index + 1}_img_{img_index + 1}.{image_ext}"
                output_path = os.path.join(output_folder, image_filename)
                
                with open(output_path, "wb") as img_file:
                    img_file.write(image_bytes)
        
        print(f"√ 成功提取 {len(image_list)} 张图片到 {output_folder}\n")
        doc.close()
    
    except Exception as e:
        print(f"处理 {pdf_file} 时出错: {str(e)}")

print("处理完成！按Enter键退出...")
input()