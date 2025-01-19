import os
import re

def process_files():
    # Walk through all directories
    for root, dirs, files in os.walk('.'):
        # Get all txt files
        txt_files = {f[:-4] for f in files if f.endswith('.txt')}
        # Get all md files
        md_files = {f[:-3] for f in files if f.endswith('.md')}
        
        # Find files that exist in both formats
        common_files = txt_files.intersection(md_files)
        
        for base_name in common_files:
            txt_path = os.path.join(root, base_name + '.txt')
            md_path = os.path.join(root, base_name + '.md')
            
            try:
                # Read txt content
                with open(txt_path, 'r', encoding='utf-8') as f:
                    txt_content = f.read()
                
                # Add extra newlines for markdown formatting
                txt_content = txt_content.replace('\n', '\n\n')
                
                # Escape regex special characters in the content
                txt_content = re.escape(txt_content)
                
                # Read md content
                with open(md_path, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                # Replace content between tags
                pattern = r'<!-- tcd_main_text -->.*?<!-- tcd_main_text_end -->'
                new_md_content = re.sub(pattern, 
                                      f'<!-- tcd_main_text -->\n{txt_content}\n<!-- tcd_main_text_end -->', 
                                      md_content, 
                                      flags=re.DOTALL)
                
                # Write back to md file
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(new_md_content)
                
                # Delete txt file after successful replacement
                os.remove(txt_path)
                print(f"Processed and deleted: {txt_path}")
                
            except Exception as e:
                print(f"Error processing {base_name}: {str(e)}")

if __name__ == "__main__":
    process_files() 