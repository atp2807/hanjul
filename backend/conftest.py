"""pytest 루트 설정 — backend 디렉토리를 sys.path 에 올려 `src`/`main`/`tests` import 보장."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
