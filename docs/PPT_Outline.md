# PPT Outline: Automated Data Visualization Dashboard System

Status: **built** as `outputs/ppt/Automated_Data_Visualization_Dashboard.pptx` (18 slides, speaker notes on every slide). Modern dark/light design, native editable charts and tables, Gantt chart drawn from native shapes.

Build notes:
- Title, team, guide, college, course and date on slide 1 are placeholders for you to edit.
- The Gantt chart and PERT critical path are drawn as PowerPoint shapes from the planning document's task list, so they can be edited.
- Slide 13 includes the measured size of the finished code (1,744 non-blank lines) next to the estimates. There is no estimated-vs-actual comparison of effort or dates, as agreed.
- Test count is 177 (re-run on 22 Oct 2026). Selenium results are from `outputs/selenium/results.xml` (6 of 6 passed).
- The diagrams keep their original look, so their internal text size is fixed by the source images.

- **Structure:** 1 title slide + 16 content slides + 1 conclusion / thank-you slide = 18 slides in total.
- **Audience:** the teacher, as a reference document. It may later be presented at the external oral exam, so each slide carries short speaker notes.
- **Style:** plain, readable on its own. One main idea per slide. The live demo covers the screens, so only one dashboard screenshot is included.
- **Diagrams:** simplified versions only. No detailed activity diagrams (AD-1 to AD-7), no class diagrams CD-1 and CD-2, no DFD Level 2. Those stay in `docs/` for reference.

## Slide plan

| # | Title | One message | Content and source | Visual |
|---|---|---|---|---|
| T | Title | Project name, team, guide, date | Details from you | None |
| 1 | Problem and objectives | Turning a raw spreadsheet into useful charts takes manual effort and chart-choosing skill | SRS 1.1, 1.3 | Three objectives |
| 2 | Scope and users | What the first release does and does not do | SRS 1.3, 2.2, 2.3; backlog items FR-22, FR-25, AI (FR-27 to 29) | Two columns: in scope, later |
| 3 | System overview | Five steps from file to dashboard: Upload, Validate, Profile, Choose charts, Render | Progress Report 2.1, 2.2 | Pipeline graphic with the four modules |
| 4 | Core rules | The system decides by rules, not by AI | SRS 4.2.3, 4.3.2, 4.3.3 | Column types on the left, chart rules R1 to R6 on the right |
| 5 | Use case diagram | Who uses the system and what it offers | `UML-Diagrams(use case+sequence).pdf`, page 1 | Diagram |
| 6 | Data flow diagrams | Level 0 (one process) and Level 1 (four processes, two data stores) | `DFD_Excel_Dashboard-1.pdf`, pages 1 and 2 | Two diagrams side by side |
| 7 | Activity diagram | The upload-to-dashboard flow | `Simplified_Activity_Diagram.png` | Diagram |
| 8 | Class diagram | The main classes and how they relate | `Simplified_Class_Diagram.png` | Diagram |
| 9 | Sequence diagram | Message order for the main scenario | `UML-Diagrams(use case+sequence).pdf`, page 2 | Diagram |
| 10 | Implementation | Python, Flask, pandas, Plotly; about 1,870 lines of application code | Progress Report 1, 4 | Tech-stack strip, module list, 1 dashboard screenshot (TF-01) |
| 11 | Estimation: function points and size | 91 function points; about 2.2 KLOC bottom-up (upper bound 4.0) | Planning doc 2, 3 | Component-count table and the LOC comparison |
| 12 | Estimation: effort and schedule (COCOMO) | 5.5 person-months, 4.8 months nominal; about 842 hours | Planning doc 4 | Result table, plus actual LOC measured against the estimate |
| 13 | Scheduling: PERT/CPM | Critical path A → D → E → G → H → J → K → M → O is 39 working days; 66% chance of finishing by the sprint 4 date, 99% with one buffer week | Planning doc 5.1 to 5.5 | Network graphic with the critical path in red, small probability table |
| 14 | Gantt chart | The project schedule with sprint review milestones | Planning doc 5.6 | The Gantt chart alone, full slide |
| 15 | Testing: strategy and results | 177 automated tests pass; all 16 SRS test files covered; each module tested separately | Progress Report 6; SRS 6.4 | Bar chart of tests per module, grouped summary of the 16 test files |
| 16 | Testing: browser checks and performance | Browser tests and Selenium results; 50,000 rows by 30 columns in 3.8 s against a 30 s limit | Progress Report 7, 8; `outputs/selenium`; Assignment 7 report | Performance against the limit, table of browser-test outcomes |
| C | Conclusion and thank you | What was achieved, known limitations, future work (FR-22, FR-25, AI, hosting), thanks | Progress Report 11, 12; `decisions.md` | Short list |

## Why the Gantt chart has its own slide

A Gantt chart with 14 tasks and four milestones needs the full slide width to stay readable. So slide 14 holds only the chart and a one-line legend (red means critical, diamonds mean sprint reviews). The text about the schedule and critical path goes on slide 13. The planning doc holds the chart as a Mermaid block, so I redraw it as an image from the same task list and dates.

## Things I need from you or will do

1. **Title slide details:** project title wording, team member names, guide, college and course, date.
2. **Test count.** The Progress Report summary says 142 tests, but its phase log says 177. I'll use **177** and re-run the suite before the final build to confirm.
3. **Estimated vs. actual.** That table is empty in the planning doc. Slide 12 shows the estimate next to the actual lines of code, which I can measure myself. Actual effort hours and dates are yours to supply, or I leave that comparison out.
4. **Browser and Selenium results (slide 16).** I'll read `outputs/selenium/results.xml` and the Assignment 7 report to get the real outcomes before writing the slide.
5. **Screenshot for slide 10.** I'll take a fresh headless screenshot of the TF-01 dashboard rather than reuse the evidence images.
6. **Diagram PDFs.** I convert the needed PDF pages to images and crop the white margins.

## Decisions for you

1. **Visual style:** a plain white academic look (recommended) or a darker, more modern one.
2. **Tooling:** I need `python-pptx` and `matplotlib`. I can install them into a scratch folder so your Python stays untouched, or you can install them yourself.

## Next phase

After you approve this outline, I generate the `.pptx` and render every slide to an image to check layout. Output goes to `outputs/ppt/`, with a short note on how each slide was built.
