import requests
from rich.console import Console
from rich.markdown import Markdown
import sys
import os
from pathlib import Path
import importlib
#import re
from jsoncolor import jprint

sys.path.insert(0, str(Path(__file__).parent))
BATMAKER = str(Path(__file__).parent / 'batmaker.py')

spec = importlib.util.spec_from_file_location("pipinfo", BATMAKER)
batmaker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batmaker)


def get_package_info(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        info = data.get('info', {})
        if os.getenv('DEBUG') == "1": jprint(info)
        package_info = {
            'name': info.get('name', 'N/A'),
            'version': info.get('version', 'N/A'),
            'summary': info.get('summary', 'No summary available.'),
            'description': info.get('description', 'No description available.'),
            'home_page': info.get('home_page', 'N/A'),
            'author': info.get('author', 'N/A'),
            'author_email': info.get('author_email', 'N/A'),
            'license': info.get('license', 'N/A'),
            'keywords': info.get('keywords', 'N/A'),
            'platform': info.get('platform', 'N/A'),
            'classifiers': info.get('classifiers', []),
            'requires_python': info.get('requires_python', 'N/A'),
            'requires_dist': info.get('requires_dist', []),
            'project_urls': info.get('project_urls', {}),
        }

        return package_info
    else:
        return f"Failed to retrieve data for package '{package_name}'. Status code: {response.status_code}"

def render_markdown(markdown_text):
    console = Console()
    md = Markdown(markdown_text)
    console.print(md)

# Example usage
def install(path = None):
    print("installing ...")
    #import shutil
    #try:
        #shutil.copyfile(
            #str(Path(__file__).parent / '__main__.py'),
            #str(Path(path or r'/usr/local/bin/' if list(filter(lambda k: k in ['linux', 'linux2', 'darwin'], [sys.platform])) else os.getenv('SYSTEMROOT')) / 'pipinfo.py')
        #)
    #except Exception as e:
        #print(f"ERROR: {e}")
        #sys.exit()
    os.system(f'pip install -r {str(Path(__file__).parent / "requirements.txt")}')
    path = path or r'/usr/local/bin/' if list(filter(lambda k: k in ['linux', 'linux2', 'darwin'], [sys.platform])) else str(Path(os.getenv('SYSTEMROOT')) / 'System32')
    try:
        batmaker.Batmaker.maker(str(Path(__file__).parent / '__main__.py'), 'pipinfo', sys.executable, path)
    except Exception as e:
        print(f"ERROR: {e}")
        if "Permission denied" in str(e):
            #dirname = re.findall(r"'(.*?)\\pipinfo.bat'", str(e))
            #dirname = dirname[0] if dirname else ''
            print(f"you don\'t have permission to write file in directory ! '{path}'")
        
def get(package_name = None): 
    if not package_name:
        if not len(sys.argv) > 1:
            print("No Package name given")
            print(f"usage: {Path(__file__).stem} [-i, i, --install, install] PACKAGE_NAME")
            sys.exit()
        elif sys.argv[1] in ['-h', 'h', '--help', 'help']:
            print(f"usage: {Path(__file__).stem} [-i, i, --install, install] PACKAGE_NAME")
            sys.exit()            
    
    if sys.argv[1] in ['-i', '--install', 'install', 'i']:
        return install()
    elif len(sys.argv) > 2:
        if (os.path.isdir(sys.argv[2]) and sys.argv[1] in ['-i', '--install', 'install', 'i']):
            install(sys.argv[2])
        elif (os.path.isdir(sys.argv[1]) and sys.argv[2] in ['-i', '--install', 'install', 'i']):
            install(sys.argv[1])
            
    package_name = package_name or sys.argv[1] if not sys.argv[1] in ['-i', '--install', 'install', 'i'] else sys.argv[2] if len(sys.argv) > 2 else ''
    if package_name:
        package_info = get_package_info(package_name)
        
        if isinstance(package_info, dict):
            for key, value in package_info.items():
                if key == 'description':
                    print(f"{key}:")
                    render_markdown(value)
                else:
                    print(f"{key}: {value}")
        else:
            print(package_info)

if __name__ == '__main__':
    get()