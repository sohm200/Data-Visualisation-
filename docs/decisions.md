# Decisions Log

Decisions made during discussion that are not yet written into the SRS. Move each one into the SRS when it's adopted, then delete it here.

| Date | Decision | Affects |
|---|---|---|
| 2026-10-10 | **Hosting (later):** optional hosting after the first release via Docker (Hugging Face Spaces or Render), with a lower file size limit (about 10 MB), a privacy note on upload, and simple access control. (The local Waitress part of this decision moved into SRS v0.3.) | §2.1, §3.4, FR-05, NFR-11, NFR-12 |
| 2026-10-10 | **Diagram timing:** do estimation (function points, COCOMO, Gantt, risks), activity diagrams and an analysis class diagram before building. Generate the design class diagram from the real code after building, plus an estimated vs. actual comparison. | Project plan |
