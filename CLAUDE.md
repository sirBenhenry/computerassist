# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project State

This project is currently in the **design and architecture phase**. There is no implementation code yet — only documentation and flowchart visualizations of the planned system.

## Architecture Reference

**Read `ARCHITECTURE.md` first.** It is the authoritative description of the full system logic, all components, all data flows, and all design decisions. Do not make assumptions about how the system works without reading it — the architecture has several non-obvious choices (e.g. HMM does not connect directly to the Confidence Aggregator; it only feeds into VMM).

## Flowchart

`computerassist-architecture(2).html` — open in any browser. Self-contained SVG diagram with full component reference table below it. No dependencies, no CDN required.

## Key Architecture Points (things easy to get wrong)

- **HMM → VMM only**: HMM's output (workflow state × confidence) feeds exclusively into VMM. It does not connect directly to the Confidence Aggregator.
- **VMM is the core predictor**: HMM only provides workflow context. VMM does the actual next-action prediction.
- **Feature Extraction is the most critical component**: all downstream model quality depends on it. Weight separation (command name = HIGH weight, arguments = LOW weight) is essential.
- **Three distinct feedback channels**: Feedback Collection routes back to VMM (online update), Fuzzy Pattern Store (pattern validation), and Log Shipping (server training data) — these are separate signals with different purposes.
- **HMM is batch-trained only** (overnight, server-side, Baum-Welch). VMM and Fuzzy Pattern Store update continuously and locally on every event.
- **Phase Gate is manual**: the user controls when to switch from Training Mode to Executing Mode. It is not automated.
