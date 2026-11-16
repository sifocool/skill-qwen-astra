"""Internal POSIX resource limiter; no dependency on the engine's import path."""
import os
import resource
import sys

resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))
resource.setrlimit(resource.RLIMIT_CPU,(30,30))
os.execvpe(sys.argv[1],sys.argv[1:],os.environ)
