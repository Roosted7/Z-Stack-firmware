# 2026-10-23

- Added an experimental build for the original CC2652R zzh with SimpleLink F2
  SDK 8.33.00.16, CCS 21.0.1.00010, TI ARM Clang 5.1.1.LTS and SysConfig
  1.28.2+4845.
- Added a command-line build recipe, configuration patches, installer checksums,
  source hashes, image validator and compiled firmware ZIP.
- Kept the upstream application revision at 20250321. The ZIP filename records
  the SDK version to distinguish this build.
- Adapted one upstream patch context line for TI's updated copyright year.
  Kept the coordinator compatibility patches and zzh flash/bootloader settings.
- Built successfully with two existing TI pointer-sign warnings and no errors.
  Validated HEX records, ZIP content, flash/NV layout and DIO13 bootloader access.
  No hardware or Zigbee-network testing was performed.
- Compared SDK sources, the linked MAC library, Z-Stack library sections and
  release notes. See [the impact and patch review](SDK_REVIEW.md). The review
  recommends further work; it does not change runtime behavior in this build.
