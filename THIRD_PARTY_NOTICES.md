# Third-party notices

The root MIT license covers original work and modifications. It does not replace the licenses and copyright notices of included upstream materials or downloaded dependencies.

| Component | Fixed version | Use | License file |
| --- | --- | --- | --- |
| [HeyChengC/wallstreet-explainer](https://github.com/HeyChengC/wallstreet-explainer) | `920ed1d3b3ecb5997d861902e2719dda6688c0b1` | Adapted renderer; mix workflow reference; original reference sources retained | [MIT](skill/ai-practical-video/references/upstream/wallstreet/LICENSE) |
| [SterlingChin/video-production-skills](https://github.com/SterlingChin/video-production-skills) | `7c06790e9bc1d83662b749b2fa09e62fe8c2b1ef` | Scriptwriting and handoff principles; original reference documents retained | [MIT](skill/ai-practical-video/references/upstream/scriptwriter/LICENSE) |
| [hexgrad/Kokoro-82M-v1.1-zh](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh) | v1.1-zh; exact downloaded file hashes in model-lock.json | Local Chinese voice model; weights downloaded separately | [Apache-2.0](skill/ai-practical-video/references/upstream/kokoro/APACHE-2.0.txt) |
| [thewh1teagle/kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) | 0.6.0 | Local TTS runtime, installed separately | [MIT](skill/ai-practical-video/references/upstream/kokoro-onnx/LICENSE) |

The adapted renderer is `skill/ai-practical-video/scripts/render.mjs`. The upstream reference copy is retained separately; its original license applies to the included and derived portions. The Chinese workflow and vertical film template were written for this project. `produce.py` implements its own audio muxing workflow and refers to upstream mixing structure.

Optional online preview: [rany2/edge-tts](https://github.com/rany2/edge-tts), version 7.3.1, is installed separately rather than vendored. Its installed LICENSE states LGPLv3 for the client except `srt_composer.py`, which is MIT. The independently written adapter uses its public Python API. These software licenses do not establish publication rights for service-generated audio; preview outputs retain `publication_rights: not_verified`.

Exact source-file identities are recorded in [upstream/pins.json](skill/ai-practical-video/references/upstream/pins.json). Downloaded model identities are recorded in [model-lock.json](skill/ai-practical-video/references/model-lock.json). Node and Python dependency versions are pinned in adjacent lockfiles; each dependency retains its own license.

No upstream example news imagery, portraits, logos, music or videos are included. The sample customer data is fictional and uses reserved `.example` email domains. System fonts are referenced from the user's computer, not redistributed. Model licensing does not grant rights to arbitrary third-party content.
