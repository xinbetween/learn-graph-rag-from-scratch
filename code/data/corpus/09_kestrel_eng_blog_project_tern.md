# Introducing Project Tern: Our Own Sonar, Built in Port Avalon

*Kestrel Labs engineering blog. Posted 30 June 2025. Authors: Jonas Vehl and Priya Nair.*

Today we are kicking off Project Tern, the biggest engineering effort in Kestrel Labs history since our first prototype. The goal is simple to state and hard to do: design and build our own sonar module, so that every Sentinel drone can run on hardware we make ourselves.

The two of us will co-lead Tern. Jonas designed the acoustic array that Sentinel drones have used since 2023; Priya has spent the last two years making the Sentinel fleet reliable at sea and, before that, worked on sensor fusion for much larger vehicles. Between us we think we have the right mix of acoustics and systems engineering, and we are hiring six more engineers to join us.

## Why the name?

Terns are small seabirds that find fish by listening and watching from above before diving with incredible precision. They are also famously good at long migrations. A small, efficient, precise instrument that can go a long way felt like the right mascot.

## What Tern replaces

Until now, the transducers and signal-processing boards inside every Sentinel drone came from Deepcast. They have been good parts, and we are grateful for three years of working together. But Deepcast units will no longer be available to us, and Project Tern will replace the Deepcast sonar in Project Sentinel. By the end of 2026 we want every drone in the fleet running a Tern module.

## Technical goals

- **Size and power:** fit into the existing Sentinel hull without redesign, using no more power than the current module.
- **Performance:** match current mapping resolution on Halden Reef and improve fish-school detection at night.
- **Manufacturability:** transducers built with a contract ceramics shop, electronics assembled in Port Avalon.
- **Openness:** document the signal-processing pipeline so that Tidewater Institute scientists can verify exactly how their acoustic data is produced.

## Timeline

1. Q3 2025: bench prototypes of transducer elements.
2. Q4 2025: first complete module tested in the harbour.
3. Q1 2026: sea trials on two Sentinel drones at Halden Reef.
4. Q2 to Q4 2026: phased replacement across the fleet.

## What this means for Sentinel partners

Nothing changes for our partners in the short term. Existing drones keep flying with their current modules, and we hold enough spares to keep monitoring Halden Reef without interruption while Tern is developed. If you work with Sentinel data, you will hear from us before any Tern module goes into the water.

We will post progress updates here every couple of months. If building sonar from scratch sounds like fun, our careers page has the open roles.

Jonas Vehl and Priya Nair
