import sys
import os
from pathlib import Path


EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXAMPLE_ROOT.absolute()))


if 'AWS_PROFILE' not in os.environ:
    os.environ['AWS_PROFILE'] = 'easysam-a'


from common.myobject.db import ItemModel  # noqa: E402
from common.myobject.models import Item  # noqa: E402


def test_item_crud_flow():
    foo_value = 'Foo#1'
    bar_value = 'Bar#1'

    created = ItemModel.put(Item(Foo=foo_value, Bar=bar_value, Baz='baz'))
    assert created.Bar == bar_value

    persisted = ItemModel.get(foo=foo_value, bar=bar_value)
    assert persisted.Baz == 'baz'

    updated = ItemModel.update(
        ItemModel.UpdateDTO(Baz='updated'),
        foo=foo_value,
        bar=bar_value,
    )
    assert updated.Baz == 'updated'

    listed = ItemModel.list(foo=foo_value)
    assert len(listed) == 1
    assert listed[0].Baz == 'updated'

    scanned = ItemModel.scan()
    assert len(scanned) == 1
    assert scanned[0].Foo == foo_value

    final = ItemModel.save(
        Item(Foo=foo_value, Bar=bar_value, Baz='saved'),
        original=updated,
    )
    assert final.Baz == 'saved'

    ItemModel.delete(foo=foo_value, bar=bar_value)
    assert ItemModel.scan() == []
