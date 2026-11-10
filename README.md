# 👾 Sofle Keyboard 👾

Here is my configuration guide for the Sofle v2 RGB Bluetooth keyboard kit (created by [@a741725193](https://github.com/a741725193/zmk-sofle)) as found on AliExpress or Taobao.

The Sofle is a 6x4+5 keys column-staggered split keyboard with encoder support, which has been [open sourced in 2020](https://josef-adamcik.cz/electronics/let-me-introduce-you-sofle-keyboard-split-keyboard-based-on-lily58.html) by [Josef Adamcik](https://josef-adamcik.cz/). It is based on [Lily58](https://github.com/kata0510/Lily58), [Corne](https://github.com/foostan/crkbd) and [Helix](https://github.com/MakotoKurauchi/helix) keyboards. You can find more details in the GitHub repo for the project and if you like to build it from scratch, here is the [build guide](https://josefadamcik.github.io/SofleKeyboard/build_guide.html).

This Sofle kit is a great and affordable starting point if you want to get into the world of split keyboards but don't yet want to do any soldering.

![Sofle Keyboard](./keyboard.jpg)

## What you will need

**1. Case & PCB**

- [Sofle on AliExpress](https://s.click.aliexpress.com/e/_ooUVBk5)
  - NOTE: there are multiple sellers offering the same, but the keyboard builds are ultimately from the same person
- Version 2 of the Sofle only supports MX switches that can be hot swapped
- You will need 58 switches & keycaps
- Bluetooth chip used is the https://www.nordicsemi.com/Products/nRF52840

**2. Switches**

- [Y3 on AliExpress](https://s.click.aliexpress.com/e/_okfiSdT)
- Any MX switches will work, I'm using Y3 linear switches https://www.aliexpress.com/item/1005007821220888.html with an actuation force of 48g

**3. Keycaps**

- I use a combination of keycap sets:
  - [SA profile black/yellow PBT keycaps on AliExpress](https://s.click.aliexpress.com/e/_onvZN6v)
  - [XDA profile white/yellow PBT keycaps on AliExpress](https://s.click.aliexpress.com/e/_oovVSRn)

## How to get started

Once you have everything, assembly is easy and fully plug & play. After you've inserted the switches and installed the keycaps, you can turn on both sides of the keyboard using the middle switch, and then go to Bluetooth in your settings and pair the device. You can find the default keymap configuration [here](https://github.com/a741725193/zmk-sofle).

### Firmware

Contrary to the original Sofle, this version uses [ZMK](https://zmk.dev) instead of [QMK](https://qmk.fm), which as far as I know is mainly due to better support for wireless using Bluetooth. _"ZMK Firmware is an open source (MIT) keyboard firmware built on the [Zephyr™ Project](https://zephyrproject.org/) Real Time Operating System (RTOS). ZMK's goal is to provide a modern and powerful firmware that is designed for power-efficiency, flexibility, and broad hardware support. ZMK is capable of being used for both wired and wireless input devices."_

### Folder structure

```shell
.
├── boards/shields/eyelash_sofle    # Sofle hardware on the standard nice!nano v2 controller definition
│ ├── Kconfig.shield               # Left/right shield selection
│ ├── Kconfig.defconfig            # Split role and shared defaults
│ ├── eyelash_sofle_left.conf      # Left controller settings
│ ├── eyelash_sofle_right.conf     # Right controller settings (USB disabled)
│ ├── eyelash_sofle_left.overlay   # Left matrix wiring and encoder
│ ├── eyelash_sofle_right.overlay  # Right matrix wiring and offset
│ ├── eyelash_sofle-layouts.dtsi   # Physical layout (unchanged)
│ ├── eyelash_sofle.dtsi           # Shared wiring, lighting and display connections
│ └── eyelash_sofle.zmk.yml        # Shield metadata
│
├── config                          # Configuration and keymap files
│ ├── eyelash_sofle.conf            # Main ZMK configuration for the Sofle board
│ ├── eyelash_sofle.json            # Keymap and layout in JSON format (for visualization/tools)
│ ├── eyelash_sofle.keymap          # Keymap file for firmware (ZMK format)
│ └── west.yml                      # West manifest for managing Zephyr/ZMK modules and dependencies
│
├── keymap-drawer                   # Keymap visualizations and YAML definitions for documentation and tools
│ ├── eyelash_sofle.svg             # SVG visualization of the Sofle keymap
│ └── eyelash_sofle.yaml            # YAML definition of the Sofle keymap (for keymap-drawer)
│
├── zephyr
│ └── module.yml                    # Zephyr module configuration for ZMK integration
```

The firmware and build workflow both follow official ZMK `main`. The controller target is `nice_nano@2.0.0//zmk`, explicitly selecting the existing nice!nano v2 hardware using the current ZMK board format. Both halves use the standard `nice_view` display; the right-hand animation module is no longer required. Your personal keymap remains in `config/eyelash_sofle.keymap`.

### Customizing keymap

If you want to customize the keymap, you have three options:

**1. [ZMK Studio](https://zmk.studio)**

- Allows you to do runtime keymap configuration for ZMK devices i.e., you can make changes without the need to flash new firmware onto your keyboard
- First MVP released to the general public in November 2024, does not yet support all ZMK features
- Here is a list of features currently supported: https://zmk.dev/docs/features/studio#capabilities
- NOTE: ZMK Studio does not yet support export `.keymap` files, hence, many people suggest to first try out your keymap layout with ZMK Studio and once you like it port over the changes to a `.keymap` file so that you can compile a custom ZMK firmware, version control the configuration and flash your keyboard with this firmware.

**2. [nickcoutsos/keymap-editor](https://github.com/nickcoutsos/keymap-editor)**

- A web based graphical editor of ZMK keymaps, which leverages GitHub Actions to compile the firmware.
- You can try it here: https://nickcoutsos.github.io/keymap-editor/
- Created in August 2020 and since July 2023 the source code is no longer updated as commercial entities have branded and used this project to sell their ZMK based keyboards without contributing back to the original `keymap-editor` project. Hence, the original author [@nickcoutsos](https://github.com/nickcoutsos) decided to pull the plug and no longer make updates to the source code available publicly.
- NOTE: If you want to use the updated Keymap-Editor app you will need to authorize it with your GitHub account so that it can push updates and trigger the GitHub Action.
- If you do not want this you could self-host an older version of `keymap-editor` from when the source code was shared or do a firmware update without the graphical editor as described in option 3

**3. [Manually flashing ZMK firmware](https://zmk.dev/docs/user-setup)**

**Option 1: Building on GitHub Actions**

- This is the recommended process of setting up and configuring ZMK as described in the documentation
- NOTE: If you've forked this repository, you can manually edit the [eyelash_sofle.keymap](./config/eyelash_sofle.keymap) file and push any changes, which will trigger GitHub actions to build the new firmware file

Once the GitHub Action pipeline has completed, you can download all firmware files.

**Option 2: Building locally**

You can also build locally with the official ZMK Docker image. Start Docker and run the following from this keyboard repository's root directory. The named volume keeps downloaded dependencies between builds, and firmware files are saved in your local `build/` directory.

```shell
mkdir -p build
docker run --rm -it \
  -v "$PWD:/repo:ro" \
  -v "$PWD/build:/output" \
  -v zmk-sofle-workspace:/work \
  -w /work \
  zmkfirmware/zmk-build-arm:stable bash
```

Inside the container, initialize or update the workspace using this repository's manifest:

```shell
mkdir -p config
cp /repo/config/west.yml config/west.yml
if [ ! -d .west ]; then west init -l config; fi
west update
west zephyr-export
```

Build the regular left/right firmware, the alternative Studio left firmware, and both recovery images:

```shell
west build -s zmk/app -d build/left -p -b nice_nano@2.0.0//zmk -- -DSHIELD="eyelash_sofle_left nice_view" -DZMK_EXTRA_MODULES=/repo -DZMK_CONFIG=/repo/config
west build -s zmk/app -d build/right -p -b nice_nano@2.0.0//zmk -- -DSHIELD="eyelash_sofle_right nice_view" -DZMK_EXTRA_MODULES=/repo -DZMK_CONFIG=/repo/config
west build -s zmk/app -d build/studio_left -p -b nice_nano@2.0.0//zmk -S studio-rpc-usb-uart -- -DSHIELD="eyelash_sofle_left nice_view" -DZMK_EXTRA_MODULES=/repo -DZMK_CONFIG=/repo/config -DCONFIG_ZMK_STUDIO=y -DCONFIG_ZMK_STUDIO_LOCKING=n
west build -s zmk/app -d build/settings_reset_left -p -b nice_nano@2.0.0//zmk -- -DSHIELD="eyelash_sofle_left settings_reset" -DZMK_EXTRA_MODULES=/repo -DZMK_CONFIG=/repo/config
west build -s zmk/app -d build/settings_reset_right -p -b nice_nano@2.0.0//zmk -- -DSHIELD="eyelash_sofle_right settings_reset" -DZMK_EXTRA_MODULES=/repo -DZMK_CONFIG=/repo/config

cp build/left/zephyr/zmk.uf2 /output/nice_view-eyelash_sofle_left-zmk.uf2
cp build/right/zephyr/zmk.uf2 /output/nice_view-eyelash_sofle_right-zmk.uf2
cp build/studio_left/zephyr/zmk.uf2 /output/eyelash_sofle_studio_left.uf2
cp build/settings_reset_left/zephyr/zmk.uf2 /output/settings_reset-eyelash_sofle_left-zmk.uf2
cp build/settings_reset_right/zephyr/zmk.uf2 /output/settings_reset-eyelash_sofle_right-zmk.uf2
exit
```

**Loading the firmware to your keyboard**

_"Then put your board into bootloader mode by double clicking the reset button (either on the MCU board itself, or the one that is part of your keyboard). The controller should appear in your OS as a new USB storage device."_

_"Once this happens, copy the correct UF2 file (e.g. left or right if working on a split), and paste it onto the root of that USB mass storage device. Once the flash is complete, the controller should unmount the USB storage, automatically restart and load your newly flashed firmware. It is recommended that you test your keyboard works over USB first to rule out hardware issues, before trying to connect to it wirelessly."_ Complete instructions can be found here: https://zmk.dev/docs/user-setup#installing-the-firmware

Choose **one** left-half firmware:

- Regular: `nice_view-eyelash_sofle_left-zmk.uf2`
- ZMK Studio: `eyelash_sofle_studio_left.uf2` (a complete firmware image that also contains the keymap)

Flash `nice_view-eyelash_sofle_right-zmk.uf2` onto the right half in either case. This replaces the previous `nice_view_custom-eyelash_sofle_right-zmk.uf2` image and shows the standard nice!view status screen.

For a normal update, flash both halves and test USB input, Bluetooth input, the encoder, mouse controls and displays. Settings reset is a recovery step, not a required part of updating:

1. If needed, flash `settings_reset-eyelash_sofle_left-zmk.uf2` onto the left half and `settings_reset-eyelash_sofle_right-zmk.uf2` onto the right half.
2. Flash your chosen normal/Studio left firmware and the normal right firmware afterwards.
3. Remove the old pairing from your computer and pair again. Reset both halves together so their split pairing can be recreated.

If you have saved a keymap in ZMK Studio, it takes precedence over the compiled keymap until you use **Restore Stock Settings** in Studio.

For more context, these Reddit threads are helpful (they apply to the Corne but the Sofle is from the same vendor):

- https://www.reddit.com/r/ErgoMechKeyboards/comments/1ju67yx/aliexpress_eyelash_corne_basic_beginner_guide/
- https://www.reddit.com/r/ErgoMechKeyboards/comments/1hgs176/what_to_expect_from_the_cheapest_aliexpress_corne/

### Configuration tests

Run the configuration checks before building:

```shell
python3 -m venv .venv
.venv/bin/python -m pip install -r tests/requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

The checks validate hardware metadata against an official ZMK schema snapshot, controller compatibility, all five build variants and their output names, PCB pin assignments, key counts and layer references. You can change key bindings without updating the tests as long as the layout remains valid.

GitHub runs these checks for pull requests and updates to `main`, then compiles every firmware variant using ZMK `main`. Physical tests are still needed for Bluetooth, displays, encoder/mouse operation and sleep/wake.

### Keeping private data out of Git

The public typing macros are demonstration placeholders. Keep personal email addresses, password-typing sequences and other private text outside this repository's tracked files.

Enable the local safeguards after cloning:

```shell
git config --local core.hooksPath .githooks
```

The hooks inspect staged content and outgoing commits before they leave your computer. They reject changed text macros, personal email addresses, home-directory paths, credential-like tokens, private files, compiled firmware and photo metadata. New commits must use a GitHub username and a private GitHub `noreply` address. Detected values are hidden from the check output. CI repeats the public-content checks as a second layer.

### Current keymap configuration

<img src="keymap-drawer/eyelash_sofle.svg" >

## Changelog

- 2025/3/30
  1. Increase sleep entry time by 1 hour, increase debounce time, optimize post-sleep power consumption.
- 2024/12/21
  1. Added support for zmk-studio (just refresh the left hand to use).
- 2024/10/24
  1. Modified power supply mode to reduce power consumption.
  2. Fixed the automatic shut-off feature for RGB power supply.

> If your keyboard was updated before October 24, please update to the latest firmware.

For 3D printed model files or hardware support, see the [vendor's repository](https://github.com/a741725193/zmk-sofle).
