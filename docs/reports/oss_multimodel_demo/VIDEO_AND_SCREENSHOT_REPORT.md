# Video and screenshot report

## Public media

- Video: `docs/assets/multimodel-research-demo.webm`
- Duration: 37.75 seconds
- Codec: VP9
- Frame size: 1440 by 1000
- Frame rate: 24 fps
- Size: 1,763,118 bytes
- SHA-256: `3cb699318e0f0ffdc94d53124774d2889a55ff511cd28a8acbdb644c3f3073b4`

The public video combines a 60-times accelerated version of the first 30-minute live browser capture with a normal-speed completed-result walkthrough. The original capture reached the recorder's 30-minute bound before the 33-minute 28-second backend run completed. A second capture then opened the same completed research ID and recorded the candidate synthesis, receipt chain, diagnostics, and return to the research result.

## Local raw media

The unaccelerated live capture is retained outside git at `output/playwright/take6/10bd995746430e2ba62812c0cff0e771.webm`.

- Duration: 1,802.60 seconds
- Size: 143,522,741 bytes
- SHA-256: `b1242ca08f499b61fe182a7923f998c44a41497a3da0bd55f27d2a24427f5376`

The normal-speed completed walkthrough is retained at `output/playwright/take6-public/multimodel-research-full.webm` with SHA-256 `e088be403f1d984a2643f736ba707cccca342985faf410da5242be0125a1d2e7`.

## Screenshots

- `multimodel-research-ready.png`: local model route and no-key boundary before execution.
- `multimodel-research-running.png`: running stage, model route, and proof timeline.
- `multimodel-research-complete.png`: both analyst outputs, candidate synthesis, hashes, receipts count, and full event timeline.
- `multimodel-research-receipts.png`: five linked workflow receipts.
- `multimodel-research-diagnostics.png`: healthy local runtime, local data label, five receipts, and one research record.

The screenshots were opened at original resolution. Video frames at 0, 15, 31, and 36 seconds were also rendered and inspected. The diagnostics view was recaptured after replacing the absolute local data path with a public-safe leaf label.
