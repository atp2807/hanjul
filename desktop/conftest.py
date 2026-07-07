"""desktop/ 은 패키지화(__init__.py) 없이 store.py 를 stdlib 스타일로 둔다 — pytest 가
desktop/tests/ 를 수집할 때 desktop/ 자체는 기본적으로 sys.path 에 없으므로, 여기서
명시적으로 등록해 `import store` 가 되게 한다. (conftest.py 는 rootdir부터 수집 대상
디렉터리까지 pytest 가 자동으로 찾아 import 하므로 실행 위치와 무관하게 항상 적용된다.)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
