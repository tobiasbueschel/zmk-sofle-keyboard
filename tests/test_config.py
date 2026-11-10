"""Offline checks for Sofle configuration mistakes; run with unittest discovery.

Metadata fixtures come from zmkfirmware/zmk at 4dd95d7840eb3d5a3f59bb29fbf1ab054715ef85:
schema/hardware-metadata.schema.json and app/boards/nicekeyboards/nice_nano/nice_nano.zmk.yml.
The wiring expectations describe the original Eyelash Sofle PCB configuration at
tobiasbueschel/zmk-sofle-keyboard commit ed4a636, not generic Sofle hardware.
"""

import json
from pathlib import Path
import re
import unittest

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
SHIELD = ROOT / "boards/shields/eyelash_sofle"
FIXTURES = Path(__file__).parent / "fixtures"


def load_yaml(path):
    return yaml.safe_load(path.read_text())


def source(path):
    text = path.read_text()
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def block(text, name):
    match = re.search(r"\b" + re.escape(name) + r"\s*\{", text)
    if match is None:
        raise AssertionError(f"Missing devicetree node {name}")
    start, depth = match.end(), 1
    for pos in range(start, len(text)):
        depth += (text[pos] == "{") - (text[pos] == "}")
        if depth == 0:
            return text[start:pos]
    raise AssertionError(f"Unclosed devicetree node {name}")


def gpio_pins(text, property_name):
    match = re.search(r"\b" + re.escape(property_name) + r"\s*=\s*(.*?);", text, re.S)
    if match is None:
        raise AssertionError(f"Missing GPIO property {property_name}")
    cells = re.findall(r"<([^>]+)>", match.group(1))
    result = []
    for cell in cells:
        pin = re.fullmatch(r"\s*&(gpio[01])\s+(\d+)\s+(.+?)\s*", cell)
        if pin is None:
            raise AssertionError(f"Unrecognized GPIO assignment: {cell}")
        flags = set(re.findall(r"GPIO_[A-Z_]+", pin.group(3)))
        result.append((pin.group(1), int(pin.group(2)), flags))
    if not result:
        raise AssertionError(f"Empty GPIO property {property_name}")
    return result


class MetadataTests(unittest.TestCase):
    def test_shield_metadata_matches_official_schema(self):
        schema = json.loads((FIXTURES / "hardware-metadata.schema.json").read_text())
        for path in SHIELD.glob("*.zmk.yml"):
            with self.subTest(file=path.name):
                jsonschema.validate(load_yaml(path), schema)

    def test_controller_exposes_required_interface(self):
        controller = load_yaml(FIXTURES / "nice_nano.zmk.yml")
        shield = load_yaml(SHIELD / "eyelash_sofle.zmk.yml")
        self.assertEqual(shield["type"], "shield")
        self.assertTrue(set(shield["requires"]) <= set(controller["exposes"]))
        self.assertEqual(set(shield["siblings"]), {"eyelash_sofle_left", "eyelash_sofle_right"})


class BuildTests(unittest.TestCase):
    def test_all_firmware_variants_have_correct_side_and_unique_output(self):
        entries = load_yaml(ROOT / "build.yaml")["include"]
        roles, outputs = set(), []
        for entry in entries:
            with self.subTest(output=entry.get("artifact-name")):
                self.assertEqual(entry["board"], "nice_nano@2.0.0//zmk")
                shields = entry["shield"].split()
                sides = [side for side in ("left", "right") if f"eyelash_sofle_{side}" in shields]
                self.assertEqual(len(sides), 1, "Every image must target exactly one half")
                side = sides[0]
                studio = "-DCONFIG_ZMK_STUDIO=y" in entry.get("cmake-args", "")
                reset = "settings_reset" in shields
                if studio:
                    self.assertEqual(side, "left", "Studio belongs on the central half")
                    self.assertEqual(entry.get("snippet"), "studio-rpc-usb-uart")
                    self.assertFalse(reset)
                else:
                    self.assertNotIn("snippet", entry)
                if reset:
                    self.assertNotIn("nice_view", shields)
                else:
                    self.assertIn("nice_view", shields)
                self.assertNotIn("nice_view_custom", shields)
                output = entry["artifact-name"]
                self.assertIn(side, output, "Filename must identify the correct half")
                self.assertRegex(output, r"^[A-Za-z0-9_-]+$")
                outputs.append(output)
                roles.add((side, "reset" if reset else "studio" if studio else "regular"))
        self.assertEqual(len(entries), 5)
        self.assertEqual(len(outputs), len(set(outputs)), "Artifacts must not overwrite one another")
        self.assertEqual(roles, {
            ("left", "regular"), ("right", "regular"), ("left", "studio"),
            ("left", "reset"), ("right", "reset"),
        })

    def test_manifest_and_workflow_use_matching_official_zmk_refs(self):
        manifest = load_yaml(ROOT / "config/west.yml")["manifest"]
        projects = {p["name"]: p for p in manifest["projects"]}
        project = projects["zmk"]
        remotes = {r["name"]: r["url-base"] for r in manifest["remotes"]}
        self.assertEqual(remotes[project["remote"]], "https://github.com/zmkfirmware")
        workflow = load_yaml(ROOT / ".github/workflows/build.yml")
        self.assertEqual(
            workflow["jobs"]["build"]["uses"],
            "zmkfirmware/zmk/.github/workflows/build-user-config.yml@" + project["revision"],
        )
        self.assertNotIn("mario-peripheral-animation", projects)


class WiringTests(unittest.TestCase):
    def test_split_keyboard_keeps_its_on_chip_bluetooth_controller(self):
        kconfig = (SHIELD / "Kconfig.defconfig").read_text()
        # Firmware can compile with an external HCI backend even when the
        # nRF52840 radio is accidentally disabled, so compilation alone is insufficient.
        self.assertRegex(kconfig, r"config\s+BT_CTLR\s+default\s+BT\b")
        self.assertRegex(kconfig, r"config\s+ZMK_SPLIT\s+default\s+y\b")
        central = kconfig.split("if SHIELD_EYELASH_SOFLE_LEFT\n", 1)[1].split("endif", 1)[0]
        self.assertRegex(central, r"config\s+ZMK_SPLIT_ROLE_CENTRAL\s+default\s+y\b")

    def test_matrix_wiring_matches_the_original_pcb(self):
        shared = source(SHIELD / "eyelash_sofle.dtsi")
        rows = gpio_pins(shared, "row-gpios")
        self.assertEqual([(p, n) for p, n, _ in rows], [
            ("gpio0", 19), ("gpio0", 8), ("gpio0", 12), ("gpio0", 11), ("gpio1", 9),
        ])
        self.assertTrue(all(f == {"GPIO_ACTIVE_HIGH", "GPIO_PULL_DOWN"} for _, _, f in rows))
        expected = {
            "left": [3, 28, 30, 21, 23, 22],
            "right": [22, 29, 3, 28, 30, 21, 23],
        }
        for side, pins in expected.items():
            with self.subTest(side=side):
                overlay = source(SHIELD / f"eyelash_sofle_{side}.overlay")
                self.assertNotIn("row-gpios", overlay, "Rows must use the shared PCB definition")
                columns = gpio_pins(overlay, "col-gpios")
                self.assertEqual([(p, n) for p, n, _ in columns], [("gpio0", n) for n in pins])
                self.assertTrue(all(f == {"GPIO_ACTIVE_HIGH"} for _, _, f in columns))
                allocated = [(p, n) for p, n, _ in rows + columns]
                self.assertEqual(len(allocated), len(set(allocated)), "Rows and columns must not share pins")
        self.assertRegex(shared, r'diode-direction\s*=\s*"col2row"\s*;')
        self.assertRegex(source(SHIELD / "eyelash_sofle_right.overlay"), r"col-offset\s*=\s*<7>")

    def test_encoder_and_display_wiring_matches_the_original_pcb(self):
        shared = source(SHIELD / "eyelash_sofle.dtsi")
        encoder = block(shared, "encoder_left")
        self.assertEqual(gpio_pins(encoder, "a-gpios"), [
            ("gpio1", 10, {"GPIO_ACTIVE_HIGH", "GPIO_PULL_UP"}),
        ])
        self.assertEqual(gpio_pins(encoder, "b-gpios"), [
            ("gpio1", 14, {"GPIO_ACTIVE_HIGH", "GPIO_PULL_UP"}),
        ])
        self.assertEqual(gpio_pins(shared, "cs-gpios"), [("gpio0", 6, {"GPIO_ACTIVE_HIGH"})])
        expected = {
            "spi0_default": {("SPIM_SCK", 0, 20), ("SPIM_MOSI", 0, 17), ("SPIM_MISO", 0, 25)},
            "spi0_sleep": {("SPIM_SCK", 0, 20), ("SPIM_MOSI", 0, 17), ("SPIM_MISO", 0, 25)},
            "spi3_default": {("SPIM_MOSI", 1, 12)},
            "spi3_sleep": {("SPIM_MOSI", 1, 12)},
            "pwm0_default": {("PWM_OUT0", 1, 13)},
            "pwm0_sleep": {("PWM_OUT0", 1, 13)},
        }
        for name, pins in expected.items():
            with self.subTest(node=name):
                values = re.findall(r"NRF_PSEL\(\s*(\w+),\s*(\d+),\s*(\d+)\s*\)", block(shared, name))
                self.assertEqual({(f, int(p), int(n)) for f, p, n in values}, pins)

    def test_shield_reuses_controller_power_and_flash_definitions(self):
        shared = source(SHIELD / "eyelash_sofle.dtsi")
        self.assertNotIn('compatible = "zmk,ext-power-generic"', shared, "Avoid duplicate power switches")
        self.assertNotIn('compatible = "fixed-partitions"', shared, "Use the controller flash layout")
        self.assertRegex(block(shared, "reg0"), r'status\s*=\s*"okay"')
        self.assertRegex(block(shared, "reg1"), r"regulator-initial-mode\s*=\s*<NRF5X_REG_MODE_DCDC>")
        self.assertRegex(shared, r"/delete-node/\s+leds\s*;", "Keep the controller-only LED pin unused")


class KeymapTests(unittest.TestCase):
    def test_every_layer_covers_the_complete_physical_layout(self):
        layout = source(SHIELD / "eyelash_sofle-layouts.dtsi")
        transform = block(source(SHIELD / "eyelash_sofle.dtsi"), "keymap_transform_0")
        positions = [(int(r), int(c)) for r, c in re.findall(r"RC\((\d+),\s*(\d+)\)", transform)]
        self.assertEqual(len(positions), 64)
        self.assertEqual(len(set(positions)), 64, "Matrix positions must be unique")
        self.assertTrue(all(0 <= r < 5 and 0 <= c < 14 for r, c in positions))
        self.assertEqual(layout.count("&key_physical_attrs"), len(positions))
        keymap = block(source(ROOT / "config/eyelash_sofle.keymap"), "keymap")
        layers = re.findall(r"(?<![\w-])bindings\s*=\s*<(.*?)>\s*;", keymap, re.S)
        self.assertGreater(len(layers), 0)
        for index, bindings in enumerate(layers):
            with self.subTest(layer=index):
                self.assertEqual(len(re.findall(r"&\w+", bindings)), len(positions))

    def test_layer_switches_reference_existing_layers(self):
        text = source(ROOT / "config/eyelash_sofle.keymap")
        keymap = block(text, "keymap")
        layer_count = len(re.findall(r"(?<![\w-])bindings\s*=\s*<", keymap))
        defines = dict(re.findall(r"^\s*#define\s+(\w+)\s+(0x[0-9a-fA-F]+|\d+)\b", text, re.M))
        for behavior, value in re.findall(r"&(mo|lt|to|tog|sl)\s+(-?\w+)", keymap):
            value = defines.get(value, value)
            with self.subTest(behavior=behavior, layer=value):
                self.assertRegex(value, r"^(0x[0-9a-fA-F]+|\d+)$", "Layer constants must resolve to numbers")
                self.assertLess(int(value, 0), layer_count)


if __name__ == "__main__":
    unittest.main()
