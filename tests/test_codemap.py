"""codemap's tools, called as plain functions."""

from devtools.codemap_server import list_public_names, trace_export


def test_a_renamed_export_leads_to_its_definition():
    found = trace_export("legacy.warehouse", "load_record")
    assert found["defined_in"] == "legacy/warehouse/records.py"
    assert found["name"] == "read_record"
    assert found["chain"] == ["legacy.warehouse:load_record",
                              "legacy.warehouse.records:read_record"]


def test_the_package_lists_where_each_name_comes_from():
    rows = {row["name"]: row for row in list_public_names("legacy.warehouse")}
    assert rows["shipping_quote"]["from"] == "legacy.warehouse.shipping"
