import socket
import unittest

from e06.core import H, W, SpecError, inspect_clipping, render

BAR = {"kind": "bar", "title": "Weekly deploys", "x_label": "week",
       "y_label": "deploys", "y_unit": "", "aggregation": "sum",
       "series": [{"label": "W1", "value": 4}, {"label": "W2", "value": 9},
                  {"label": "W3", "value": 2}]}

LINE = {"kind": "line", "title": "p99 latency", "x_label": "day",
        "y_label": "latency", "y_unit": "ms",
        "series": [{"label": "Mon", "value": 120}, {"label": "Tue", "value": 180},
                   {"label": "Wed", "value": 150}]}


class Validation(unittest.TestCase):
    def test_missing_labels_units_refused(self):
        for drop in ("title", "x_label", "y_label", "y_unit", "series"):
            bad = {k: v for k, v in BAR.items() if k != drop}
            with self.assertRaises(SpecError, msg=drop):
                render(bad)

    def test_bad_series_and_kind_refused(self):
        with self.assertRaises(SpecError):
            render(dict(BAR, series=[]))
        with self.assertRaises(SpecError):
            render(dict(BAR, series=[{"label": "x", "value": "nine"}]))
        with self.assertRaises(SpecError):
            render(dict(BAR, kind="pie3d"))
        with self.assertRaises(SpecError):
            render(dict(BAR, aggregation="vibes"))


class Determinism(unittest.TestCase):
    def test_byte_stable_output(self):
        a, b = render(BAR), render(BAR)
        self.assertEqual(a["svg"], b["svg"])
        self.assertEqual(a["output_digest"], b["output_digest"])

    def test_different_data_different_digest(self):
        other = dict(BAR, series=BAR["series"][:2])
        self.assertNotEqual(render(BAR)["output_digest"],
                            render(other)["output_digest"])

    def test_pure_no_io(self):
        import builtins
        opened = []
        real_open, real_socket = builtins.open, socket.socket
        builtins.open = lambda *a, **k: (opened.append(a), real_open(*a, **k))[1]
        socket.socket = lambda *a, **k: (_ for _ in ()).throw(AssertionError)
        try:
            r = render(LINE)
            inspect_clipping(r)
        finally:
            builtins.open, socket.socket = real_open, real_socket
        self.assertEqual(opened, [])
        self.assertTrue(r["ephemeral"])


class Semantics(unittest.TestCase):
    def test_bar_axis_zero_based(self):
        r = render(BAR)
        self.assertEqual(r["semantics"]["scale"]["domain"][0], 0.0)
        self.assertTrue(r["semantics"]["scale"]["zero_based"])

    def test_line_axis_fits_data(self):
        r = render(LINE)
        self.assertEqual(r["semantics"]["scale"]["domain"], [120, 180])

    def test_scale_mapping_recomputable(self):
        r = render(BAR)
        lo, hi = r["semantics"]["scale"]["domain"]
        plot_h = H - 40 - 50
        # tallest bar (value 9) top y from the published mapping
        expect_y = round(40 + plot_h * (1 - (9 - lo) / (hi - lo)), 2)
        tallest = min(r["elements"], key=lambda e: e["y"])
        self.assertEqual(tallest["y"], expect_y)

    def test_labels_units_values_in_svg(self):
        r = render(LINE)
        for needle in ("p99 latency", "latency (ms)", "Mon", "day"):
            self.assertIn(needle, r["svg"])
        self.assertEqual(r["semantics"]["unit"], "ms")
        self.assertEqual(r["semantics"]["values"], [120, 180, 150])

    def test_negative_bars_hang_below_zero(self):
        r = render(dict(BAR, series=[{"label": "up", "value": 5},
                                     {"label": "down", "value": -3}]))
        self.assertEqual(r["semantics"]["scale"]["domain"][0], -3)
        up = r["elements"][0]
        down = r["elements"][1]
        self.assertLess(up["y"], down["y"])       # up-bar top above down-bar top

    def test_escaping(self):
        r = render(dict(LINE, title="a<b & c"))
        self.assertIn("a&lt;b &amp; c", r["svg"])
        self.assertNotIn("a<b", r["svg"].split("<title>")[1].split("</title>")[0][1:])


class Clipping(unittest.TestCase):
    def test_clean_renders_pass(self):
        for spec in (BAR, LINE):
            self.assertEqual(inspect_clipping(render(spec))["verdict"], "PASS")

    def test_tampered_element_fails(self):
        r = render(BAR)
        r["elements"][0]["y"] = -50
        rep = inspect_clipping(r)
        self.assertEqual(rep["verdict"], "FAIL")
        self.assertTrue(rep["clipped_elements"])

    def test_many_points_stay_inside(self):
        big = dict(LINE, series=[{"label": f"d{i}", "value": (i * 37) % 500}
                                 for i in range(40)])
        rep = inspect_clipping(render(big))
        self.assertEqual(rep["verdict"], "PASS", rep)


if __name__ == "__main__":
    unittest.main()


class StrictInputHardening(unittest.TestCase):
    """Added in 0.1.1-partial: findings A023-F1..F6."""

    def test_nan_inf_refused(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(SpecError, msg=repr(bad)):
                render(dict(BAR, series=[{"label": "a", "value": bad},
                                         {"label": "b", "value": 1}]))

    def test_bool_value_refused(self):
        with self.assertRaises(SpecError):
            render(dict(BAR, series=[{"label": "a", "value": True}]))

    def test_finite_numeric_values_still_accepted(self):
        r = render(dict(BAR, series=[{"label": "a", "value": 4.5},
                                     {"label": "b", "value": 0}]))
        self.assertEqual(r["semantics"]["values"], [4.5, 0])

    def test_non_dict_spec_is_specerror(self):
        for bad in (None, 42, "spec", [1, 2]):
            with self.assertRaises(SpecError, msg=repr(bad)):
                render(bad)

    def test_non_dict_series_item_is_specerror(self):
        for bad in (5, None, "label", ["label", "value"]):
            with self.assertRaises(SpecError, msg=repr(bad)):
                render(dict(BAR, series=[bad]))

    def test_inspector_flags_nonfinite_tamper(self):
        r = render(BAR)
        r["elements"][0]["y"] = float("nan")
        rep = inspect_clipping(r)
        self.assertEqual(rep["verdict"], "FAIL")
        self.assertTrue(rep["clipped_elements"])

    def test_version_constant(self):
        from e06.core import VERSION, __version__
        self.assertEqual(VERSION, "0.1.2a1")
        self.assertEqual(__version__, VERSION)
