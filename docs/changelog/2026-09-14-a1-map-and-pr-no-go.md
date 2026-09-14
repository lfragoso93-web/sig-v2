# 2026-09-14 - A1 map update and PR NO-GO

## Scope

Governance-only update for the current `stable-15jun` certification path.

No runtime, schema, migration, provider, OCI or real-data operation changed in
this block.

## Current baseline

- branch: `stable-15jun`;
- current published HEAD before this documentation block:
  `b89851de83d2a1670682275f31788301f8278e7a`;
- #363 is closed after local recovery of backend technical gates;
- #354 remains closed after frontend/backend password policy alignment;
- #352 remains open.

## A1 state

#352 has two automated evidence blocks:

- `f89f9f0641b1a68e44db798fc56ed382bd1db769` covers that the selected class in
  `AddTransactionModal` reaches the canonical transaction write path as
  `asset_type`;
- `b89851de83d2a1670682275f31788301f8278e7a` covers mobile class tabs at
  375 px and 430 px as non-wrapping horizontally scrollable controls.

The remaining #352 decision is visual/manual validation, or an explicit Issue
decision that the automated evidence is sufficient for the first assisted gate.

## PR decision

Opening a `stable-15jun` -> `main` PR is **NO-GO** at this point.

Reason:

- #303 has not yet formally declared `PORTFOLIO-TEST-READY`;
- #226, #216, #158, #269, #284 and #227 remain part of the mandatory Track A
  chain;
- opening a PR now would spend CI before the macroblock is certified and would
  increase review/rework risk;
- PRs to `main` are reserved for certified structural macroblocks, not #363/#352
  microblocks.

## Canonical next map

1. Complete #352 final validation or record sufficiency of current evidence.
2. Finish #303 and freeze an exact candidate SHA for `PORTFOLIO-TEST-READY`.
3. Decide and close #226 using the existing portfolio-scoped Proventos evidence,
   or justify a controlled global run if materially needed.
4. Close #216 using the #226 result and already consolidated benchmark/FX
   evidence.
5. Execute the minimal #158 promotion reconciliation on the frozen SHA/dataset.
6. Run #269 security gate on exactly the same candidate SHA.
7. Homologate exactly the same SHA in OCI via #284.
8. Use #227 to issue formal GO/NO-GO.
9. Only after GO evaluate `ready_for_real_data=true`.
10. Only after the certified macroblock, open a new structural PR
    `stable-15jun` -> `main`.

## Guardrails

- Do not start Track B features before Track A completes, except P0/P1 fixes
  required for certification.
- Do not mix Dependabot/toolchain upgrades into the candidate SHA unless a
  critical vulnerability requires it.
- Do not run OCI as a development environment.
- Do not force `/ready` or `ready_for_real_data=true`.
- Keep providers out of financial read paths.
