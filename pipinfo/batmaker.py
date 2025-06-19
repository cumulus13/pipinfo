import os
import sys
from configset import configset
from pathlib import Path
from make_colors import make_colors
from pydebugger.debug import debug
import argparse

class Batmaker(object):
    CONFIGNAME = str(Path(__file__).parent / 'batmaker.ini')
    CONFIG = configset(CONFIGNAME)
    ROOT_PATH = CONFIG.get_config('general', 'root') or r'c:\TOOLS\pyx' if os.path.isdir(r'c:\TOOLS\pyx') else None
    if not ROOT_PATH:
        ROOT_PATH = r'/usr/local/bin/' if list(filter(lambda k: k in ['linux', 'linux2', 'darwin'], [sys.platform])) else str(Path(os.getenv('SYSTEMROOT')) / 'System32')

    @classmethod
    def maker(self, filepath, name = None, exepath = None, rootpath = None, quite = False):
        rootpath = rootpath or self.ROOT_PATH
        if name:
            if os.path.splitext(name)[-1] == '.bat':
                file_name = os.path.join(rootpath, name)
            else:
                file_name = os.path.join(rootpath, name) + ".bat"
        else:
            file_name = os.path.join(rootpath, os.path.splitext(os.path.basename(filepath))[0]) + ".bat"
            
        print(make_colors("file be created:", 'b', 'y'), make_colors(file_name, 'lw', 'bl'))
        
        if not Path(file_name).is_file():
            file_create = open(file_name, 'wb')
        else:
            if not quite:
                q = input(make_colors(f"file {make_colors(f'{file_name} already exists !', 'lw', 'r')}", 'lw', 'bl') + ", " + make_colors("Overwrite [y/n]:", 'b', 'y') + " ")
                if q and q.lower() in ['y', 'yes']:
                    file_create = open(file_name, 'wb')
            else:
                file_create = open(file_name, 'wb')
            
            
        #string_create = """@echo off\n"%s" %%*"""%(os.path.abspath(path))
        exepath = '"' + exepath + '" ' if exepath else ''
        string_create = f"""@echo off\n{exepath}"{os.path.abspath(filepath)}" %*"""
        print(make_colors("string_create", 'lc'), make_colors(string_create, 'lw', 'bl'))
        file_create.write(bytes(string_create, encoding = 'utf-8'))
        file_create.close()

    @classmethod
    def usage(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('FILE', action = 'store', help = 'Main file')
        parser.add_argument('-n', '--name', action = 'store', help = 'Save as name')
        parser.add_argument('-x', '--exe', action = 'store', help = 'Main executable')
        parser.add_argument('-r', '--root', action = 'store', help = 'Root path, where is script be created')
        parser.add_argument('-q', '--quite', action = 'store_true', help = 'Suppres any question / overwrite if exists')
        
        if len(sys.argv) == 1:
            parser.print_help()
        else:
            args = parser.parse_args()
            self.maker(args.FILE, args.name, args.exe, args.root, args.quite)
            
        
        
if __name__ == '__main__':
    Batmaker.usage()
