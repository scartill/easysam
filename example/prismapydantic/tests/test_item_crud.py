import sys
import os
from pathlib import Path


EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXAMPLE_ROOT.absolute()))


if 'AWS_PROFILE' not in os.environ:
    os.environ['AWS_PROFILE'] = 'easysam-a'


from common.myobject.db import ItemModel  # noqa: E402
from common.myobject.models import Item, NestedItem  # noqa: E402


def test_item_crud_flow():
    foo_value = 'Foo#1'
    bar_value = 'Bar#1'
    nested_initial = NestedItem(NestedFoo='nested#1')

    created = ItemModel.put(Item(Foo=foo_value, Bar=bar_value, Baz='baz', Nested=nested_initial))
    assert created.Bar == bar_value
    assert created.Nested.NestedFoo == 'nested#1'

    persisted = ItemModel.get(foo=foo_value, bar=bar_value)
    assert persisted.Baz == 'baz'
    assert persisted.Nested.NestedFoo == 'nested#1'

    updated = ItemModel.update(
        ItemModel.UpdateDTO(Baz='updated', Nested=NestedItem(NestedFoo='nested#2')),
        foo=foo_value,
        bar=bar_value,
    )
    assert updated.Baz == 'updated'
    assert updated.Nested.NestedFoo == 'nested#2'

    listed = ItemModel.list(foo=foo_value)
    assert len(listed) == 1
    assert listed[0].Baz == 'updated'
    assert listed[0].Nested.NestedFoo == 'nested#2'

    scanned = ItemModel.scan()
    assert len(scanned) == 1
    assert scanned[0].Foo == foo_value
    assert scanned[0].Nested.NestedFoo == 'nested#2'

    final = ItemModel.save(
        Item(Foo=foo_value, Bar=bar_value, Baz='saved', Nested=NestedItem(NestedFoo='nested#3')),
        original=updated,
    )
    assert final.Baz == 'saved'
    assert final.Nested.NestedFoo == 'nested#3'

    ItemModel.delete(foo=foo_value, bar=bar_value)
    assert ItemModel.scan() == []
