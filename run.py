#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tofu_eq.__main__ import main  # noqa: E402

sys.exit(main())
