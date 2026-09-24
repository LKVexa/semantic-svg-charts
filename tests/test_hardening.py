import copy
from fractions import Fraction
import hashlib
import json
import math
import sys
import unittest
import xml.etree.ElementTree as ET

from e06.core import render, inspect_clipping, SpecError, MARGIN, _digest
from tests.test_e06 import BAR, LINE

NS = "{http://www.w3.org/2000/svg}"


class Hardening(unittest.TestCase):
    def test_text_types(self):
        for field in ("title", "x_label", "y_label", "y_unit"):
            for value in (None, 1, [], {}):
                with self.assertRaises(SpecError):
                    render(dict(BAR, **{field: value}))

    def test_empty_text_and_unitless(self):
        for field in ("title", "x_label", "y_label"):
            for value in ("", "   "):
                with self.assertRaises(SpecError):
                    render(dict(BAR, **{field: value}))
        self.assertEqual(render(BAR)["semantics"]["unit"], "")

    def test_text_length(self):
        for field, length in (("title", 257), ("x_label", 257), ("y_label", 257), ("y_unit", 33)):
            with self.assertRaises(SpecError):
                render(dict(BAR, **{field: "x" * length}))

    def test_xml_and_bidi_controls(self):
        for value in ("x\0", "x\n", "\ud800", "\ufffe", "\u202evalue", "\u2066x"):
            with self.assertRaises(SpecError):
                render(dict(BAR, title=value))

    def test_point_label_types(self):
        for value in (None, 1, "", "x"*129):
            with self.assertRaises(SpecError):
                render(dict(BAR, series=[{"label": value, "value": 1}]))

    def test_unknown_fields(self):
        with self.assertRaises(SpecError):
            render(dict(BAR, y_min=3))
        with self.assertRaises(SpecError):
            render(dict(BAR, series=[{"label": "x", "value": 1, "url": "x"}]))

    def test_aggregation_strict(self):
        for value in (None, False, [], {}):
            with self.assertRaises(SpecError):
                render(dict(BAR, aggregation=value))

    def test_max_points(self):
        point = {"label": "x", "value": 1}
        with self.assertRaises(SpecError):
            render(dict(BAR, series=[point] * 257))
        self.assertEqual(len(render(dict(BAR, series=[point] * 256))["elements"]), 256)

    def test_combined_text_budget(self):
        with self.assertRaises(SpecError):
            render(dict(BAR, series=[{"label": "界" * 128, "value": 1}] * 50))

    def test_integer_limits(self):
        for value in (2**53, -2**53, 10**1000):
            with self.assertRaises(SpecError):
                render(dict(BAR, series=[{"label": "x", "value": value}]))

    def test_numeric_subclasses(self):
        class Numeric(float):
            pass
        with self.assertRaises(SpecError):
            render(dict(BAR, series=[{"label": "x", "value": Numeric(2)}]))

    def test_extreme_floats(self):
        for kind in ("bar", "line"):
            result = render(dict(BAR, kind=kind, series=[{"label": "a", "value": -sys.float_info.max},
                                                        {"label": "b", "value": sys.float_info.max}]))
            self.assertEqual(inspect_clipping(result)["verdict"], "PASS")
            self.assertEqual(result["elements"][1]["y"], 40)
            json.dumps(result, allow_nan=False)

    def test_subnormal_floats(self):
        result = render(dict(LINE, series=[{"label": "a", "value": 5e-324},
                                          {"label": "b", "value": 1e-323}]))
        self.assertEqual([e["y"] for e in result["elements"]], [350, 40])

    def test_constant_extremes(self):
        for value in (0, 4, 1e300, -1e300, sys.float_info.max, -sys.float_info.max, 5e-324, -5e-324):
            result = render(dict(LINE, series=[{"label": "a", "value": value}] * 2))
            lo, hi = result["semantics"]["scale"]["domain"]
            self.assertLess(lo, hi)
            self.assertTrue(lo <= value <= hi)
            self.assertEqual(inspect_clipping(result)["verdict"], "PASS")

    def test_single_line_point_center(self):
        result = render(dict(LINE, series=[{"label": "only", "value": 10}]))
        self.assertEqual(result["elements"][0]["x"], 356)

    def test_bar_all_zero(self):
        result = render(dict(BAR, series=[{"label": "zero", "value": 0}]))
        self.assertEqual(result["semantics"]["scale"]["domain"], [0, 1])
        self.assertEqual(result["elements"][0]["h"], 0)

    def test_all_negative_bar_domain(self):
        result = render(dict(BAR, series=[{"label": "a", "value": -4}, {"label": "b", "value": -2}]))
        self.assertEqual(result["semantics"]["scale"]["domain"], [-4, 0])
        self.assertTrue(all(e["y"] == 40 for e in result["elements"]))

    def test_exact_mapping_from_metadata(self):
        result = render(dict(LINE, series=[{"label": str(i), "value": value}
                                          for i, value in enumerate((-1e308, 1e-308, 1e308))]))
        scale = result["semantics"]["scale"]
        lo, hi = map(Fraction, scale["domain"])
        for value, element in zip(result["semantics"]["values"], result["elements"]):
            expected = round(float(scale["top"] + scale["plot_height"] * (1-(Fraction(value)-lo)/(hi-lo))), 2)
            self.assertEqual(element["y"], expected)

    def test_tick_ratios_recompute(self):
        result = render(LINE)
        lo, hi = map(Fraction, result["semantics"]["scale"]["domain"])
        for tick in result["semantics"]["scale"]["ticks"]:
            value = Fraction(*map(int, tick["exact_ratio"]))
            self.assertEqual(tick["y"], round(float(40 + 310 * (1-(value-lo)/(hi-lo))), 2))

    def test_mark_metadata_matches_svg(self):
        for spec in (BAR, LINE):
            result = render(spec)
            xml = ET.fromstring(result["svg"])
            if spec["kind"] == "bar":
                marks = [e for e in xml.findall(NS+"rect") if e.attrib.get("fill") == "#4477aa"]
                for mark, element in zip(marks, result["elements"]):
                    self.assertEqual([float(mark.attrib[k]) for k in ("x", "y", "width", "height")],
                                     [element[k] for k in ("x", "y", "w", "h")])
            else:
                for mark, element in zip(xml.findall(NS+"circle"), result["elements"]):
                    self.assertEqual([float(mark.attrib[k]) for k in ("cx", "cy", "r")],
                                     [element[k] for k in ("x", "y", "radius")])

    def test_escaping_prevents_nodes(self):
        payload = '</text><script>alert("x")</script>&'
        result = render(dict(BAR, title=payload, series=[{"label": payload, "value": 1}]))
        xml = ET.fromstring(result["svg"])
        self.assertFalse(xml.findall(".//"+NS+"script"))
        self.assertEqual(xml.find(NS+"title").text, payload)

    def test_no_executable_or_external_attributes(self):
        xml = ET.fromstring(render(BAR)["svg"])
        allowed = {"svg", "title", "desc", "rect", "line", "text"}
        for element in xml.iter():
            self.assertIn(element.tag.removeprefix(NS), allowed)
            self.assertFalse(any(k.lower().startswith("on") or k in ("href", "style") for k in element.attrib))

    def test_input_detached(self):
        spec = copy.deepcopy(BAR)
        result = render(spec)
        spec["series"][0]["value"] = 100
        self.assertEqual(result["spec"]["series"][0]["value"], 4)
        self.assertEqual(inspect_clipping(result)["verdict"], "PASS")

    def test_all_semantics_hashed(self):
        result = render(BAR)
        result["semantics"]["unit"] = "different"
        self.assertEqual(inspect_clipping(result)["verdict"], "FAIL")

    def test_svg_tamper_with_rehash_refused(self):
        result = render(BAR)
        result["svg"] = result["svg"].replace('y="24"', 'y="900"')
        result["output_digest"] = "sha256:" + hashlib.sha256(result["svg"].encode()).hexdigest()
        result["render_digest"] = _digest({k: v for k, v in result.items() if k != "render_digest"})
        self.assertEqual(inspect_clipping(result)["verdict"], "FAIL")

    def test_missing_svg_or_elements(self):
        for key in ("svg", "elements", "output_digest", "semantics", "spec"):
            result = render(BAR)
            result.pop(key)
            self.assertEqual(inspect_clipping(result)["verdict"], "FAIL")

    def test_negative_extent_refused(self):
        for field in ("w", "h"):
            result = render(BAR)
            result["elements"][0][field] = -1
            report = inspect_clipping(result)
            self.assertEqual(report["verdict"], "FAIL")
            self.assertTrue(report["clipped_elements"])

    def test_circle_radius_refused(self):
        result = render(LINE)
        result["elements"][0]["radius"] = 1000
        self.assertTrue(inspect_clipping(result)["clipped_elements"])

    def test_vertical_and_horizontal_text_anchors(self):
        for field in ("x", "y"):
            result = render(BAR)
            result["text_anchors"][0][field] = 999
            self.assertTrue(inspect_clipping(result)["out_of_bounds_anchors"])

    def test_bad_inspection_types(self):
        for value in (None, 1, [], "svg", {"svg": []}, {"spec": None}):
            self.assertEqual(inspect_clipping(value)["verdict"], "FAIL")

    def test_cycles_and_oversized_inspection(self):
        result = render(BAR)
        result["cycle"] = result
        self.assertEqual(inspect_clipping(result)["verdict"], "FAIL")
        result = render(BAR)
        result["svg"] = "x" * 524289
        self.assertEqual(inspect_clipping(result)["verdict"], "FAIL")

    def test_boolean_geometry_refused(self):
        result = render(BAR)
        result["elements"][0]["x"] = True
        self.assertEqual(inspect_clipping(result)["verdict"], "FAIL")

    def test_inspection_scope_explicit(self):
        report = inspect_clipping(render(BAR))
        self.assertEqual(report["integrity"], "PASS")
        self.assertEqual(report["text_glyph_bounds"], "NOT_CHECKED")
        self.assertEqual(report["label_overlap"], "NOT_CHECKED")

    def test_thinning_preserves_full_series(self):
        series = [{"label": "category"+str(i), "value": i} for i in range(40)]
        result = render(dict(LINE, series=series))
        self.assertEqual(len(result["elements"]), 40)
        self.assertEqual(result["semantics"]["hidden_category_labels"], 32)
        self.assertEqual(result["semantics"]["labels"], [p["label"] for p in series])
        self.assertIn("category39: 39", result["svg"])
        self.assertEqual(result["semantics"]["visible_label_indices"][0], 0)
        self.assertEqual(result["semantics"]["visible_label_indices"][-1], 39)

    def test_declared_aggregation_not_computed(self):
        result = render(dict(BAR, aggregation="mean"))
        self.assertFalse(result["semantics"]["aggregation_performed"])
        self.assertEqual(result["semantics"]["values"], [4, 9, 2])

    def test_margins_immutable(self):
        with self.assertRaises(TypeError):
            MARGIN["left"] = -100

    def test_digest_includes_all_fields(self):
        result = render(BAR)
        digest = result.pop("render_digest")
        self.assertEqual(digest, _digest(result))

    def test_distinct_accessibility_ids(self):
        a, b = ET.fromstring(render(BAR)["svg"]), ET.fromstring(render(LINE)["svg"])
        self.assertNotEqual(a.attrib["aria-labelledby"], b.attrib["aria-labelledby"])

    def test_narrow_tick_rounding_disclosed(self):
        result = render(dict(LINE, series=[{"label": "a", "value": 1.0},
                                          {"label": "b", "value": math.nextafter(1.0, math.inf)}]))
        self.assertTrue(result["semantics"]["scale"]["repeated_tick_labels"])
        self.assertIn("Rounded ticks; exact scale in metadata", result["svg"])
        self.assertEqual([e["y"] for e in result["elements"]], [350, 40])
