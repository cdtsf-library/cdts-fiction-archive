import os
import re


def clean_text(text):
    # First clean up common interference characters in spam text
    # text = re.sub(r'\[|\]|【|】||）|\(|\)', ' ', text)  # Remove brackets
    
    # Remove spam/ads patterns
    spam_patterns = [
        # Basic patterns
        r'终[%\s]*身.*?在线客服',
        r'请记住.*?在线客服',
        r'新.*?在线客服',
        r'缺失章节.*?在线客服',
        
        # QQ related patterns
        r'一[%\s]*次购买.*?[QI]Q{1,2}\d*',
        r'更多、更全小说等，请记住.*?[QI]Q{1,2}[\d%]*',
        r'更多、更全小说.*?备用[QI]Q{1,2}[\d%]*',
        r'更多、更全小说漫画视频账号等.*?[QI]Q{1,2}[\d%]*',
        r'请记住唯一联系方式.*?[QI]Q{1,2}[\d%]*',
        r'终[%\s]*身免费更新.*?[QI]Q{1,2}[\d%]*',
        r'缺失章节等，请记住.*?[QI]Q{1,2}[\d%]*',
        r'[QI]Q{1,2}\d{5,12}',  # Match QQ numbers with possible interference
        r'备用[QI]Q{1,2}[\d%]*',
        r'请记住.*?[QI]Q{1,2}',  # Added: Simple "请记住QQ" pattern
        
        # Contact info patterns
        r'更多.*?联系方式.*?备用',
        r'[\s%]*更新.*?联系方式',
        r'[%\s]*免费更新',
        r'请记住.*?联系方式.*?备用',
        r'请记住唯一联系方式[QI]Q{1,2}以及备用',
        r'更多、更全小说等，请记住唯一联系方式.*?备用',
        r'更多、更全小说漫画视频账号等.*?联系方式',
        
        # Cleanup patterns
        r'缺.*?失.*?章节',
        r'更全',
        r'小说.*?漫画.*?视频.*?账号.*?等',
        r'以及.*?备用',
        r'唯.*?一.*?联.*?系.*?方.*?式',
        r'免费更新',
        r'24小时.*?在线客服',
        r'，终身，，',
        
        # 添加新的广告模式
        r'唯一.*?联.*?系.*?方.*?式.*?在.*?线.*?客.*?服.*?[QI]Q{1,2}',
        r'唯一.*?联.*?系.*?方.*?式.*?在.*?线.*?客.*?服',
        r'24小时在线客服.*?[QI]Q{1,2}',
        
        # 添加新的更强大的广告模式
        r'更多.*?[~\s*@#^&]*.*?[QI]Q{1,2}[\d%]*',  # 处理带特殊字符的QQ广告
        r'请记[~\s*@#^&]*住.*?[QI]Q{1,2}[\d%]*',   # 处理带特殊字符的"请记住"
        r'小说漫[~\s*@#^&]*画.*?账号',             # 处理带特殊字符的小说广告
        r'[~\s*@#^&]+.*?[QI]Q{1,2}\d+',           # 处理用特殊字符分隔的QQ号
        
        # 处理特殊字符分隔的广告文本
        r'(?:[~\s*@#^&]+\w+){3,}.*?[QI]Q{1,2}',   # 连续3个以上被特殊字符分隔的词
        r'\w+[~\s*@#^&]+\w+[~\s*@#^&]+QQ',        # 特殊字符分隔的QQ相关文本
        
        # 更严格的QQ号清理
        r'[QI]Q{1,2}[\s~*@#^&]*\d+[\s~*@#^&]*\d+',  # 被分隔的QQ号
        r'备用[~\s*@#^&]*[QI]Q{1,2}',               # 被分隔的"备用QQ"
    ]
    
    # Apply patterns with case insensitive and multiline flags
    for pattern in spam_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE|re.MULTILINE)
    
    # # 清理连续的特殊字符组合（保留单个~符号）
    # text = re.sub(r'[\s*@#^&]{4,}', ' ', text)
    
    # # 清理被特殊字符包围的单个字符
    # text = re.sub(r'[~\s*@#^&]+.\s*[~\s*@#^&]+', ' ', text)
    
    # 修改特殊字符清理逻辑,保留~符号
    text = re.sub(r'\s+[@#^*$&+vPGX%]\s+', '', text)
    
    # 修改短行清理逻辑,保留包含中文字符的行
    text = re.sub(r'\n[,.，\s]?(?![^\x00-\xff])[a-zA-Z0-9,.，\s]{1,2}[,.，\s]?\n', '\n\n', text)
    
    # Modified: Remove single letters/numbers with punctuation around them
    # Changed to preserve 。 at line end and percentages
    text = re.sub(r'[,，\s](?!\d+\.?\d*%)[a-zA-Z0-9][,，\s]', '', text)
    
    # Remove single numbers at the end of paragraphs while preserving line breaks
    text = re.sub(r'(?<![\d.])\d+\s*$', '\n', text, flags=re.MULTILINE)
    
    # Clean up any remaining % characters and numbers in spam-like contexts
    # Modified to preserve percentage numbers
    text = re.sub(r'(?<!\d)%', '', text)
    
    # Clean up extra spaces and line endings
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()
    
    return text 

def process_md_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract text between markers
    main_text_pattern = r'<!-- tcd_main_text -->\n(.*?)\n<!-- tcd_main_text_end -->'
    match = re.search(main_text_pattern, content, re.DOTALL)
    
    if not match:
        print(f"No main text markers found in {file_path}")
        return
    
    main_text = match.group(1)
    cleaned_text = clean_text(main_text)
    
    # Replace the original text with cleaned text
    new_content = re.sub(
        main_text_pattern,
        f'<!-- tcd_main_text -->\n{cleaned_text}\n<!-- tcd_main_text_end -->',
        content,
        flags=re.DOTALL
    )
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                print(f"Processing {file_path}")
                process_md_file(file_path)

if __name__ == '__main__':
    # Replace with your directory path
    directory = './'
    process_directory(directory) 
