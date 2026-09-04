# ICRA two-column build

`root.tex` is the anonymous, unsealed ICRA paper source. Phase-G result text remains visibly
pending until the preregistered manipulation and provenance gates authorize endpoint access.

Build from the repository root:

```bash
paper/icra/build.sh
```

The build script downloads the official PaperCept `ieeeconf.cls` and a static Tectonic compiler
into an external cache, verifies their pinned SHA-256 digests, and writes generated files under
`paper/icra/build/` (ignored). It prints the PDF page count, paper size, and embedded-font table.
It fails on more than eight pages, non-Letter output, Type 3 or unembedded fonts, overfull boxes,
or unresolved citations. A passing build updates the tracked `ICRA_DRAFT.pdf` handoff. The ICRA
2027 submission limit is eight US-Letter pages total, including references.
