#!/usr/bin/env python

if __name__ == '__main__':
    import sys
    try:
        from .pipinfo import main
    except:
        from pipinfo import main
    sys.exit(main())