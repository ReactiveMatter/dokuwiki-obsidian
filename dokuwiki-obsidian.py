import os
import re
import hashlib
import shutil
import urllib.parse
import uuid
from datetime import datetime

# Errors to be fixed
# Image as links

# Define the source and destination folders
source_folder = 'path/to/source'
destination_folder = 'path/to/destination'

def clean_for_filename(text):
    # Define a list of characters not allowed in file names
    forbidden_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']

    # Replace forbidden characters with "-"
    for char in forbidden_chars:
        if char != ' ':  # Skip spaces
            text = text.replace(char, '-')

    # Remove leading and trailing hyphens
    text = text.strip('-')

    # Remove leading and trailing whitespaces
    text = text.strip()

    return text

# Function to extract the first heading from DokuWiki content
def extract_first_heading(content):
    # Use regular expression to find the first heading
    match = re.search(r'====== (.+?) ======', content)
    if match:
        heading_text = match.group(1)
        return clean_for_filename(heading_text)
    else:
        return "Untitled"  # If no heading is found, use a default name

# Function to convert DokuWiki syntax to Obsidian
def convert_syntax(content, root):
    # You can add more conversion rules as needed
    
    # To preserve the code inside code block
    code_fragments = re.findall(r'(<code(.*?)>((.|\n)*?)<\/code>)', content, flags=re.MULTILINE)
    code_tuple = []

    for code_fragment in code_fragments:
        tid = uuid.uuid1().hex
        tid = tid.replace('-','')
        code_tuple.append([tid, code_fragment[0]])
        content = content.replace(code_fragment[0], tid)


    # To convert DokuWiki headings to Obsidian headings:
    content = re.sub(r'^======(.+?)======', r'# \1', content, flags=re.MULTILINE)
    content = re.sub(r'^=====(.+?)=====', r'## \1', content, flags=re.MULTILINE)
    content = re.sub(r'^====(.+?)====', r'### \1', content, flags=re.MULTILINE)
    content = re.sub(r'^===(.+?)===', r'#### \1', content, flags=re.MULTILINE)
    content = re.sub(r'^==(.+?)==', r'##### \1', content, flags=re.MULTILINE)
    content = re.sub(r'^=(.+?)=', r'####### \1', content, flags=re.MULTILINE)

    content = re.sub(r'^# .+', '', content, count=1)
    
    content = re.sub(r'^ {0,3}([*-]) ', r'\1 ', content, flags=re.MULTILINE)
    content = re.sub(r'^ {4,6}([*-]) ', r'    \1 ', content, flags=re.MULTILINE)
    content = re.sub(r'^ {7,9}([*-]) ', r'        \1 ', content, flags=re.MULTILINE)
    content = re.sub(r'^ {10,12}([*-]) ', r'            \1 ', content, flags=re.MULTILINE)

    # For index menu plugin
    content = re.sub(r'\{\{indexmenu>([^|}]+)(?:\|(?:[^}]+))?\}\}', "", content)
    
    # For include plugin; 
    # This is being done before links as later this will we converted to embedded link
    content = re.sub(r'\{\{(page|section)>([^|}]+)(?:\|(?:[^}]+))?\}\}', r"![[\2]]", content)
    
  


    # To convert DokuWiki links to Obsidian links:
    content = re.sub(r'\[\[(.+?)\]\]', lambda match: convert_link(match, root), content)
    content = re.sub(r'\{\{([^|}]+)(?:\|(?:[^}]+))?\}\}', convert_media_link, content)


    # Coverting tables
    content = re.sub(r'^[ \t]*?\^(.*)(\^|\|)$', replace_carrot, content, flags=re.MULTILINE)
    content = re.sub(r'^[ \t]*?\|[ \t]*?\^(.*)(\^|\|)$', replace_carrot, content, flags=re.MULTILINE)

    # Convert // used for italics
    content = re.sub(r'(?<!:)//(.*?)//', r'*\1*', content)

    # New line token in Dokuwiki removed
    content = re.sub(r'(?<!:)\\', '', content)
    
    content = re.sub(r'<del.*?>((.|\n)*?)<\/del>',r"~~\1~~" , content)
    
    # WRAP plugin and CKGEDIT plugin converts
    content = re.sub(r'<font.*?>((.|\n)*?)<\/font>',r"==\1==" , content)
    content = re.sub(r'<WRAP[ \t]*noprint(.*?)>((.|\n)*?)<\/WRAP>',r'\2', content)
    content = re.sub(r'<div[ \t]*(.*?)>((.|\n)*?)<\/div>',wrap_regex, content)  
    content = re.sub(r'<block[ \t]*(.*?)>((.|\n)*?)<\/block>',wrap_regex, content)  
    content = re.sub(r'<WRAP[ \t]*(.*?)>((.|\n)*?)<\/WRAP>',wrap_regex, content) 
    content = re.sub(r'<(WRAP|wrap)[ \t]*(.*?)>','', content)
    content = re.sub(r'<\/(WRAP|wrap)[ \t]*(.*?)>','', content)
    
    for code in code_tuple:
        code_content = re.sub(r'(<code(.*?)>((.|\n)*?)<\/code>)', r'\3',code[1],  flags=re.MULTILINE)
        content = re.sub(code[0], '\n```\n'+code_content.strip()+'\n```', content)

    content = re.sub(r'\n\s*\n+', '\n\n', content)
    
    return content.strip()

# Function to convert links
def convert_link(match, root):
    link = match.group(0)
    if "http://" in link:
        pattern = r'\[\[(http?://[^|]+)\s*\|\s*([^]]*)\]\]'
        return re.sub(pattern, convert_http_link, link)
    elif "https://" in link:
        pattern = r'\[\[(https?://[^|]+)\s*\|\s*([^]]*)\]\]'
        return re.sub(pattern, convert_http_link, link)
    else:
        pattern = r'\[\[(.*?)\s*\|\s*(.*?)\]\]'
        link = re.sub(pattern, lambda match: convert_internal_link(match, root), link)
        pattern = r'\[\[([^|]*)\]\]'
        link = re.sub(pattern, lambda match: convert_internal_link(match, root), link)
        return link
        

# Define a function to convert DokuWiki links to Markdown links
def convert_http_link(match):
    # Match DokuWiki links in the format [[http://path | text]]
    url = match.group(1).strip()
    # Split the URL into components
    url_parts = urllib.parse.urlsplit(url)

    # Encode the path part to replace spaces with %20
    encoded_path = urllib.parse.quote(url_parts.path)

    # Reconstruct the URL with the encoded path
    url = urllib.parse.urlunsplit((url_parts.scheme, url_parts.netloc, encoded_path, url_parts.query, url_parts.fragment))
    url = url.strip()
    text = False

    try:
        text = match.group(2).strip()
    except:
        text = False
    
    # If text is empty, use the URL as the link text
    if not text:
        return f'[{url}]({url})'
    else:
        return f'[{text}]({url})'

# Convert internal link
def convert_internal_link(match, root):
    # Match DokuWiki links in the format [[internal_link| text]]
    internal_link = match.group(1)
    text = False
    try:
        text = match.group(2)
    except:
        text = False
    

    heading = False
    if "#" in internal_link:
        heading = internal_link.split('#')[-1]

    internal_link  = internal_link.split('#')[0]

    rel_file = os.path.join(*internal_link.split(':'))
    file = os.path.join(source_folder, "pages", rel_file)+".txt"
    
    if os.path.exists(os.path.join(root, rel_file)+".txt"):
        with open(os.path.join(root, rel_file)+".txt", 'r', encoding='utf-8') as existing_file:
            content = existing_file.read()
            obsidian_path = extract_first_heading(content)
            if heading:
                heading = get_Obsidian_heading(content, heading)
                if heading:
                    obsidian_path = obsidian_path+"#"+heading
    elif os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as existing_file:
            content = existing_file.read()
            obsidian_path = extract_first_heading(content)
            if heading:
                heading = get_Obsidian_heading(content, heading)
                if heading:
                    obsidian_path = obsidian_path+"#"+heading
    else:
        obsidian_path = internal_link.split(':')[-1]

    if not text:
        return f'[[{obsidian_path}]]'
    elif text.lower() == obsidian_path.lower():
        return f'[[{text}]]'
    else:
        return f'[[{obsidian_path} | {text}]]'


# Get Obsidian heading which matches Dokuwiki heading in the internal link
def get_Obsidian_heading(content, heading):
    print("Looking for "+heading)
    obsidian_heading = False
    headings = re.findall(r'^[ \t]*((=){1,6}) (.+?) \1', content, flags=re.MULTILINE)

    for h in headings:
        doku_heading = generate_doku_hid(h[2].strip())
        input_heading = generate_doku_hid(heading.strip())
        if doku_heading.lower() == input_heading.lower():
            obsidian_heading = h[2].strip()
    return obsidian_heading

def generate_doku_hid(heading):
    doku_heading = re.sub(r' *: *','', heading)
    doku_heading = re.sub(r'[^a-zA-Z0-9:]', '_', doku_heading)
    doku_heading = re.sub(r'_{2,}','_', doku_heading)
    doku_heading = doku_heading.strip('_')
    return doku_heading

# Reverse
def reverse(s):
    str = ""
    for i in s:
        str = i + str
    return str

def contains(needles, content):
    for needle in needles:
        if needle in content:
            return True

    return False


# convert media link
def convert_media_link(match): 
    image_ext = ["jpg", "jpeg", "png", "svg"]
    match_type = "image"
    
    if len(match.groups()) > 1:
        caption = match.group(2)
    else:
        caption = False

    sub_link = match.group(1).split('?')
    
    link =  ''

    if len(sub_link) > 1:
        for i in range(len(sub_link)-1):
            link += sub_link[i]
    else:
        link = sub_link[0]

    link = link.strip()

    if not contains(image_ext, link):
        match_type = "media"

    if match_type == "image":
        if "http://" in link or "https://" in link:
            if(caption):
                return f'!['+caption+' | 300]({link})'
            else:
                return f'![Image | 300]({link})'
        else:
            return f'![[{link.split(":")[-1].strip()} | 300]]'
    else:
        if "http://" in link or "https://" in link:
            if(caption):
                return f'!['+caption+' | 300]({link})'
            else:
                return f'![Image | 400]({link})'
        else:
            return f'![[{link.split(":")[-1].strip()}]]'

    return ""

def wrap_regex(match):
    if len(match.group(2).strip()) > 0:
        return "\n> [!tip | cc-nt]\n"+re.sub(r'^','> ',match.group(2).strip(), flags=re.MULTILINE)
    else:
        return ""


def replace_carrot(match):
    
    c_count = match.group(0).count("^")
    result = match.group(0).replace("^","|").strip()
    if c_count > 1:
        result += "\n";
        for _ in range(result.count('|')-1):
            result+="|---"
        result+="|"
    return result

# Function to check if a file with the same name exists and whether it should be overwritten
def should_write(file_path, new_content, dokuwiki_path):
    
    return True
    # Get the DokuWiki file's modification date
    dokuwiki_modification_date = datetime.fromtimestamp(os.path.getmtime(dokuwiki_path))

    if not os.path.exists(file_path):
        return True  # File doesn't exist, so write it
    
    # Check if the content hash is different
    with open(file_path, 'r', encoding='utf-8') as existing_file:
        existing_content = existing_file.read()
        existing_hash = hashlib.md5(existing_content.encode()).hexdigest()
        new_hash = hashlib.md5(new_content.encode()).hexdigest()
        if existing_hash != new_hash:
            # Check if the DokuWiki file is more recent
            file_modification_date = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_modification_date < dokuwiki_modification_date:
                return True  # DokuWiki file is more recent and Hash is different so write it

    return False  # File should not be overwritten

# Walk through the source folder
for root, _, files in os.walk(os.path.join(source_folder, 'pages')):
    for file in files:
        if file.endswith('.txt'):  # Assuming DokuWiki pages have .txt extension
            dokuwiki_path = os.path.join(root, file)
            with open(dokuwiki_path, 'r', encoding='utf-8') as dokuwiki_file:
                dokuwiki_content = dokuwiki_file.read()

            title = extract_first_heading(dokuwiki_content)

            print("Converting "+ os.path.join(os.path.relpath(root, os.path.join(source_folder, 'pages')), file)+"\n")

            # Convert DokuWiki syntax to Obsidian syntax
            obsidian_content = convert_syntax(dokuwiki_content, root)

            # Build Obsidian file name
            rel_path_array = os.path.relpath(root, os.path.join(source_folder, 'pages')).split(os.path.sep)
            rel_path = os.path.join(*[r.capitalize() for r in rel_path_array])
            
            obsidian_folder= os.path.join(destination_folder, rel_path)
            
            obsidian_path = os.path.join(obsidian_folder, title+ '.md')  # Change file extension to .md

            # Check if the file should be overwritten
            if should_write(obsidian_path, obsidian_content, dokuwiki_path):
                # Create directories
                os.makedirs(os.path.dirname(obsidian_path), exist_ok=True)
                # Write the converted content to the Obsidian file
                with open(obsidian_path, 'w', encoding='utf-8') as obsidian_file:
                    obsidian_file.write(obsidian_content)
            else:
                print("The file already exits and hash matches. Overwriting skipped. \n")

# Copy media files from DokuWiki's media folder to Obsidian's media folder
media_source_folder = os.path.join(source_folder, 'media')
media_destination_folder = os.path.join(destination_folder, 'media')

for root, _, files in os.walk(media_source_folder):
    for file in files:
        media_source_path = os.path.join(root, file)
        media_destination_path = os.path.join(media_destination_folder, os.path.relpath(media_source_path, media_source_folder))
        # Check if the media file exists in the destination folder
        if not os.path.exists(media_destination_path):
            # Create directories
            os.makedirs(os.path.dirname(media_destination_path), exist_ok=True)
            shutil.copy2(media_source_path, media_destination_path)

input(f"Press any key to exit")
