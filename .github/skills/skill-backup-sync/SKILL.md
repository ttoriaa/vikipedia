---
name: skill-backup-sync
description: "Synchronize the active workspace skill set to the ATC Confluence skill backup page. Use when you need to publish or refresh reusable skill backup pages for teammates."
argument-hint: "可选参数: instance=atc|cc, root_page=<id-or-url>, skill=<slug>, source_dir=.github/skills, include_template=true|false, apply=true|false"
user-invocable: true
disable-model-invocation: false
---

# Skill Backup Sync

## Purpose
Synchronize the active workspace skill set to the ATC Confluence skill backup page so teammates can discover and reuse the latest skill contracts.

## When To Use
- You need to refresh the Confluence backup index after local skill changes.
- You want teammates to discover the latest reusable skill contracts from ATC Confluence.
- The task is publishing skill contracts rather than invoking one business workflow.

## Inputs
- The local skill set to be synchronized.
- Target backup index or backup parent page.
- Optional subset of skills to publish.

## Outputs
- Sync summary showing which skill contracts were published or refreshed.
- Any skipped skills and the reason.
- Failure details for missing access or invalid source files.

## Boundaries
- Review source material before sharing outside the intended audience.
- Publish environment variable names only, never secrets.
- Keep generated cache or raw enterprise content out of the backup.

## Local Deployment Notes
- This repository now contains the local routing contract for the sync workflow.
- Helper scripts referenced by the Confluence backup are not present here.

## Sensitivity
Medium: review source material before sharing outside the intended audience.
