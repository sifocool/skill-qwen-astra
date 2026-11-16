"""Profile calls in a trusted target without breaking pickle's __main__ binding."""
import json
import os
import runpy
import sys

target=os.path.realpath(sys.argv[1])
seen=set()
def profile(frame,event,arg):
    if event=='call' and os.path.realpath(frame.f_code.co_filename)==target:
        seen.add(frame.f_code.co_qualname)
sys.argv=sys.argv[1:]
sys.setprofile(profile)
try:
    runpy.run_path(target,run_name='__main__')
finally:
    sys.setprofile(None)
    print('ASTRA_TRACE='+json.dumps(sorted(seen)))
