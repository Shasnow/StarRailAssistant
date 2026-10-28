"""UTF-8 echo fixture only: no SRA startup, operators, game or user state."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from SRACore.util.standard_io import configure_standard_streams

configure_standard_streams()
for line in sys.stdin:
    value = line.rstrip('\r\n')
    if value == 'exit':
        break
    print(value, flush=True)
    print(value, file=sys.stderr, flush=True)
