#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from fieldkit.store_jsonl import Store
from collections import Counter

store = Store('prototype/data_baseline_test')
events = store.load_events()

print(f'Total events: {len(events)}')
print('\nTop 20 event types:')
event_types = Counter(e['name'] for e in events)
for name, count in event_types.most_common(20):
    print(f'  {name}: {count}')

