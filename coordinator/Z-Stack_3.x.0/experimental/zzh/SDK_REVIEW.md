# TI SDK upgrade impact and patch review

Reviewed on 2026-10-23 for the original Electrolama zzh (CC2652R), comparing our
SDK 8.30.01.01 / Clang 4.0.2 / SysConfig 1.21.1 build with the experimental
SDK 8.33.00.16 / Clang 5.1.1 / SysConfig 1.28.2 build. CCS moved from 20.1.0
to 21.0.1. Both builds use the repository's 20250321 coordinator patch.

**Recommendation: keep the established coordinator compatibility patches, reduce
irrelevant patch scope, and add narrowly targeted checks and diagnostics. Do not
increase buffers/retries or remove workarounds simply because the SDK is newer.**
The updated image is suitable for controlled hardware evaluation, not a proven
reliability upgrade for an existing network.

## What changed

| Area | Evidence | Impact for the zzh |
| --- | --- | --- |
| SDK 8.33 | TI says this release updates Wi-SUN; other components come from 8.31. | Wi-SUN TCP/MQTT/CSMP features do not add features to this Zigbee coordinator. Compare against our actual 8.30 baseline, not just 8.32. |
| Zigbee component | Both SDKs report Z-Stack 8.30.00. Their Zigbee release-note text differs only in copyright year. Four Cortex-M4F Z-Stack archives have identical compared allocatable ELF and relocation sections and member lists. | No demonstrated new APS/NWK/ZCL implementation that replaces our compatibility workarounds. Archive-file hashes alone misleadingly suggest more changes. This section comparison is not a complete semantic-equivalence proof. |
| Shared MAC | The linked `maclib_nosecure_cc26x2_2_4g_tirtos7.a` has changed executable sections in seven members: `mac_rx`, `mac_hl_patch`, `mac_autopend`, `mac_low_level`, `mac`, `mac_tx`, `mac_radio`. | This is a real radio-stack change relevant to the CC2652R, even though the Zigbee component version stayed the same. |
| Temperature and reset handling | New Z-Stack SysConfig dependency on `/ti/drivers/Temperature`; new MAC temperature-monitoring code and source-matching clear/check functions. The linker map includes these functions. | Plausible gains around temperature changes and reset/source-matching correctness. Hardware tests must establish whether these changes fix our actual symptoms. |
| MAC integration source | `zmac.c` moves some API helpers out and handles `MAC_BC_TIM_TASK_EVT`; the shared MAC API changes too. | Retain the matching vendor source and libraries together. Do not mix old MAC libraries with new wrapper source. The broadcast-timer event does not establish a new Zigbee broadcast feature. |
| TI drivers, CC13x2/CC26x2 device source and TI-RTOS7 | Compared `.c`, `.h`, `.asm`, `.cmd`, `.opts`, `.js` and `.xdt` files in these directories are unchanged after text newline normalization. | UART race fixes listed in both SDK changelogs were already present in the baseline. They do not justify dropping our UART transport patch. This check did not establish binary equivalence of every driver library. |
| Clang 5.1.1 LTS | LLVM/Clang 22 base; code-generation improvements and bug fixes. TI publishes Cortex-M4 CoreMark improvement from 3.51 to 3.89 for 4.0.4 versus 5.1.0; Dhrystone results are unchanged. | Possible CPU improvements, but these benchmarks do not measure our `-Oz` Zigbee application. Most vendor prebuilt code is not recompiled by changing our compiler. No measured latency, throughput or power benefit here. |
| CCS 21 / SysConfig 1.28 | New IDE, debugging, build and scripting capabilities; our project explicitly selected and successfully ran the new compiler and SysConfig. | Useful development tooling, not an automatic improvement to radio reliability. The detailed SysConfig 1.28.2 issue history was not independently retrieved; no specific fix is attributed to it. |

The aggregate SDK changelog lists TI154STACK-4484 (large-packet/bad-MAC-state
memory leak), -4480 (RX-reset race), -4477 (clear source matching on reset),
-4476 (low-temperature radio failure), and other fixes. The changed linked MAC
code makes MAC improvements relevant to investigate, especially reset and
temperature handling. The public descriptions do not prove that every listed
TI 15.4 fix affects our 2.4 GHz Zigbee configuration. Frequency-hopping features,
Sub-1 GHz behavior, and CC1354/CC2674 PA-table improvements are not zzh gains.

The unchanged driver source also prevents double-counting TIDRIVERS-6757 and
TIDRIVERS-6735 as benefits of this particular upgrade. The newer compiler's
5.1.1-specific LTO/FPU target-triple warning fix is not a demonstrated runtime
benefit for this non-LTO build.

## Measured build impact

| Measurement | Previous build | Updated build | Difference |
| --- | ---: | ---: | ---: |
| Application FLASH region used | 180,331 bytes | 181,046 bytes | +715 bytes |
| Linker SRAM used | 30,763 bytes | 31,155 bytes | +392 bytes |
| HEX data, including CCFG | 180,419 bytes | 181,134 bytes | +715 bytes |
| C stack reservation | 4,096 bytes | 4,096 bytes | No change |
| Flash/NV boundary | `0x50000` | `0x50000` | No change |
| Bootloader word | `0xc5fe0dc5` | `0xc5fe0dc5` | DIO13, active low |

These are linker/image measurements, not heap minimum-free or task-stack
high-water measurements. The C stack reservation is separate from the Z-Stack
task's stack. The differences combine SDK, generator and compiler effects; this
comparison does not isolate which change accounts for each byte.

Likely better: supported current development tools, compiler maintenance fixes,
and updated MAC temperature/reset handling. Likely worse or riskier: slightly
higher memory use, a new vendor MAC binary, different generated/code-optimized
behavior, and a tool combination outside TI's listed SDK test matrix. TI still
lists Clang 3.2.2 and SysConfig 1.21.1 as SDK dependencies. A successful link and
valid HEX do not establish interoperability or long-duration stability.

## Should we patch less?

| Patch group | Recommendation | Reason and tradeoff |
| --- | --- | --- |
| Bootloader/DIO13, DCDC, 5 dBm, linker and NV layout | Keep | Hardware and storage requirements. Linker region, SysConfig NVS region and `NVOCMP_NVPAGES` must agree. Removing one side can damage persistence or flashing access. |
| Extended NV/key-management interface, version identity and custom association commands | Keep while required by the host | These support host backup/restore and coordinator management. A plain TI ZNP build does not necessarily provide the same host contract. Treat host access to key material as intentional, privileged management access. |
| `packDev_t` serialization correction | Keep | The upstream patch changes `*pBuf += 4` to `pBuf += 4` and serializes missing fields. SDK 8.33 does not supply a replacement in the reviewed source. |
| Router-targeted permit join, group/profile forwarding and multicast setting | Keep | These implement established coordinator/host behavior. Removing them can regress pairing through routers, group traffic visibility or nonstandard device profiles. |
| UART `TX_FINISHED` callback | Keep pending a targeted transport test | TI's unchanged UART2 API explicitly says the write callback means bytes reached the FIFO; `TX_FINISHED` means they reached the pin. The driver race fix and our completion-semantic patch are different changes. |
| Xiaomi/Aqara manufacturer response and selective child-aging exemption | Keep for affected devices | These are vendor compatibility workarounds, not SDK-version workarounds. Test older and newer models separately; do not expand the OUI exemption or disable aging globally without evidence. |
| Route-failure rediscovery | Keep initially, measure | SDK NWK library section comparison does not show that this workaround has become redundant. More route discoveries can add traffic in a troubled network. |
| Router-only code, PA-board generated files, copyright reformatting | Reduce application/maintenance scope | A zzh-only recipe need not carry other products' edits. Keep the shared upstream patch for the repository's other targets. Current source-wide patch application still includes router-only sections; slimming that scope is recommended follow-up, not an already implemented change. |

The UART callback also runs in interrupt context. Any future rewrite must preserve
nonblocking callbacks and review cancellation/error handling, not just the
successful `TX_FINISHED` path.

## Should we patch more?

Add defensive fixes and observability before adding new radio behavior:

- Validate custom MT command payload lengths before reading LED/association
  fields. Return meaningful errors where operations can fail. The added handlers
  currently read fixed offsets without local minimum-length checks.
- Check `LED_open()` before calling the LED APIs in `MT_UtilLedControl()`.
  `updateLED()` already checks for a null handle; the command handler does not.
- Bound `numBytesToMatch` to `1..Z_EXTADDR_LEN` in the custom child-aging helper
  and use a defensive `>=` capacity check. It currently receives a safe constant
  `3`, so this is future-proofing, not a reproduced field failure.
- Measure minimum free heap, per-task stack high-water, UART RX errors/overruns,
  allocation failures, retries, route discoveries and NV-compaction failures.
  Preserve the host protocol when adding diagnostics.
- Record a distinguishable local build identity for deployment. The current
  image still reports 20250321, so host version output alone cannot identify the
  new tools. Review host version-based feature decisions before assigning a new
  runtime revision; artifact hashes and manifests already distinguish builds.

Two existing policy groups need explicit decisions, not unconditional additions:

1. **Rejoin security.** The coordinator patch changes
   `zgAllowRejoinsWithWellKnownKey` from TI's `FALSE` to `TRUE`. In the reviewed
   `ZDSecMgrDeviceJoin()` path, that permits network-key delivery using the
   well-known trust-center link key for the relevant unsecured TC-rejoin case,
   even when normal joining is closed. This helps legacy-device recovery but
   weakens the default admission policy. Prefer an explicitly selected legacy
   compatibility policy or a stricter tested profile over an invisible global
   relaxation. Do not silently disable it on an existing fleet without rejoin
   tests. This does not mean every device can join through every path.
2. **Buffers, retries and timeouts.** The patch increases MAC buffers, NWK queue
   limits (total 12 to 72), routing/device tables and retry limits, while reducing
   the polled APS ACK wait from six seconds to one second. These can help bursts
   and large networks, but consume memory and can increase congestion or cause
   false timeouts on sleepy/busy devices. Do not enlarge them further by default.
   Tune one parameter group at a time from measurements and host-level pacing.

No new protocol/security/tuning changes were applied during this review. They
should be separate, reviewable changes with their own validation and rollback.

## What would make the upgrade preferable?

Keep the previous build and test this image on a spare zzh or a recoverable test
network. Use the same network/device mix and host software when comparing:

1. Repeated host restarts, coordinator resets and sustained bidirectional UART
   bursts. Check missing frames, RX errors and recovery, not only throughput.
2. Pair through both the coordinator and a router; test closed-network rejoin,
   power loss, secure rejoin and the legacy-device recovery policy separately.
3. Group commands, profile-mismatch devices, old Aqara/Xiaomi sleepy devices,
   route failures and recovery under interference.
4. Large bursts and sleepy-device polls with heap/stack and retry telemetry.
   A linker's unused SRAM figure is not a heap-exhaustion test.
5. NV writes/compaction, power interruption and host backup/restore. Keep NV layout
   unchanged while comparing toolchains.
6. Controlled testing within the device's rated temperature range and a multi-day
   soak. Verify the new temperature handling actually improves the target case.

If results regress, isolate SDK/MAC changes from compiler/generator changes with
separate builds. The previous build uses Clang 4.0.2, which itself differs from
TI's SDK-listed 3.2.2; it is a comparison baseline, not TI certification. Avoid
combining a toolchain migration, rejoin-policy change and aggressive retry tuning
in one candidate image.

## Evidence and sources

The investigation compared the two installed SDK trees after applying equivalent
coordinator patches. Source comparisons normalized line endings. The archive
comparison examined member lists plus allocatable ELF sections and relocation
sections in the four `source/ti/zstack/lib/ticlang/m4f/*.a` archives and the linked
`maclib_nosecure_cc26x2_2_4g_tirtos7.a`. Differences in debug-only relocations were
not counted as changed MAC executable code. The linker maps confirmed that new
MAC/temperature functions are present in the final image. No runtime performance
or field-failure claim is established by these checks.

- [F2 SDK 8.33 release notes](https://software-dl.ti.com/simplelink/esd/simplelink_cc13xx_cc26xx_sdk/8.33.00.16/exports/release_notes_simplelink_cc13xx_cc26xx_sdk_8_33_00_16.html)
- Installed SDK `changelog.html`, `docs/zigbee/release_notes_zigbee_8_30_00.html`
  and `docs/simplelink_mcu_sdk/changelog_coresdk_cc13xx_cc26xx_8_30_02_00.html`
  in both versions; aggregate lists are not treated as all-new fixes.
- Installed Clang 5.1.1 `README.html`, including its Cortex-M4 benchmark table,
  resolved defects and 5.1.1-specific LTO warning fix.
- [CCS 21.0.1 release notes](https://software-dl.ti.com/ccs/esd/CCSv20/CCS_21_0_1/exports/ccstudio-ide_21.0.1_releasenote.html)
- SDK `source/ti/drivers/UART2.h` for FIFO versus on-wire completion semantics.
- The repository's [firmware patch](../../firmware.patch) and
  [coordinator changelog](../../CHANGELOG.md) for workaround history.
- [Build manifest](build-manifest.json), [image checks](validation.json),
  [source hashes](patched-source-sha256.json), and [rebuild recipe](README.md).
