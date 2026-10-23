# Experimental zzh build with updated TI tools

This directory records a successfully compiled **original Electrolama zzh
(CC2652R) coordinator** using SDK 8.33.00.16, CCS 21.0.1.00010, TI ARM Clang
5.1.1.LTS and SysConfig 1.28.2+4845. The SDK's Zigbee component is Z-Stack
8.30.00. These were the latest releases on TI's download pages on 2026-10-23.

TI lists Clang 3.2.2 and SysConfig 1.21.1 as tested SDK dependencies. This newer
combination is experimental: compilation and static image checks passed, but no
stick was flashed and no Zigbee network was tested. Do not use this image for
zzhp, zzhp-lite or CC2652RB. Back up coordinator/network state before testing.
The main [compilation guide](../../COMPILE.md) remains the baseline for other
hardware and router builds.

The firmware still reports revision **20250321**; a toolchain update alone did
not change its application revision. The SDK version in the ZIP filename
separates this artifact from the previous build. `build-manifest.json` records
source and tool versions, and `validation.json` records the committed image's
hashes and validation results. Repackaging changes ZIP timestamps/hashes; compare
the HEX hash when comparing builds. The build retains the same two pointer-sign
warnings in TI's `npi_tl.c:183` as the baseline.

See the [changelog](CHANGELOG.md) and [SDK impact and patch review](SDK_REVIEW.md)
for the upgrade assessment and recommended follow-up.

## Install

`downloads.json` contains official Linux x86-64 installer URLs and published
SHA-256 checksums. Verify every download before running or extracting it. Install
outside the repository, using a directory of your choice:

```sh
simplelink_cc13xx_cc26xx_sdk_8_33_00_16.run --mode unattended --prefix /path/to/sdk-bundle
ccs_setup_21.0.1.00010.run --mode unattended --prefix /path/to/ccs2101 --enable-components PF_WCONN
sysconfig-1.28.2_4845-setup.run --mode unattended --prefix /path/to/sysconfig_1.28.2
ti_cgt_armllvm_5.1.1.LTS_linux-x64_installer.bin --mode unattended --prefix /path/to/compiler
```

Extract the CCS ZIP before running its installer. Wait for each installer to
finish. Set the following variables to the actual installed locations:

```sh
ZZH_SDK=/path/to/sdk-bundle/simplelink_cc13xx_cc26xx_sdk_8_33_00_16
ZZH_CCS=/path/to/ccs2101
ZZH_SYSCONFIG=/path/to/sysconfig_1.28.2
ZZH_COMPILER=/path/to/compiler
ZZH_REPO=/path/to/Z-Stack-firmware
ZZH_RECIPE="$ZZH_REPO/coordinator/Z-Stack_3.x.0/experimental/zzh"
ZZH_TARGET=znp_CC26X2R1_LAUNCHXL_tirtos7_ticlang
ZZH_CLI="$ZZH_CCS/ccs/eclipse/ccs-server-cli.sh"
```

## Configure a fresh SDK once

The existing upstream firmware patch remains unchanged. The only SDK 8.33 source
patch-context adjustment is the UART copyright year (2024 to 2025).
`latest-tool-config.patch` pins the tools before import and appends the same four
zzh SysConfig settings used by the upstream firmware patch after import. This
avoids depending on a GUI save/reformat operation.

```sh
"$ZZH_CLI" -workspace "$ZZH_SDK/workspace" -application initialize \
  -ccs.productDiscoveryPath "$(dirname "$ZZH_SDK");$ZZH_SYSCONFIG" \
  -ccs.toolDiscoveryPath "$ZZH_COMPILER"
cd "$ZZH_SDK"
git apply --check --include='examples/*' "$ZZH_RECIPE/latest-tool-config.patch"
git apply --include='examples/*' "$ZZH_RECIPE/latest-tool-config.patch"
"$ZZH_CLI" -workspace "$ZZH_SDK/workspace" -application createProject \
  -ccs.projectSpec "$ZZH_SDK/examples/rtos/CC26X2R1_LAUNCHXL/zstack/znp/tirtos7/ticlang/$ZZH_TARGET.projectspec"
```

Prepare a temporary copy of `firmware.patch` and apply the compatibility change
there. Keep that temporary directory outside both the repository and SDK:

```sh
ZZH_PATCH_DIR=$(mktemp -d)
cp "$ZZH_REPO/coordinator/Z-Stack_3.x.0/firmware.patch" "$ZZH_PATCH_DIR/firmware.patch"
git -C "$ZZH_PATCH_DIR" apply --check "$ZZH_RECIPE/sdk833-context.patch"
git -C "$ZZH_PATCH_DIR" apply "$ZZH_RECIPE/sdk833-context.patch"
git apply --check --ignore-space-change \
  --exclude="workspace/$ZZH_TARGET/znp.syscfg" \
  --include='source/*' --include='package.py' --include="workspace/$ZZH_TARGET/*" \
  "$ZZH_PATCH_DIR/firmware.patch"
git apply --ignore-space-change --whitespace=nowarn \
  --exclude="workspace/$ZZH_TARGET/znp.syscfg" \
  --include='source/*' --include='package.py' --include="workspace/$ZZH_TARGET/*" \
  "$ZZH_PATCH_DIR/firmware.patch"
git apply --check --include='workspace/*' "$ZZH_RECIPE/latest-tool-config.patch"
git apply --include='workspace/*' "$ZZH_RECIPE/latest-tool-config.patch"
```

## Build and validate

```sh
python3 "$ZZH_RECIPE/build.py" --sdk "$ZZH_SDK" --ccs "$ZZH_CCS" --output /path/to/build-output
```

The script checks the selected tools and patched SDK source hashes, builds the
project, runs the patch-provided packager, and validates the resulting HEX and ZIP.
It requires a successful CCS project summary because CCS can return exit status
zero even when a project fails. Source hashes intentionally reject unreviewed
SDK changes. For subsequent builds, repeat only this build command.

Validation covers record lengths/checksums/EOF, duplicate addresses, flash bounds,
vector-table addresses, NV-storage exclusion, ZIP content/CRC and the ROM
bootloader word `0xc5fe0dc5` at `0x57fd8` (DIO13, active low). It does not prove
radio operation, device interoperability, or persistence across environment
sessions. The hardware-specific validator must not be reused for other adapters.
